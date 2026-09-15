from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import initialize_capacity_state, reserve_capacity
from .durable import RecoveredInFlightLease, build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ExecutionSession, ExecutionSpec, ResultEnvelope, RunnerRegistry
from .persistence import SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_completed, observe_failure
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import RecoveryReconciliationReceipt, commit_reconciliation, plan_provider_outcome_reconciliation
from .reference_bridge import query_reference_status, reattachable_reference_runner, record_reference_terminal, register_reference_invocation
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session

RehearsalTerminalKind = Literal["timed_out", "completed"]
RehearsalContextMode = Literal["caller_retained"]


class RehearsalError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class StoreReopenRehearsalReport:
    terminal_kind: RehearsalTerminalKind
    provider_key: str
    provider_job_id: str
    initial_head_digest: str
    recovered_head_digest: str
    recovered_lease_id: str
    running_status_digest: str
    running_assessment_digest: str
    terminal_status_digest: str
    outcome_digest: str
    reconciliation_plan_digest: str
    reconciliation_receipt_digest: str
    committed_head_digest: str
    session_state_after_reconciliation: str
    logical_result_digest: str | None = None
    context_mode: RehearsalContextMode = "caller_retained"
    schema_version: str = "ge.store-reopen-rehearsal-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.store-reopen-rehearsal-report.v1":
            raise ValueError("unsupported store reopen rehearsal report schema")
        if self.context_mode != "caller_retained":
            raise ValueError("v0.0.10 rehearsal context must be caller_retained")
        if self.terminal_kind not in {"timed_out", "completed"}:
            raise ValueError("unsupported rehearsal terminal kind")
        for name in ("provider_key", "provider_job_id", "recovered_lease_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "initial_head_digest",
            "recovered_head_digest",
            "running_status_digest",
            "running_assessment_digest",
            "terminal_status_digest",
            "outcome_digest",
            "reconciliation_plan_digest",
            "reconciliation_receipt_digest",
            "committed_head_digest",
        ):
            _require_sha256(name, getattr(self, name))
        if self.initial_head_digest != self.recovered_head_digest:
            raise ValueError("store reopen must recover the exact initial durable head")
        if self.session_state_after_reconciliation != "running":
            raise ValueError("reconciliation must not submit or revoke the logical Session")
        if self.terminal_kind == "completed":
            if self.logical_result_digest is None:
                raise ValueError("completed rehearsal must expose logical result digest")
            _require_sha256("logical_result_digest", self.logical_result_digest)
        elif self.logical_result_digest is not None:
            raise ValueError("timed_out rehearsal cannot expose logical result digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ReferenceStoreReopenRehearsal:
    report: StoreReopenRehearsalReport
    session: ExecutionSession
    recovered_lease: RecoveredInFlightLease
    outcome: PhysicalOutcomeBundle
    result: ResultEnvelope | None
    reconciliation_receipt: RecoveryReconciliationReceipt
    schema_version: str = "ge.reference-store-reopen-rehearsal.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reference-store-reopen-rehearsal.v1":
            raise ValueError("unsupported reference store reopen rehearsal schema")
        if self.report.context_mode != "caller_retained":
            raise ValueError("reference store reopen rehearsal requires caller-retained execution context")
        if self.session.state != "running" or self.report.session_state_after_reconciliation != self.session.state:
            raise ValueError("rehearsal must preserve logical Session as running")
        if self.report.recovered_lease_id != self.recovered_lease.lease_id:
            raise ValueError("rehearsal report does not bind the recovered lease")
        if self.report.outcome_digest != self.outcome.digest:
            raise ValueError("rehearsal report does not bind the physical outcome")
        if self.report.reconciliation_receipt_digest != self.reconciliation_receipt.digest:
            raise ValueError("rehearsal report does not bind the reconciliation receipt")
        if self.outcome.result != self.result:
            raise ValueError("rehearsal result must equal physical outcome result")
        if self.report.terminal_kind == "completed":
            if self.result is None or self.report.logical_result_digest != self.result.digest:
                raise ValueError("completed rehearsal result binding mismatch")
        elif self.result is not None or self.report.logical_result_digest is not None:
            raise ValueError("timed_out rehearsal cannot carry result")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _reference_spec(suffix: str) -> ExecutionSpec:
    input_digest = "sha256:" + "d" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-store-reopen-rehearsal",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable store reopen rehearsal {suffix}",
        source_revision=f"source-store-reopen-rehearsal-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://store-reopen-rehearsal/{suffix}", input_digest),),
    )


