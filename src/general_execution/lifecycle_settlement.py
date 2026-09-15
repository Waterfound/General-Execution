from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import initialize_capacity_state, reserve_capacity
from .cold_bootstrap import bootstrap_active_recovery_contexts
from .cutpoint_matrix import CutPointAssessment, assess_reference_cutpoint
from .durable import build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ExecutionSpec, ResultEnvelope, RunnerRegistry
from .persistence import SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_completed
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import commit_reconciliation, plan_provider_outcome_reconciliation
from .recovery_context import SQLiteRecoveryContextStore, build_recovery_context
from .reference_bridge import (
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session
from .session_settlement import (
    DurableSessionRecord,
    SessionSettlementConflict,
    SessionSettlementReceipt,
    SQLiteSessionSettlementStore,
)

LogicalLifecycleState = Literal[
    "physical_pending_session_running",
    "physical_settled_session_running",
    "logical_result_submitted",
    "logical_revoked",
]


class LifecycleSettlementError(ValueError):
    pass


class LifecycleSettlementIntegrityError(LifecycleSettlementError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _require_distinct_paths(*paths: str | Path) -> None:
    resolved = [Path(path).resolve() for path in paths]
    if len(resolved) != len(set(resolved)):
        raise LifecycleSettlementError("lifecycle stores must use four distinct filesystem paths")


def _reference_spec(suffix: str) -> ExecutionSpec:
    digest = "sha256:" + "6" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cold-lifecycle-settlement",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cold lifecycle settlement {suffix}",
        source_revision=f"source-cold-lifecycle-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://cold-lifecycle/{suffix}", digest),),
    )


@dataclass(frozen=True, slots=True)
class LifecyclePreparationReceipt:
    session_id: str
    running_session_record_digest: str
    context_id: str
    context_digest: str
    anchor_head_digest: str
    provider_key: str
    provider_job_id: str
    schema_version: str = "ge.lifecycle-preparation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.lifecycle-preparation-receipt.v1":
            raise ValueError("unsupported lifecycle preparation receipt schema")
        for name in ("session_id", "context_id", "provider_key", "provider_job_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("running_session_record_digest", "context_digest", "anchor_head_digest"):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PhysicalSettlementReport:
    context_id: str
    context_digest: str
    session_id: str
    result_digest: str
    outcome_digest: str
    reconciliation_plan_digest: str
    reconciliation_receipt_digest: str
    committed_head_digest: str
    durable_session_state: Literal["running"]
    durable_session_record_digest: str
    schema_version: str = "ge.physical-settlement-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.physical-settlement-report.v1":
            raise ValueError("unsupported physical settlement report schema")
        if self.durable_session_state != "running":
            raise ValueError("physical settlement must not submit logical Session result")
        for name in ("context_id", "session_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "context_digest",
            "result_digest",
            "outcome_digest",
            "reconciliation_plan_digest",
            "reconciliation_receipt_digest",
            "committed_head_digest",
            "durable_session_record_digest",
        ):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class LogicalLifecycleAssessment:
    state: LogicalLifecycleState
    session_id: str
    durable_session_record_digest: str
    physical_state: str
    physical_assessment_digest: str
    result_digest: str | None = None
    schema_version: str = "ge.logical-lifecycle-assessment.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.logical-lifecycle-assessment.v1":
            raise ValueError("unsupported logical lifecycle assessment schema")
        if self.state not in {
            "physical_pending_session_running",
            "physical_settled_session_running",
            "logical_result_submitted",
            "logical_revoked",
        }:
            raise ValueError("unsupported logical lifecycle state")
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must be non-empty")
        _require_sha256("durable_session_record_digest", self.durable_session_record_digest)
        _require_sha256("physical_assessment_digest", self.physical_assessment_digest)
        if self.state == "logical_result_submitted":
            if self.result_digest is None:
                raise ValueError("logical_result_submitted requires result digest")
            _require_sha256("result_digest", self.result_digest)
        elif self.result_digest is not None:
            raise ValueError("only logical_result_submitted may carry result digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class LogicalSettlementReceipt:
    physical_assessment_digest: str
    session_settlement_receipt: SessionSettlementReceipt
    result_digest: str
    idempotent: bool
    schema_version: str = "ge.logical-settlement-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.logical-settlement-receipt.v1":
            raise ValueError("unsupported logical settlement receipt schema")
        _require_sha256("physical_assessment_digest", self.physical_assessment_digest)
        _require_sha256("result_digest", self.result_digest)
        if self.session_settlement_receipt.state != "result_submitted":
            raise ValueError("logical settlement receipt requires result_submitted Session receipt")
        if self.session_settlement_receipt.result_digest != self.result_digest:
            raise ValueError("logical settlement result digest mismatch")
        if self.idempotent != self.session_settlement_receipt.idempotent:
            raise ValueError("logical settlement idempotency mismatch")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def prepare_reference_cold_lifecycle(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    *,
    suffix: str = "1",
) -> LifecyclePreparationReceipt:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    runner = reattachable_reference_runner()
    spec = _reference_spec(suffix)
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-cold-lifecycle-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, session, runner, authorization)
    anchor = build_durable_snapshot(state, runner)
    _, recovery = recover_after_restart(anchor, runner)
    if len(recovery.active_leases) != 1:
        raise LifecycleSettlementError("lifecycle preparation requires exactly one active lease")
    recovered = recovery.active_leases[0]
    context = build_recovery_context(
        anchor, spec, registry, plan, session, runner, authorization, recovered
    )
    key = reattachment_key_from_authorization(authorization, runner)

    session_store = SQLiteSessionSettlementStore(session_store_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)

    if session_store.load(session.session_id) is not None:
        raise LifecycleSettlementError("Session store must be empty for new lifecycle fixture")
    if context_store.list_contexts():
        raise LifecycleSettlementError("recovery context store must be empty for new lifecycle fixture")
    if capacity_store.load_current(runner) is not None:
        raise LifecycleSettlementError("capacity store must be empty for new lifecycle fixture")
    if provider_store.lookup(key) is not None:
        raise LifecycleSettlementError("provider store must be empty for new lifecycle fixture")

    # Logical source state is made durable before physical work becomes recoverable.
    session_receipt = session_store.register_running(session)
    context_receipt = context_store.save(context, anchor)
    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=None)
    registered_key, registration = register_reference_invocation(provider_store, authorization, runner)
    if session_receipt.idempotent or context_receipt.idempotent or registration.idempotent:
        raise LifecycleSettlementError("new lifecycle fixture unexpectedly reused durable identity")
    if registered_key != key:
        raise LifecycleSettlementIntegrityError("provider registration changed deterministic key")

    return LifecyclePreparationReceipt(
        session_id=session.session_id,
        running_session_record_digest=session_receipt.committed_record_digest,
        context_id=context.context_id,
        context_digest=context.digest,
        anchor_head_digest=anchor.head.digest,
        provider_key=key.provider_key,
        provider_job_id=registration.job_id,
    )


