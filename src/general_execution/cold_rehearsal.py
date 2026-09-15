from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import initialize_capacity_state, reserve_capacity
from .cold_bootstrap import ColdRecoveryBinding, bootstrap_active_recovery_contexts
from .durable import build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ExecutionSession, ExecutionSpec, ResultEnvelope, RunnerRegistry
from .persistence import PersistenceCommitReceipt, SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_completed, observe_failure
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import RecoveryReconciliationReceipt, commit_reconciliation, plan_provider_outcome_reconciliation
from .recovery_context import (
    DurableRecoveryContext,
    RecoveryContextCommitReceipt,
    SQLiteRecoveryContextStore,
    build_recovery_context,
)
from .reference_bridge import (
    ReferenceRegistrationReceipt,
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session

ColdTerminalKind = Literal["timed_out", "completed"]
COLD_CONTEXT_MODE = "cold_reconstructed"


class ColdRehearsalError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _distinct_paths(*paths: str | Path) -> bool:
    resolved = [Path(path).resolve() for path in paths]
    return len(resolved) == len(set(resolved))


@dataclass(frozen=True, slots=True)
class ColdRestartPreparationReceipt:
    context_id: str
    context_digest: str
    context_commit_digest: str
    authorization_id: str
    anchor_head_digest: str
    capacity_commit_digest: str
    provider_key: str
    provider_job_id: str
    provider_registration_digest: str
    schema_version: str = "ge.cold-restart-preparation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cold-restart-preparation-receipt.v1":
            raise ValueError("unsupported cold restart preparation receipt schema")
        for name in ("context_id", "authorization_id", "provider_key", "provider_job_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "context_digest",
            "context_commit_digest",
            "anchor_head_digest",
            "capacity_commit_digest",
            "provider_registration_digest",
        ):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ColdRestartRehearsalReport:
    terminal_kind: ColdTerminalKind
    context_mode: Literal["cold_reconstructed"]
    context_id: str
    context_digest: str
    runner_id: str
    authorization_id: str
    source_head_digest: str
    recovered_lease_id: str
    provider_key: str
    provider_job_id: str
    running_status_digest: str
    running_assessment_digest: str
    terminal_status_digest: str
    outcome_digest: str
    reconciliation_plan_digest: str
    reconciliation_receipt_digest: str
    committed_head_digest: str
    session_state_after_reconciliation: str
    logical_result_digest: str | None = None
    schema_version: str = "ge.cold-restart-rehearsal-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cold-restart-rehearsal-report.v1":
            raise ValueError("unsupported cold restart rehearsal report schema")
        if self.terminal_kind not in {"timed_out", "completed"}:
            raise ValueError("unsupported cold rehearsal terminal kind")
        if self.context_mode != COLD_CONTEXT_MODE:
            raise ValueError("cold rehearsal context_mode must be cold_reconstructed")
        for name in (
            "context_id",
            "runner_id",
            "authorization_id",
            "recovered_lease_id",
            "provider_key",
            "provider_job_id",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "context_digest",
            "source_head_digest",
            "running_status_digest",
            "running_assessment_digest",
            "terminal_status_digest",
            "outcome_digest",
            "reconciliation_plan_digest",
            "reconciliation_receipt_digest",
            "committed_head_digest",
        ):
            _require_sha256(name, getattr(self, name))
        if self.session_state_after_reconciliation != "running":
            raise ValueError("cold reconciliation must leave logical Session running")
        if self.terminal_kind == "completed":
            if self.logical_result_digest is None:
                raise ValueError("completed cold rehearsal requires logical_result_digest")
            _require_sha256("logical_result_digest", self.logical_result_digest)
        elif self.logical_result_digest is not None:
            raise ValueError("timed_out cold rehearsal cannot carry logical_result_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ReferenceColdRestartRehearsal:
    report: ColdRestartRehearsalReport
    context: DurableRecoveryContext
    reconstructed_session: ExecutionSession
    outcome: PhysicalOutcomeBundle
    result: ResultEnvelope | None
    reconciliation_receipt: RecoveryReconciliationReceipt
    schema_version: str = "ge.reference-cold-restart-rehearsal.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reference-cold-restart-rehearsal.v1":
            raise ValueError("unsupported reference cold restart rehearsal schema")
        if self.report.context_mode != COLD_CONTEXT_MODE:
            raise ValueError("reference cold rehearsal must use reconstructed context")
        if self.report.context_id != self.context.context_id or self.report.context_digest != self.context.digest:
            raise ValueError("cold rehearsal report does not bind reconstructed context")
        if self.reconstructed_session != self.context.session:
            raise ValueError("cold rehearsal Session must come from reconstructed context")
        if self.reconstructed_session.state != "running":
            raise ValueError("cold rehearsal must preserve logical Session as running")
        if self.report.outcome_digest != self.outcome.digest:
            raise ValueError("cold rehearsal report does not bind physical outcome")
        if self.report.reconciliation_receipt_digest != self.reconciliation_receipt.digest:
            raise ValueError("cold rehearsal report does not bind reconciliation receipt")
        if self.outcome.result != self.result:
            raise ValueError("cold rehearsal result must equal physical outcome result")
        if self.report.terminal_kind == "completed":
            if self.result is None or self.report.logical_result_digest != self.result.digest:
                raise ValueError("completed cold rehearsal result binding mismatch")
        elif self.result is not None or self.report.logical_result_digest is not None:
            raise ValueError("timed_out cold rehearsal cannot carry result")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _reference_spec(suffix: str) -> ExecutionSpec:
    input_digest = "sha256:" + "b" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cold-restart-rehearsal",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cold coordinator reconstruction rehearsal {suffix}",
        source_revision=f"source-cold-restart-rehearsal-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://cold-restart-rehearsal/{suffix}", input_digest),),
    )


