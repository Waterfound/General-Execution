from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest
from .capacity import release_capacity_for_outcome, release_capacity_for_revocation
from .durable import (
    DurableCapacitySnapshot,
    RecoveredInFlightLease,
    build_durable_snapshot,
    recover_after_restart,
    verify_durable_snapshot,
    verify_durable_successor,
)
from .models import ExecutionSession, RunnerCapabilities
from .persistence import (
    PersistenceCommitReceipt,
    PersistenceConflict,
    SQLiteDurableHeadStore,
)
from .physical import PhysicalOutcomeBundle

ResolutionKind = Literal["provider_outcome", "session_revoked"]
VALID_RESOLUTION_KINDS = frozenset({"provider_outcome", "session_revoked"})


class ReconciliationError(ValueError):
    pass


class ReconciliationConflict(ReconciliationError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class RecoveryReconciliationPlan:
    resolution_kind: ResolutionKind
    source_snapshot: DurableCapacitySnapshot
    recovered_lease: RecoveredInFlightLease
    evidence_digest: str
    release_digest: str
    target_snapshot: DurableCapacitySnapshot
    schema_version: str = "ge.recovery-reconciliation-plan.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.recovery-reconciliation-plan.v1":
            raise ValueError("unsupported recovery reconciliation plan schema")
        if self.resolution_kind not in VALID_RESOLUTION_KINDS:
            raise ValueError("unsupported recovery resolution kind")
        _require_sha256("evidence_digest", self.evidence_digest)
        _require_sha256("release_digest", self.release_digest)
        if self.target_snapshot.head.previous_head_digest != self.source_snapshot.head.digest:
            raise ValueError("target durable head must directly reference source durable head")

    @property
    def source_head_digest(self) -> str:
        return self.source_snapshot.head.digest

    @property
    def source_snapshot_digest(self) -> str:
        return self.source_snapshot.digest

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RecoveryReconciliationReceipt:
    plan_digest: str
    resolution_kind: ResolutionKind
    lease_id: str
    lease_digest: str
    source_head_digest: str
    committed_head_digest: str
    committed_generation: int
    target_snapshot_digest: str
    release_digest: str
    persistence_receipt_digest: str
    idempotent: bool
    schema_version: str = "ge.recovery-reconciliation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.recovery-reconciliation-receipt.v1":
            raise ValueError("unsupported recovery reconciliation receipt schema")
        if self.resolution_kind not in VALID_RESOLUTION_KINDS:
            raise ValueError("unsupported recovery resolution kind")
        if not self.lease_id or not self.lease_id.strip():
            raise ValueError("lease_id must be non-empty")
        if self.committed_generation < 1:
            raise ValueError("committed_generation must be >= 1")
        for name in (
            "plan_digest",
            "lease_digest",
            "source_head_digest",
            "committed_head_digest",
            "target_snapshot_digest",
            "release_digest",
            "persistence_receipt_digest",
        ):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _find_recovered_active_lease(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    recovered: RecoveredInFlightLease,
):
    if not verify_durable_snapshot(snapshot, runner):
        raise ReconciliationError("source durable snapshot is invalid")
    _, report = recover_after_restart(snapshot, runner)
    if recovered not in report.active_leases:
        raise ReconciliationConflict("recovered lease is not active in the source durable head")
    matches = [
        lease
        for lease in snapshot.state.active_leases
        if lease.lease_id == recovered.lease_id and lease.digest == recovered.lease_digest
    ]
    if len(matches) != 1:
        raise ReconciliationError("recovered lease does not map to one canonical active capacity lease")
    return matches[0]


def _verify_target_intrinsic(plan: RecoveryReconciliationPlan, runner: RunnerCapabilities) -> bool:
    target = plan.target_snapshot
    if not verify_durable_snapshot(target, runner):
        return False
    if target.head.previous_head_digest != plan.source_head_digest:
        return False
    if not target.state.transitions:
        return False
    transition = target.state.transitions[-1]
    if transition.kind != "release" or transition.release is None:
        return False
    release = transition.release
    if release.digest != plan.release_digest:
        return False
    if release.lease_id != plan.recovered_lease.lease_id or release.lease_digest != plan.recovered_lease.lease_digest:
        return False
    if any(lease.lease_id == plan.recovered_lease.lease_id for lease in target.state.active_leases):
        return False
    if plan.resolution_kind == "provider_outcome":
        return (
            release.release_kind == "terminal_outcome"
            and release.outcome_digest == plan.evidence_digest
            and release.revoked_session_digest is None
        )
    return (
        release.release_kind == "session_revoked"
        and release.revoked_session_digest == plan.evidence_digest
        and release.outcome_digest is None
    )


def verify_reconciliation_plan(
    source: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    plan: RecoveryReconciliationPlan,
) -> bool:
    if source != plan.source_snapshot:
        return False
    if not verify_durable_snapshot(source, runner):
        return False
    try:
        _find_recovered_active_lease(source, runner, plan.recovered_lease)
    except ReconciliationError:
        return False
    target = plan.target_snapshot
    if not _verify_target_intrinsic(plan, runner):
        return False
    if not verify_durable_successor(source, target, runner):
        return False
    if target.state.generation != source.state.generation + 1:
        return False
    if target.state.transitions[:-1] != source.state.transitions:
        return False
    return True


def plan_provider_outcome_reconciliation(
    source: DurableCapacitySnapshot,
    spec,
    registry,
    execution_plan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    recovered: RecoveredInFlightLease,
    outcome: PhysicalOutcomeBundle,
) -> RecoveryReconciliationPlan:
    lease = _find_recovered_active_lease(source, runner, recovered)
    try:
        next_state, grant, _ = release_capacity_for_outcome(
            source.state,
            spec,
            registry,
            execution_plan,
            session,
            runner,
            lease,
            outcome,
        )
    except ValueError as exc:
        raise ReconciliationError("provider outcome cannot resolve the recovered lease") from exc
    target = build_durable_snapshot(next_state, runner, previous=source)
    plan = RecoveryReconciliationPlan(
        resolution_kind="provider_outcome",
        source_snapshot=source,
        recovered_lease=recovered,
        evidence_digest=outcome.digest,
        release_digest=grant.release.digest,
        target_snapshot=target,
    )
    if not verify_reconciliation_plan(source, runner, plan):
        raise ReconciliationError("constructed provider-outcome reconciliation plan failed verification")
    return plan


def plan_revocation_reconciliation(
    source: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    recovered: RecoveredInFlightLease,
    revoked_session: ExecutionSession,
) -> RecoveryReconciliationPlan:
    lease = _find_recovered_active_lease(source, runner, recovered)
    try:
        next_state, grant, _ = release_capacity_for_revocation(
            source.state,
            runner,
            lease,
            revoked_session,
        )
    except ValueError as exc:
        raise ReconciliationError("revoked Session cannot resolve the recovered lease") from exc
    target = build_durable_snapshot(next_state, runner, previous=source)
    plan = RecoveryReconciliationPlan(
        resolution_kind="session_revoked",
        source_snapshot=source,
        recovered_lease=recovered,
        evidence_digest=sha256_digest(revoked_session),
        release_digest=grant.release.digest,
        target_snapshot=target,
    )
    if not verify_reconciliation_plan(source, runner, plan):
        raise ReconciliationError("constructed revocation reconciliation plan failed verification")
    return plan


def commit_reconciliation(
    store: SQLiteDurableHeadStore,
    runner: RunnerCapabilities,
    plan: RecoveryReconciliationPlan,
) -> tuple[DurableCapacitySnapshot, PersistenceCommitReceipt, RecoveryReconciliationReceipt]:
    if not verify_reconciliation_plan(plan.source_snapshot, runner, plan):
        raise ReconciliationError("reconciliation plan failed intrinsic source-to-target verification")

    current = store.load_current(runner)
    if current is None:
        raise ReconciliationConflict("no canonical durable head exists for recovered lease")

    if current == plan.source_snapshot:
        try:
            persistence_receipt = store.compare_and_swap(
                plan.target_snapshot,
                runner,
                expected_head_digest=plan.source_head_digest,
            )
        except PersistenceConflict as exc:
            raise ReconciliationConflict("canonical durable head changed during reconciliation") from exc
    elif current == plan.target_snapshot:
        try:
            persistence_receipt = store.compare_and_swap(
                plan.target_snapshot,
                runner,
                expected_head_digest=plan.target_snapshot.head.digest,
            )
        except PersistenceConflict as exc:
            raise ReconciliationConflict("canonical durable head changed during idempotent reconciliation") from exc
    else:
        raise ReconciliationConflict("canonical durable head is neither reconciliation source nor exact target")

    receipt = RecoveryReconciliationReceipt(
        plan_digest=plan.digest,
        resolution_kind=plan.resolution_kind,
        lease_id=plan.recovered_lease.lease_id,
        lease_digest=plan.recovered_lease.lease_digest,
        source_head_digest=plan.source_head_digest,
        committed_head_digest=plan.target_snapshot.head.digest,
        committed_generation=plan.target_snapshot.head.generation,
        target_snapshot_digest=plan.target_snapshot.digest,
        release_digest=plan.release_digest,
        persistence_receipt_digest=persistence_receipt.digest,
        idempotent=persistence_receipt.idempotent,
    )
    if not verify_reconciliation_receipt(plan, persistence_receipt, receipt):
        raise ReconciliationError("reconciliation receipt failed verification")
    return plan.target_snapshot, persistence_receipt, receipt


def verify_reconciliation_receipt(
    plan: RecoveryReconciliationPlan,
    persistence_receipt: PersistenceCommitReceipt,
    receipt: RecoveryReconciliationReceipt,
) -> bool:
    return (
        receipt.plan_digest == plan.digest
        and receipt.resolution_kind == plan.resolution_kind
        and receipt.lease_id == plan.recovered_lease.lease_id
        and receipt.lease_digest == plan.recovered_lease.lease_digest
        and receipt.source_head_digest == plan.source_head_digest
        and receipt.committed_head_digest == plan.target_snapshot.head.digest
        and receipt.committed_generation == plan.target_snapshot.head.generation
        and receipt.target_snapshot_digest == plan.target_snapshot.digest
        and receipt.release_digest == plan.release_digest
        and receipt.persistence_receipt_digest == persistence_receipt.digest
        and receipt.idempotent == persistence_receipt.idempotent
        and persistence_receipt.committed_head_digest == plan.target_snapshot.head.digest
        and persistence_receipt.generation == plan.target_snapshot.head.generation
        and persistence_receipt.snapshot_digest == plan.target_snapshot.digest
    )
