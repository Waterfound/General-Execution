from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import initialize_capacity_state, reserve_capacity
from .cold_bootstrap import ColdRecoveryBinding, bootstrap_active_recovery_contexts
from .durable import build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ResultEnvelope, RunnerRegistry
from .persistence import SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_completed, observe_failure
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import RecoveryReconciliationReceipt, commit_reconciliation, plan_provider_outcome_reconciliation
from .recovery_context import SQLiteRecoveryContextStore, build_recovery_context
from .reference_bridge import (
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session
from .models import ExecutionSpec

ColdTerminalKind = Literal["timed_out", "completed"]


class ColdRehearsalError(ValueError):
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
        raise ColdRehearsalError("capacity, provider, and recovery-context stores must use distinct files")


@dataclass(frozen=True, slots=True)
class ColdRestartPreparationReceipt:
    context_id: str
    context_digest: str
    authorization_id: str
    session_id: str
    anchor_head_digest: str
    anchor_snapshot_digest: str
    provider_key: str
    provider_job_id: str
    schema_version: str = "ge.cold-restart-preparation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cold-restart-preparation-receipt.v1":
            raise ValueError("unsupported cold restart preparation receipt schema")
        for name in ("context_id", "authorization_id", "session_id", "provider_key", "provider_job_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("context_digest", "anchor_head_digest", "anchor_snapshot_digest"):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ColdRestartReport:
    terminal_kind: ColdTerminalKind
    context_mode: Literal["cold_reconstructed"]
    context_id: str
    context_digest: str
    provider_key: str
    provider_job_id: str
    source_head_digest: str
    recovered_lease_id: str
    running_status_digest: str
    running_assessment_digest: str
    terminal_status_digest: str
    outcome_digest: str
    reconciliation_plan_digest: str
    reconciliation_receipt_digest: str
    committed_head_digest: str
    reconstructed_session_id: str
    session_state_after_reconciliation: str
    logical_result_digest: str | None = None
    schema_version: str = "ge.cold-restart-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cold-restart-report.v1":
            raise ValueError("unsupported cold restart report schema")
        if self.terminal_kind not in {"timed_out", "completed"}:
            raise ValueError("unsupported cold restart terminal kind")
        if self.context_mode != "cold_reconstructed":
            raise ValueError("cold restart report must use cold_reconstructed context mode")
        if self.session_state_after_reconciliation != "running":
            raise ValueError("cold reconciliation must leave logical Session running")
        for name in (
            "context_id",
            "provider_key",
            "provider_job_id",
            "recovered_lease_id",
            "reconstructed_session_id",
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
        if self.terminal_kind == "completed":
            if self.logical_result_digest is None:
                raise ValueError("completed cold restart requires logical result digest")
            _require_sha256("logical_result_digest", self.logical_result_digest)
        elif self.logical_result_digest is not None:
            raise ValueError("timed_out cold restart cannot carry logical result digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ReferenceColdRestartRehearsal:
    report: ColdRestartReport
    binding: ColdRecoveryBinding
    outcome: PhysicalOutcomeBundle
    result: ResultEnvelope | None
    reconciliation_receipt: RecoveryReconciliationReceipt
    schema_version: str = "ge.reference-cold-restart-rehearsal.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reference-cold-restart-rehearsal.v1":
            raise ValueError("unsupported reference cold restart rehearsal schema")
        context = self.binding.context
        if self.report.context_id != context.context_id or self.report.context_digest != context.digest:
            raise ValueError("cold restart report does not bind reconstructed context")
        if self.report.recovered_lease_id != self.binding.recovered_lease.lease_id:
            raise ValueError("cold restart report does not bind recovered lease")
        if self.report.reconstructed_session_id != context.session.session_id:
            raise ValueError("cold restart report does not bind reconstructed Session")
        if self.report.outcome_digest != self.outcome.digest:
            raise ValueError("cold restart report does not bind physical outcome")
        if self.report.reconciliation_receipt_digest != self.reconciliation_receipt.digest:
            raise ValueError("cold restart report does not bind reconciliation receipt")
        if context.session.state != "running":
            raise ValueError("cold restart must reconstruct a running Session")
        if self.outcome.result != self.result:
            raise ValueError("cold restart result must equal physical outcome result")
        if self.report.terminal_kind == "completed":
            if self.result is None or self.report.logical_result_digest != self.result.digest:
                raise ValueError("completed cold restart result binding mismatch")
        elif self.result is not None or self.report.logical_result_digest is not None:
            raise ValueError("timed_out cold restart cannot carry result")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _reference_spec(suffix: str) -> ExecutionSpec:
    digest = "sha256:" + "b" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cold-restart-rehearsal",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cold restart rehearsal {suffix}",
        source_revision=f"source-cold-restart-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://cold-restart/{suffix}", digest),),
    )


def prepare_reference_cold_restart(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
    *,
    suffix: str = "1",
) -> ColdRestartPreparationReceipt:
    _require_distinct_paths(capacity_store_path, provider_registry_path, recovery_context_store_path)

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
        invocation_id=f"gei-cold-restart-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, session, runner, authorization)
    anchor = build_durable_snapshot(state, runner)
    _, recovery = recover_after_restart(anchor, runner)
    if len(recovery.active_leases) != 1:
        raise ColdRehearsalError("cold restart preparation requires exactly one active lease")
    recovered = recovery.active_leases[0]
    context = build_recovery_context(
        anchor, spec, registry, plan, session, runner, authorization, recovered
    )

    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)
    key = reattachment_key_from_authorization(authorization, runner)

    if context_store.list_contexts():
        raise ColdRehearsalError("recovery context store must be empty for a new rehearsal")
    if capacity_store.load_current(runner) is not None:
        raise ColdRehearsalError("capacity store must be empty for a new rehearsal")
    if provider_store.lookup(key) is not None:
        raise ColdRehearsalError("provider key must be absent for a new rehearsal")

    context_receipt = context_store.save(context, anchor)
    if context_receipt.idempotent:
        raise ColdRehearsalError("new rehearsal unexpectedly reused recovery context")
    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=None)
    registered_key, registration = register_reference_invocation(provider_store, authorization, runner)
    if registered_key != key or registration.idempotent:
        raise ColdRehearsalError("new rehearsal did not create expected provider identity")

    return ColdRestartPreparationReceipt(
        context_id=context.context_id,
        context_digest=context.digest,
        authorization_id=authorization.authorization_id,
        session_id=session.session_id,
        anchor_head_digest=anchor.head.digest,
        anchor_snapshot_digest=anchor.digest,
        provider_key=key.provider_key,
        provider_job_id=registration.job_id,
    )


