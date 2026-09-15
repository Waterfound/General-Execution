from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import sha256_digest, stable_id
from .capacity import (
    CapacityReleaseGrant,
    CapacityTransition,
    release_capacity_for_outcome,
    verify_capacity_release_grant,
)
from .durable import (
    DurableCapacitySnapshot,
    RecoveredInFlightLease,
    build_durable_snapshot,
    recover_after_restart,
    verify_durable_snapshot,
    verify_durable_successor,
)
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import PhysicalOutcomeBundle, verify_physical_outcome


class ReconciliationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReconciliationRecord:
    runner_id: str
    runner_capability_digest: str
    session_id: str
    logical_attempt: int
    spec_id: str
    spec_digest: str
    plan_id: str
    plan_digest: str
    registry_digest: str
    source_head_digest: str
    source_snapshot_digest: str
    lease_id: str
    lease_digest: str
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    outcome_digest: str
    receipt_digest: str
    transport_status: str
    result_digest: str | None
    release_digest: str
    successor_head_digest: str
    successor_snapshot_digest: str
    schema_version: str = "ge.restart-reconciliation-record.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.restart-reconciliation-record.v1":
            raise ValueError("unsupported reconciliation record schema")
        for name in (
            "runner_id",
            "session_id",
            "spec_id",
            "plan_id",
            "lease_id",
            "authorization_id",
            "invocation_id",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError("attempt ordinals must be >= 1")
        for name in (
            "runner_capability_digest",
            "spec_digest",
            "plan_digest",
            "registry_digest",
            "source_head_digest",
            "source_snapshot_digest",
            "lease_digest",
            "authorization_digest",
            "outcome_digest",
            "receipt_digest",
            "release_digest",
            "successor_head_digest",
            "successor_snapshot_digest",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc
        if self.result_digest is not None:
            if not self.result_digest.startswith("sha256:") or len(self.result_digest) != 71:
                raise ValueError("result_digest must be sha256:<64-hex>")
            try:
                int(self.result_digest[7:], 16)
            except ValueError as exc:
                raise ValueError("result_digest must contain 64 hexadecimal characters") from exc

    @property
    def reconciliation_id(self) -> str:
        return stable_id("gerr", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ReconciliationCandidate:
    source_snapshot: DurableCapacitySnapshot
    spec: ExecutionSpec
    registry: RunnerRegistry
    plan: DispatchPlan
    session: ExecutionSession
    recovered_lease: RecoveredInFlightLease
    outcome: PhysicalOutcomeBundle
    release_grant: CapacityReleaseGrant
    release_transition: CapacityTransition
    successor_snapshot: DurableCapacitySnapshot
    record: ReconciliationRecord
    schema_version: str = "ge.restart-reconciliation-candidate.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.restart-reconciliation-candidate.v1":
            raise ValueError("unsupported reconciliation candidate schema")

    @property
    def digest(self) -> str:
        return sha256_digest(
            {
                "schema_version": self.schema_version,
                "source_snapshot_digest": self.source_snapshot.digest,
                "spec_digest": self.spec.digest,
                "registry_digest": self.registry.digest,
                "plan_digest": self.plan.digest,
                "session_digest": sha256_digest(self.session),
                "recovered_lease_digest": self.recovered_lease.digest,
                "outcome_digest": self.outcome.digest,
                "release_grant_digest": self.release_grant.digest,
                "release_transition_digest": self.release_transition.digest,
                "successor_snapshot_digest": self.successor_snapshot.digest,
                "record_digest": self.record.digest,
            }
        )


def reconciliation_record_to_dict(record: ReconciliationRecord) -> dict[str, Any]:
    return asdict(record)


def reconciliation_record_from_dict(data: dict[str, Any]) -> ReconciliationRecord:
    if data.get("schema_version") != "ge.restart-reconciliation-record.v1":
        raise ReconciliationError("unsupported reconciliation record schema")
    try:
        return ReconciliationRecord(
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            session_id=str(data["session_id"]),
            logical_attempt=int(data["logical_attempt"]),
            spec_id=str(data["spec_id"]),
            spec_digest=str(data["spec_digest"]),
            plan_id=str(data["plan_id"]),
            plan_digest=str(data["plan_digest"]),
            registry_digest=str(data["registry_digest"]),
            source_head_digest=str(data["source_head_digest"]),
            source_snapshot_digest=str(data["source_snapshot_digest"]),
            lease_id=str(data["lease_id"]),
            lease_digest=str(data["lease_digest"]),
            authorization_id=str(data["authorization_id"]),
            authorization_digest=str(data["authorization_digest"]),
            invocation_id=str(data["invocation_id"]),
            physical_attempt=int(data["physical_attempt"]),
            outcome_digest=str(data["outcome_digest"]),
            receipt_digest=str(data["receipt_digest"]),
            transport_status=str(data["transport_status"]),
            result_digest=str(data["result_digest"]) if data.get("result_digest") is not None else None,
            release_digest=str(data["release_digest"]),
            successor_head_digest=str(data["successor_head_digest"]),
            successor_snapshot_digest=str(data["successor_snapshot_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ReconciliationError("invalid reconciliation record payload") from exc


def _match_recovered_lease(snapshot: DurableCapacitySnapshot, outcome: PhysicalOutcomeBundle, runner: RunnerCapabilities) -> RecoveredInFlightLease:
    _, report = recover_after_restart(snapshot, runner, expected_head_digest=snapshot.head.digest)
    auth = outcome.authorization
    matches = [
        lease
        for lease in report.active_leases
        if lease.authorization_id == auth.authorization_id
        and lease.authorization_digest == auth.digest
        and lease.invocation_id == auth.request.invocation_id
        and lease.physical_attempt == auth.physical_attempt
    ]
    if len(matches) != 1:
        raise ReconciliationError("outcome does not identify exactly one recovered in-flight lease")
    return matches[0]


def _record_for(
    runner: RunnerCapabilities,
    source: DurableCapacitySnapshot,
    lease,
    outcome: PhysicalOutcomeBundle,
    release_grant: CapacityReleaseGrant,
    successor: DurableCapacitySnapshot,
) -> ReconciliationRecord:
    request = outcome.authorization.request
    return ReconciliationRecord(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        session_id=request.session_id,
        logical_attempt=request.attempt,
        spec_id=request.spec_id,
        spec_digest=request.spec_digest,
        plan_id=request.plan_id,
        plan_digest=request.plan_digest,
        registry_digest=request.registry_digest,
        source_head_digest=source.head.digest,
        source_snapshot_digest=source.digest,
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        authorization_id=outcome.authorization.authorization_id,
        authorization_digest=outcome.authorization.digest,
        invocation_id=request.invocation_id,
        physical_attempt=outcome.authorization.physical_attempt,
        outcome_digest=outcome.digest,
        receipt_digest=outcome.receipt.digest,
        transport_status=outcome.receipt.transport_status,
        result_digest=outcome.result.digest if outcome.result is not None else None,
        release_digest=release_grant.release.digest,
        successor_head_digest=successor.head.digest,
        successor_snapshot_digest=successor.digest,
    )


def prepare_restart_reconciliation(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    outcome: PhysicalOutcomeBundle,
) -> ReconciliationCandidate:
    if not verify_durable_snapshot(snapshot, runner):
        raise ReconciliationError("source durable snapshot is invalid")
    if not verify_physical_outcome(spec, registry, plan, session, runner, outcome):
        raise ReconciliationError("provider outcome does not reproduce from execution context")

    recovered = _match_recovered_lease(snapshot, outcome, runner)
    active = [lease for lease in snapshot.state.active_leases if lease.lease_id == recovered.lease_id and lease.digest == recovered.lease_digest]
    if len(active) != 1:
        raise ReconciliationError("recovered lease is not one exact active capacity lease")
    lease = active[0]

    successor_state, release_grant, release_transition = release_capacity_for_outcome(
        snapshot.state,
        spec,
        registry,
        plan,
        session,
        runner,
        lease,
        outcome,
    )
    successor = build_durable_snapshot(successor_state, runner, previous=snapshot)
    record = _record_for(runner, snapshot, lease, outcome, release_grant, successor)
    candidate = ReconciliationCandidate(
        source_snapshot=snapshot,
        spec=spec,
        registry=registry,
        plan=plan,
        session=session,
        recovered_lease=recovered,
        outcome=outcome,
        release_grant=release_grant,
        release_transition=release_transition,
        successor_snapshot=successor,
        record=record,
    )
    if not verify_reconciliation_candidate(candidate, runner):
        raise ReconciliationError("constructed reconciliation candidate did not verify")
    return candidate


def verify_reconciliation_candidate(candidate: ReconciliationCandidate, runner: RunnerCapabilities) -> bool:
    source = candidate.source_snapshot
    successor = candidate.successor_snapshot
    outcome = candidate.outcome
    if not verify_durable_snapshot(source, runner) or not verify_durable_snapshot(successor, runner):
        return False
    if not verify_durable_successor(source, successor, runner):
        return False
    if not verify_physical_outcome(
        candidate.spec,
        candidate.registry,
        candidate.plan,
        candidate.session,
        runner,
        outcome,
    ):
        return False

    try:
        _, report = recover_after_restart(source, runner, expected_head_digest=source.head.digest)
    except ValueError:
        return False
    if candidate.recovered_lease not in report.active_leases:
        return False

    if candidate.release_transition.kind != "release" or not successor.state.transitions:
        return False
    if successor.state.transitions[-1] != candidate.release_transition:
        return False
    if not verify_capacity_release_grant(successor.state, runner, candidate.release_grant):
        return False
    release = candidate.release_grant.release
    if release != candidate.release_transition.release or release.release_kind != "terminal_outcome":
        return False

    recovered = candidate.recovered_lease
    active_matches = [
        lease
        for lease in source.state.active_leases
        if lease.lease_id == recovered.lease_id and lease.digest == recovered.lease_digest
    ]
    if len(active_matches) != 1:
        return False
    lease = active_matches[0]
    auth = outcome.authorization
    if (
        recovered.authorization_id != auth.authorization_id
        or recovered.authorization_digest != auth.digest
        or recovered.invocation_id != auth.request.invocation_id
        or recovered.physical_attempt != auth.physical_attempt
        or lease.authorization_id != auth.authorization_id
        or lease.authorization_digest != auth.digest
        or lease.invocation_id != auth.request.invocation_id
        or lease.physical_attempt != auth.physical_attempt
    ):
        return False
    if (
        release.lease_id != lease.lease_id
        or release.lease_digest != lease.digest
        or release.authorization_id != auth.authorization_id
        or release.authorization_digest != auth.digest
        or release.invocation_id != auth.request.invocation_id
        or release.physical_attempt != auth.physical_attempt
        or release.outcome_digest != outcome.digest
        or release.receipt_digest != outcome.receipt.digest
        or release.transport_status != outcome.receipt.transport_status
    ):
        return False

    expected = _record_for(runner, source, lease, outcome, candidate.release_grant, successor)
    return candidate.record == expected