def run_reference_store_reopen_rehearsal(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    *,
    terminal_kind: RehearsalTerminalKind = "timed_out",
    suffix: str = "1",
) -> ReferenceStoreReopenRehearsal:
    if terminal_kind not in {"timed_out", "completed"}:
        raise RehearsalError("terminal_kind must be timed_out or completed")
    if Path(capacity_store_path).resolve() == Path(provider_registry_path).resolve():
        raise RehearsalError("capacity store and provider registry must use distinct files")

    # v0.0.10 intentionally retains immutable execution context in the caller.
    # It proves durable-store reopen semantics, not yet cold coordinator reconstruction.
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
        invocation_id=f"gei-store-reopen-rehearsal-{suffix}",
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
    source = build_durable_snapshot(state, runner)

    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    if capacity_store.load_current(runner) is not None:
        raise RehearsalError("capacity store must be empty for a new rehearsal")
    provider_registry = SQLiteReferenceJobRegistry(provider_registry_path)
    expected_key = reattachment_key_from_authorization(authorization, runner)
    if provider_registry.lookup(expected_key) is not None:
        raise RehearsalError("provider key must be absent for a new rehearsal")

    capacity_store.compare_and_swap(source, runner, expected_head_digest=None)
    key, registration = register_reference_invocation(provider_registry, authorization, runner)
    if key != expected_key or registration.idempotent:
        raise RehearsalError("provider registration did not create the expected fresh identity")

    # Durable-store reopen boundary. Protocol context above is deliberately caller-retained.
    reopened_capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    recovered_source = reopened_capacity_store.load_current(runner)
    if recovered_source is None or recovered_source != source:
        raise RehearsalError("capacity head did not survive store reopen")
    _, recovery_report = recover_after_restart(recovered_source, runner)
    if len(recovery_report.active_leases) != 1:
        raise RehearsalError("store reopen rehearsal requires exactly one recovered in-flight lease")
    recovered = recovery_report.active_leases[0]
    probe = build_status_probe(recovered_source, runner, recovered)

    reopened_provider_registry = SQLiteReferenceJobRegistry(provider_registry_path)
    running_status = query_reference_status(reopened_provider_registry, probe)
    if running_status.status != "running" or running_status.provider_invocation_id != registration.job_id:
        raise RehearsalError("provider running identity did not survive store reopen")
    running_assessment, running_outcome = assess_provider_status(
        recovered_source,
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
        raise RehearsalError("running provider status must preserve in-flight occupancy")
    if not recovered_source.state.active_leases:
        raise RehearsalError("running provider status unexpectedly released recovered capacity")

    result: ResultEnvelope | None
    if terminal_kind == "timed_out":
        physical = observe_failure(
            authorization,
            "timed_out",
            failure_code="reference.rehearsal.timeout",
            provider_invocation_id=registration.job_id,
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
            summary="Reference provider completed after durable-store reopen.",
        )
        physical = observe_completed(
            authorization,
            result,
            provider_invocation_id=registration.job_id,
        )

    record_reference_terminal(reopened_provider_registry, key, physical)
    terminal_status = query_reference_status(reopened_provider_registry, probe)
    if terminal_status.status != "terminal":
        raise RehearsalError("reference provider did not expose terminal status")

    terminal_assessment, outcome = assess_provider_status(
        recovered_source,
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
        raise RehearsalError("terminal provider status did not admit a physical outcome")

    reconciliation_plan = plan_provider_outcome_reconciliation(
        recovered_source,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        recovered,
        outcome,
    )
    committed, _, reconciliation_receipt = commit_reconciliation(
        reopened_capacity_store,
        runner,
        reconciliation_plan,
    )
    if committed.state.active_leases:
        raise RehearsalError("reconciliation did not release recovered capacity")
    if session.state != "running":
        raise RehearsalError("reconciliation unexpectedly changed logical Session state")

    report = StoreReopenRehearsalReport(
        terminal_kind=terminal_kind,
        provider_key=key.provider_key,
        provider_job_id=registration.job_id,
        initial_head_digest=source.head.digest,
        recovered_head_digest=recovered_source.head.digest,
        recovered_lease_id=recovered.lease_id,
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
    return ReferenceStoreReopenRehearsal(
        report=report,
        session=session,
        recovered_lease=recovered,
        outcome=outcome,
        result=result,
        reconciliation_receipt=reconciliation_receipt,
    )