def resume_reference_cold_restart(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
    *,
    terminal_kind: ColdTerminalKind = "timed_out",
) -> ReferenceColdRestartRehearsal:
    if terminal_kind not in {"timed_out", "completed"}:
        raise ColdRehearsalError("terminal_kind must be timed_out or completed")
    _require_distinct_paths(capacity_store_path, provider_registry_path, recovery_context_store_path)

    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    bindings = bootstrap_active_recovery_contexts(context_store, capacity_store)
    if len(bindings) != 1:
        raise ColdRehearsalError("cold restart rehearsal requires exactly one active durable recovery binding")
    binding = bindings[0]
    context = binding.context
    runner = binding.runner
    source = binding.current_snapshot
    recovered = binding.recovered_lease

    probe = build_status_probe(source, runner, recovered)
    running_status = query_reference_status(provider_store, probe)
    if running_status.status != "running" or running_status.provider_invocation_id is None:
        raise ColdRehearsalError("provider must be durably running at cold resume boundary")
    running_assessment, running_outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        running_status,
    )
    if running_assessment.disposition != "keep_running" or running_outcome is not None:
        raise ColdRehearsalError("running provider status must preserve recovered occupancy")

    result: ResultEnvelope | None
    if terminal_kind == "timed_out":
        result = None
        physical = observe_failure(
            context.authorization,
            "timed_out",
            failure_code="reference.cold-restart.timeout",
            provider_invocation_id=running_status.provider_invocation_id,
        )
    else:
        result = ResultEnvelope(
            session_id=context.session.session_id,
            spec_id=context.spec.spec_id,
            spec_digest=context.spec.digest,
            runner_id=runner.runner_id,
            attempt=context.session.attempt,
            status="completed",
            evidence=(),
            summary="Reference provider completed after cold coordinator restart.",
        )
        physical = observe_completed(
            context.authorization,
            result,
            provider_invocation_id=running_status.provider_invocation_id,
        )

    key = reattachment_key_from_authorization(context.authorization, runner)
    record_reference_terminal(provider_store, key, physical)
    terminal_status = query_reference_status(provider_store, probe)
    if terminal_status.status != "terminal":
        raise ColdRehearsalError("provider did not expose terminal status after cold resume")
    terminal_assessment, outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        terminal_status,
    )
    if terminal_assessment.disposition != "terminal_outcome" or outcome is None:
        raise ColdRehearsalError("terminal provider status did not admit physical outcome")

    reconciliation_plan = plan_provider_outcome_reconciliation(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        recovered,
        outcome,
    )
    committed, _, reconciliation_receipt = commit_reconciliation(
        capacity_store, runner, reconciliation_plan
    )
    if committed.state.active_leases:
        raise ColdRehearsalError("cold reconciliation did not release recovered capacity")
    if context.session.state != "running":
        raise ColdRehearsalError("cold reconciliation unexpectedly changed logical Session")

    report = ColdRestartReport(
        terminal_kind=terminal_kind,
        context_mode="cold_reconstructed",
        context_id=context.context_id,
        context_digest=context.digest,
        provider_key=key.provider_key,
        provider_job_id=running_status.provider_invocation_id,
        source_head_digest=source.head.digest,
        recovered_lease_id=recovered.lease_id,
        running_status_digest=running_status.digest,
        running_assessment_digest=running_assessment.digest,
        terminal_status_digest=terminal_status.digest,
        outcome_digest=outcome.digest,
        reconciliation_plan_digest=reconciliation_plan.digest,
        reconciliation_receipt_digest=reconciliation_receipt.digest,
        committed_head_digest=committed.head.digest,
        reconstructed_session_id=context.session.session_id,
        session_state_after_reconciliation=context.session.state,
        logical_result_digest=result.digest if result else None,
    )
    return ReferenceColdRestartRehearsal(
        report=report,
        binding=binding,
        outcome=outcome,
        result=result,
        reconciliation_receipt=reconciliation_receipt,
    )


def run_reference_cold_restart_rehearsal(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
    *,
    terminal_kind: ColdTerminalKind = "timed_out",
    suffix: str = "1",
) -> tuple[ColdRestartPreparationReceipt, ReferenceColdRestartRehearsal]:
    preparation = prepare_reference_cold_restart(
        capacity_store_path,
        provider_registry_path,
        recovery_context_store_path,
        suffix=suffix,
    )
    rehearsal = resume_reference_cold_restart(
        capacity_store_path,
        provider_registry_path,
        recovery_context_store_path,
        terminal_kind=terminal_kind,
    )
    if preparation.context_id != rehearsal.report.context_id:
        raise ColdRehearsalError("cold resume reconstructed a different recovery context")
    if preparation.context_digest != rehearsal.report.context_digest:
        raise ColdRehearsalError("cold resume reconstructed a different recovery context digest")
    if preparation.provider_key != rehearsal.report.provider_key:
        raise ColdRehearsalError("cold resume reconstructed a different provider key")
    if preparation.provider_job_id != rehearsal.report.provider_job_id:
        raise ColdRehearsalError("cold resume reconstructed a different provider job")
    return preparation, rehearsal