def resume_reference_completed_physical_settlement(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> tuple[PhysicalSettlementReport, ResultEnvelope]:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    session_store = SQLiteSessionSettlementStore(session_store_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)

    bindings = bootstrap_active_recovery_contexts(context_store, capacity_store)
    if len(bindings) != 1:
        raise LifecycleSettlementError("physical settlement resume requires one active cold binding")
    binding = bindings[0]
    context = binding.context
    runner = binding.runner
    source = binding.current_snapshot
    recovered = binding.recovered_lease

    durable_session = session_store.load(context.session.session_id)
    if durable_session is None:
        raise LifecycleSettlementIntegrityError("reconstructed Session has no durable logical record")
    if durable_session != DurableSessionRecord(context.session, context.session):
        raise LifecycleSettlementIntegrityError("logical Session must still be exact durable running source")

    probe = build_status_probe(source, runner, recovered)
    running = query_reference_status(provider_store, probe)
    running_assessment, running_outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        running,
    )
    if running.status != "running" or running_assessment.disposition != "keep_running" or running_outcome is not None:
        raise LifecycleSettlementIntegrityError("provider must remain running before reference completion")
    if running.provider_invocation_id is None:
        raise LifecycleSettlementIntegrityError("running provider record must expose job identity")

    result = ResultEnvelope(
        session_id=context.session.session_id,
        spec_id=context.spec.spec_id,
        spec_digest=context.spec.digest,
        runner_id=runner.runner_id,
        attempt=context.session.attempt,
        status="completed",
        evidence=(),
        summary="Reference cold lifecycle completed physical work.",
    )
    physical = observe_completed(
        context.authorization,
        result,
        provider_invocation_id=running.provider_invocation_id,
    )
    key = reattachment_key_from_authorization(context.authorization, runner)
    record_reference_terminal(provider_store, key, physical)
    terminal = query_reference_status(provider_store, probe)
    terminal_assessment, outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        terminal,
    )
    if terminal_assessment.disposition != "terminal_outcome" or outcome is None:
        raise LifecycleSettlementIntegrityError("terminal provider state did not admit physical outcome")
    if outcome.result != result:
        raise LifecycleSettlementIntegrityError("admitted physical outcome changed completed result")

    plan = plan_provider_outcome_reconciliation(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        recovered,
        outcome,
    )
    committed, _, reconciliation_receipt = commit_reconciliation(capacity_store, runner, plan)
    if committed.state.active_leases:
        raise LifecycleSettlementIntegrityError("physical reconciliation did not release capacity")

    still_running = session_store.load(context.session.session_id)
    if still_running is None or still_running != durable_session or still_running.current_session.state != "running":
        raise LifecycleSettlementIntegrityError("physical reconciliation unexpectedly changed logical Session")

    return (
        PhysicalSettlementReport(
            context_id=context.context_id,
            context_digest=context.digest,
            session_id=context.session.session_id,
            result_digest=result.digest,
            outcome_digest=outcome.digest,
            reconciliation_plan_digest=plan.digest,
            reconciliation_receipt_digest=reconciliation_receipt.digest,
            committed_head_digest=committed.head.digest,
            durable_session_state="running",
            durable_session_record_digest=still_running.digest,
        ),
        result,
    )