def prepare_reference_cold_restart(
    capacity_store_path: str | Path,
    context_store_path: str | Path,
    provider_registry_path: str | Path,
    *,
    suffix: str = "1",
) -> ColdRestartPreparationReceipt:
    if not _distinct_paths(capacity_store_path, context_store_path, provider_registry_path):
        raise ColdRehearsalError("capacity, recovery-context, and provider stores must use distinct files")

    runner = reattachable_reference_runner()
    spec = _reference_spec(suffix)
    registry = RunnerRegistry((runner,))
    execution_plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, execution_plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        execution_plan,
        session,
        runner,
        invocation_id=f"gei-cold-restart-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(
        state,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
    )
    anchor = build_durable_snapshot(state, runner)
    _, recovery_report = recover_after_restart(anchor, runner)
    if len(recovery_report.active_leases) != 1:
        raise ColdRehearsalError("cold preparation requires exactly one active lease")
    recovered = recovery_report.active_leases[0]
    context = build_recovery_context(
        anchor,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
        recovered,
    )

    context_store = SQLiteRecoveryContextStore(context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_registry = SQLiteReferenceJobRegistry(provider_registry_path)
    if context_store.list_contexts():
        raise ColdRehearsalError("recovery-context store must be empty for a new rehearsal")
    if capacity_store.load_current(runner) is not None:
        raise ColdRehearsalError("capacity store must be empty for a new rehearsal")
    provider_key = reattachment_key_from_authorization(authorization, runner)
    if provider_registry.lookup(provider_key) is not None:
        raise ColdRehearsalError("provider key must be absent for a new rehearsal")

    # Fail-safe ordering: context -> capacity -> provider identity.
    context_receipt: RecoveryContextCommitReceipt = context_store.save(context, anchor)
    if context_receipt.idempotent:
        raise ColdRehearsalError("fresh recovery context unexpectedly replayed")
    capacity_receipt: PersistenceCommitReceipt = capacity_store.compare_and_swap(
        anchor, runner, expected_head_digest=None
    )
    provider_key, registration = register_reference_invocation(
        provider_registry, authorization, runner
    )
    if registration.idempotent:
        raise ColdRehearsalError("fresh provider registration unexpectedly replayed")

    return ColdRestartPreparationReceipt(
        context_id=context.context_id,
        context_digest=context.digest,
        context_commit_digest=context_receipt.digest,
        authorization_id=authorization.authorization_id,
        anchor_head_digest=anchor.head.digest,
        capacity_commit_digest=capacity_receipt.digest,
        provider_key=provider_key.provider_key,
        provider_job_id=registration.job_id,
        provider_registration_digest=registration.digest,
    )


def _single_cold_binding(
    capacity_store_path: str | Path,
    context_store_path: str | Path,
) -> ColdRecoveryBinding:
    bindings = bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(context_store_path),
        SQLiteDurableHeadStore(capacity_store_path),
    )
    if len(bindings) != 1:
        raise ColdRehearsalError("cold resume requires exactly one active recoverable context")
    return bindings[0]