def _reconstruct_reconciled_completed_outcome(
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> tuple[CutPointAssessment, object, object, PhysicalOutcomeBundle]:
    physical_assessment = assess_reference_cutpoint(
        capacity_store_path,
        provider_registry_path,
        recovery_context_store_path,
    )
    if physical_assessment.state != "settled_terminal_reconciliation":
        raise LifecycleSettlementError("logical result settlement requires settled terminal physical reconciliation")

    candidates = SQLiteRecoveryContextStore(recovery_context_store_path).bootstrap_candidates()
    if len(candidates) != 1:
        raise LifecycleSettlementError("logical result settlement requires one durable recovery context")
    context, runner = candidates[0]
    _, anchor_recovery = recover_after_restart(context.anchor_snapshot, runner)
    matches = [
        lease
        for lease in anchor_recovery.active_leases
        if lease.lease_id == context.recovered_lease_id
        and lease.lease_digest == context.recovered_lease_digest
    ]
    if len(matches) != 1:
        raise LifecycleSettlementIntegrityError("recovery context anchor does not reproduce its physical lease")
    probe = build_status_probe(context.anchor_snapshot, runner, matches[0])
    terminal = query_reference_status(SQLiteReferenceJobRegistry(provider_registry_path), probe)
    assessment, outcome = assess_provider_status(
        context.anchor_snapshot,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        terminal,
    )
    if assessment.disposition != "terminal_outcome" or outcome is None:
        raise LifecycleSettlementIntegrityError("durable provider terminal state did not reproduce physical outcome")
    if outcome.digest != physical_assessment.outcome_digest:
        raise LifecycleSettlementIntegrityError("reconstructed physical outcome differs from canonical reconciliation")
    if outcome.result is None:
        raise LifecycleSettlementError("settled physical outcome carries no logical result")
    return physical_assessment, context, runner, outcome


def settle_reference_reconciled_result(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> LogicalSettlementReceipt:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    physical_assessment, context, _, outcome = _reconstruct_reconciled_completed_outcome(
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    result = outcome.result
    assert result is not None
    store = SQLiteSessionSettlementStore(session_store_path)
    record = store.load(context.session.session_id)
    if record is None:
        raise LifecycleSettlementIntegrityError("reconciled Session has no durable logical state")
    if record.source_session != context.session:
        raise LifecycleSettlementIntegrityError("durable logical Session source differs from recovery context")

    try:
        receipt = store.submit_result(context.session, result)
    except SessionSettlementConflict:
        raise
    return LogicalSettlementReceipt(
        physical_assessment_digest=physical_assessment.digest,
        session_settlement_receipt=receipt,
        result_digest=result.digest,
        idempotent=receipt.idempotent,
    )


def assess_reference_logical_lifecycle(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> LogicalLifecycleAssessment:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    physical = assess_reference_cutpoint(
        capacity_store_path,
        provider_registry_path,
        recovery_context_store_path,
    )
    candidates = SQLiteRecoveryContextStore(recovery_context_store_path).bootstrap_candidates()
    if len(candidates) != 1:
        raise LifecycleSettlementError("logical lifecycle assessment requires one durable recovery context")
    context, _ = candidates[0]
    record = SQLiteSessionSettlementStore(session_store_path).load(context.session.session_id)
    if record is None:
        raise LifecycleSettlementIntegrityError("logical lifecycle has no durable Session record")
    if record.source_session != context.session:
        raise LifecycleSettlementIntegrityError("durable Session source differs from recovery context")

    if physical.state != "settled_terminal_reconciliation":
        if record.current_session.state != "running":
            raise LifecycleSettlementIntegrityError("logical Session settled before physical lifecycle settled")
        return LogicalLifecycleAssessment(
            state="physical_pending_session_running",
            session_id=record.session_id,
            durable_session_record_digest=record.digest,
            physical_state=physical.state,
            physical_assessment_digest=physical.digest,
        )

    if record.current_session.state == "running":
        return LogicalLifecycleAssessment(
            state="physical_settled_session_running",
            session_id=record.session_id,
            durable_session_record_digest=record.digest,
            physical_state=physical.state,
            physical_assessment_digest=physical.digest,
        )
    if record.current_session.state == "revoked":
        return LogicalLifecycleAssessment(
            state="logical_revoked",
            session_id=record.session_id,
            durable_session_record_digest=record.digest,
            physical_state=physical.state,
            physical_assessment_digest=physical.digest,
        )
    if record.result is None or record.current_session.result_digest != record.result.digest:
        raise LifecycleSettlementIntegrityError("submitted durable Session lacks exact result binding")
    _, _, _, outcome = _reconstruct_reconciled_completed_outcome(
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    if outcome.result != record.result:
        raise LifecycleSettlementIntegrityError("logical submitted result differs from reconciled physical result")
    return LogicalLifecycleAssessment(
        state="logical_result_submitted",
        session_id=record.session_id,
        durable_session_record_digest=record.digest,
        physical_state=physical.state,
        physical_assessment_digest=physical.digest,
        result_digest=record.result.digest,
    )