def resume_reference_cold_restart(
    capacity_store_path: str | Path,
    context_store_path: str | Path,
    provider_registry_path: str | Path,
    *,
    terminal_kind: ColdTerminalKind = "timed_out",
) -> ReferenceColdRestartRehearsal:
    if terminal_kind not in {"timed_out", "completed"}:
        raise ColdRehearsalError("terminal_kind must be timed_out or completed")
    if not _distinct_paths(capacity_store_path, context_store_path, provider_registry_path):
        raise ColdRehearsalError("capacity, recovery-context, and provider stores must use distinct files")

    # No caller-retained protocol objects enter this phase.
    binding = _single_cold_binding(capacity_store_path, context_store_path)
    context = binding.context
    runner = binding.runner
    source = binding.current_snapshot
    recovered = binding.recovered_lease
    spec = context.spec
    registry = context.registry
    execution_plan = context.plan
    session = context.session
    authorization = context.authorization

    provider_registry = SQLiteReferenceJobRegistry(provider_registry_path)
    probe = build_status_probe(source, runner, recovered)
    running_status = query_reference_status(provider_registry, probe)
    if running_status.status != "running" or not running_status.provider_invocation_id:
        raise ColdRehearsalError("cold resume requires a running provider identity")
    running_assessment, running_outcome = assess_provider_status(
        source,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
        probe,
        running_status,
    )
    if running_assessment.disposition != "keep_running" or running_outcome is not None:
        raise ColdRehearsalError("running provider status must preserve recovered occupancy")

    result: ResultEnvelope | None
    if terminal_kind == "timed_out":
        physical = observe_failure(
            authorization,
            "timed_out",
            failure_code="reference.cold-rehearsal.timeout",
            provider_invocation_id=running_status.provider_invocation_id,
        )
        result = None
    else:
        result = ResultEnvelope(
            session_id=session.session_id,
            spec_id=spec.spec_id,
            spec_digest=spec.digest,
            runner_id=runner.runner_id,
            attempt=session.attempt,
            status="completed",
            evidence=(),
            summary="Reference provider completed after cold context reconstruction.",
        )
        physical = observe_completed(
            authorization,
            result,
            provider_invocation_id=running_status.provider_invocation_id,
        )

    provider_key = reattachment_key_from_authorization(authorization, runner)
    record_reference_terminal(provider_registry, provider_key, physical)
    terminal_status = query_reference_status(provider_registry, probe)
    if terminal_status.status != "terminal":
        raise ColdRehearsalError("provider did not expose terminal state after cold reconstruction")

    terminal_assessment, outcome = assess_provider_status(
        source,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
        probe,
        terminal_status,
    )
    if terminal_assessment.disposition != "terminal_outcome" or outcome is None:
        raise ColdRehearsalError("terminal provider status did not admit physical outcome")

    reconciliation_plan = plan_provider_outcome_reconciliation(
        source,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        recovered,
        outcome,
    )
    committed, _, reconciliation_receipt = commit_reconciliation(
        SQLiteDurableHeadStore(capacity_store_path),
        runner,
        reconciliation_plan,
    )
    if committed.state.active_leases:
        raise ColdRehearsalError("cold reconciliation did not release recovered capacity")
    if session.state != "running":
        raise ColdRehearsalError("cold reconciliation unexpectedly changed logical Session")

    report = ColdRestartRehearsalReport(
        terminal_kind=terminal_kind,
        context_mode=COLD_CONTEXT_MODE,
        context_id=context.context_id,
        context_digest=context.digest,
        runner_id=runner.runner_id,
        authorization_id=authorization.authorization_id,
        source_head_digest=source.head.digest,
        recovered_lease_id=recovered.lease_id,
        provider_key=provider_key.provider_key,
        provider_job_id=running_status.provider_invocation_id,
        running_status_digest=running_status.digest,
        running_assessment_digest=running_assessment.digest,
        terminal_status_digest=terminal_status.digest,
        outcome_digest=outcome.digest,
        reconciliation_plan_digest=reconciliation_plan.digest,
        reconciliation_receipt_digest=reconciliation_receipt.digest,
        committed_head_digest=committed.head.digest,
        session_state_after_reconciliation=session.state,
        logical_result_digest=result.digest if result else None,
    )
    return ReferenceColdRestartRehearsal(
        report=report,
        context=context,
        reconstructed_session=session,
        outcome=outcome,
        result=result,
        reconciliation_receipt=reconciliation_receipt,
    )
