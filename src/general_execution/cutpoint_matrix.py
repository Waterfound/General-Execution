from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import initialize_capacity_state, reserve_capacity
from .cold_bootstrap import ColdRecoveryBinding, bootstrap_active_recovery_contexts
from .durable import build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ExecutionSpec, RunnerRegistry
from .persistence import SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_failure
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import (
    RecoveryReconciliationPlan,
    commit_reconciliation,
    plan_provider_outcome_reconciliation,
)
from .recovery_context import SQLiteRecoveryContextStore, build_recovery_context
from .reference_bridge import (
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session

CutPointName = Literal[
    "context_only",
    "capacity_committed",
    "provider_running",
    "terminal_persisted",
    "reconciliation_planned",
    "reconciled",
]
SafeDisposition = Literal[
    "orphan_context",
    "remain_unknown",
    "keep_running",
    "terminal_pending_reconciliation",
    "terminal_plan_reproducible",
    "reconciled",
]
ProviderState = Literal["absent", "not_found", "running", "terminal"]

CUT_POINT_ORDER: tuple[CutPointName, ...] = (
    "context_only",
    "capacity_committed",
    "provider_running",
    "terminal_persisted",
    "reconciliation_planned",
    "reconciled",
)


class CutPointMatrixError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class CutPointObservation:
    cut_point: CutPointName
    disposition: SafeDisposition
    context_count: int
    active_binding_count: int
    active_lease_count: int
    provider_state: ProviderState
    context_digest: str
    capacity_head_digest: str | None = None
    provider_record_digest: str | None = None
    status_observation_digest: str | None = None
    assessment_digest: str | None = None
    outcome_digest: str | None = None
    reconciliation_plan_digest: str | None = None
    schema_version: str = "ge.cut-point-observation.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cut-point-observation.v1":
            raise ValueError("unsupported cut-point observation schema")
        if self.cut_point not in CUT_POINT_ORDER:
            raise ValueError("unsupported cut point")
        if self.context_count < 1:
            raise ValueError("cut-point matrix requires at least one durable context")
        if self.active_binding_count < 0 or self.active_lease_count < 0:
            raise ValueError("counts must be >= 0")
        _require_sha256("context_digest", self.context_digest)
        for name in (
            "capacity_head_digest",
            "provider_record_digest",
            "status_observation_digest",
            "assessment_digest",
            "outcome_digest",
            "reconciliation_plan_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_sha256(name, value)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RestartCutPointMatrixReport:
    observations: tuple[CutPointObservation, ...]
    schema_version: str = "ge.restart-cut-point-matrix-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.restart-cut-point-matrix-report.v1":
            raise ValueError("unsupported restart cut-point matrix report schema")
        if tuple(item.cut_point for item in self.observations) != CUT_POINT_ORDER:
            raise ValueError("cut-point matrix observations must use the canonical order")
        expected = {
            "context_only": "orphan_context",
            "capacity_committed": "remain_unknown",
            "provider_running": "keep_running",
            "terminal_persisted": "terminal_pending_reconciliation",
            "reconciliation_planned": "terminal_plan_reproducible",
            "reconciled": "reconciled",
        }
        for item in self.observations:
            if item.disposition != expected[item.cut_point]:
                raise ValueError("cut-point disposition does not match canonical safe state")
        terminal = self.observations[3]
        planned = self.observations[4]
        if terminal.capacity_head_digest != planned.capacity_head_digest:
            raise ValueError("planning must not mutate the durable capacity head")
        if terminal.provider_record_digest != planned.provider_record_digest:
            raise ValueError("planning must not mutate provider terminal state")
        if terminal.reconciliation_plan_digest != planned.reconciliation_plan_digest:
            raise ValueError("reconciliation plan must reproduce after volatile loss")
        if self.observations[-1].active_lease_count != 0:
            raise ValueError("reconciled cut point must have zero active leases")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _reference_spec(suffix: str) -> ExecutionSpec:
    input_digest = "sha256:" + "c" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cut-point-matrix",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Restart cut-point matrix {suffix}",
        source_revision=f"source-cut-point-matrix-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://cut-point-matrix/{suffix}", input_digest),),
    )


def _active_binding(
    context_store: SQLiteRecoveryContextStore,
    capacity_store: SQLiteDurableHeadStore,
) -> ColdRecoveryBinding | None:
    bindings = bootstrap_active_recovery_contexts(context_store, capacity_store)
    if len(bindings) > 1:
        raise CutPointMatrixError("reference cut-point matrix expected at most one active binding")
    return bindings[0] if bindings else None


def _provider_record_digest(
    context_store: SQLiteRecoveryContextStore,
    provider_store: SQLiteReferenceJobRegistry,
) -> tuple[str, ProviderState]:
    candidates = context_store.bootstrap_candidates()
    if len(candidates) != 1:
        raise CutPointMatrixError("reference matrix requires exactly one durable context")
    context, runner = candidates[0]
    key = reattachment_key_from_authorization(context.authorization, runner)
    record = provider_store.lookup(key)
    if record is None:
        return "", "absent"
    return record.digest, record.state


def _observe_cut_point(
    cut_point: CutPointName,
    context_store: SQLiteRecoveryContextStore,
    capacity_store: SQLiteDurableHeadStore,
    provider_store: SQLiteReferenceJobRegistry,
) -> tuple[CutPointObservation, PhysicalOutcomeBundle | None, RecoveryReconciliationPlan | None]:
    candidates = context_store.bootstrap_candidates()
    if len(candidates) != 1:
        raise CutPointMatrixError("reference matrix requires exactly one durable context")
    candidate, runner = candidates[0]
    current = capacity_store.load_current(runner)
    binding = _active_binding(context_store, capacity_store)
    provider_record_digest, provider_record_state = _provider_record_digest(context_store, provider_store)

    capacity_head_digest = current.head.digest if current is not None else None
    active_lease_count = len(current.state.active_leases) if current is not None else 0
    status_digest = None
    assessment_digest = None
    outcome: PhysicalOutcomeBundle | None = None
    plan: RecoveryReconciliationPlan | None = None

    if current is None:
        provider_state: ProviderState = "absent" if not provider_record_digest else provider_record_state
    elif binding is not None:
        context = binding.context
        probe = build_status_probe(current, runner, binding.recovered_lease)
        status = query_reference_status(provider_store, probe)
        provider_state = status.status
        status_digest = status.digest
        assessment, outcome = assess_provider_status(
            current,
            context.spec,
            context.registry,
            context.plan,
            context.session,
            runner,
            context.authorization,
            probe,
            status,
        )
        assessment_digest = assessment.digest
        if outcome is not None:
            plan = plan_provider_outcome_reconciliation(
                current,
                context.spec,
                context.registry,
                context.plan,
                context.session,
                runner,
                binding.recovered_lease,
                outcome,
            )
    else:
        provider_state = provider_record_state if provider_record_digest else "absent"

    dispositions: dict[CutPointName, SafeDisposition] = {
        "context_only": "orphan_context",
        "capacity_committed": "remain_unknown",
        "provider_running": "keep_running",
        "terminal_persisted": "terminal_pending_reconciliation",
        "reconciliation_planned": "terminal_plan_reproducible",
        "reconciled": "reconciled",
    }
    observation = CutPointObservation(
        cut_point=cut_point,
        disposition=dispositions[cut_point],
        context_count=len(candidates),
        active_binding_count=1 if binding is not None else 0,
        active_lease_count=active_lease_count,
        provider_state=provider_state,
        context_digest=candidate.digest,
        capacity_head_digest=capacity_head_digest,
        provider_record_digest=provider_record_digest or None,
        status_observation_digest=status_digest,
        assessment_digest=assessment_digest,
        outcome_digest=outcome.digest if outcome is not None else None,
        reconciliation_plan_digest=plan.digest if plan is not None else None,
    )
    return observation, outcome, plan


def run_reference_cut_point_matrix(
    root: str | Path,
    *,
    suffix: str = "1",
) -> RestartCutPointMatrixReport:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    capacity_path = root / "capacity.db"
    context_path = root / "context.db"
    provider_path = root / "provider.db"

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
        invocation_id=f"gei-cut-point-matrix-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(
        state, spec, registry, execution_plan, session, runner, authorization
    )
    anchor = build_durable_snapshot(state, runner)
    _, recovery_report = recover_after_restart(anchor, runner)
    if len(recovery_report.active_leases) != 1:
        raise CutPointMatrixError("reference matrix requires exactly one active lease")
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

    context_store = SQLiteRecoveryContextStore(context_path)
    capacity_store = SQLiteDurableHeadStore(capacity_path)
    provider_store = SQLiteReferenceJobRegistry(provider_path)
    if context_store.list_contexts() or capacity_store.load_current(runner) is not None:
        raise CutPointMatrixError("cut-point matrix requires fresh durable stores")

    observations: list[CutPointObservation] = []

    # 1. Context is durable but no capacity head exists: safe orphan.
    context_store.save(context, anchor)
    item, _, _ = _observe_cut_point(
        "context_only", context_store, capacity_store, provider_store
    )
    if item.active_binding_count != 0 or item.active_lease_count != 0:
        raise CutPointMatrixError("context-only cut point must not expose active work")
    observations.append(item)

    # 2. Capacity becomes canonical before provider identity exists.
    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=None)
    item, outcome, _ = _observe_cut_point(
        "capacity_committed", context_store, capacity_store, provider_store
    )
    if item.provider_state != "not_found" or outcome is not None or item.active_lease_count != 1:
        raise CutPointMatrixError("capacity-without-provider must remain unknown and occupied")
    observations.append(item)

    # 3. Provider identity is durable and running.
    key, registration = register_reference_invocation(provider_store, authorization, runner)
    if registration.idempotent:
        raise CutPointMatrixError("fresh provider registration unexpectedly replayed")
    item, outcome, _ = _observe_cut_point(
        "provider_running", context_store, capacity_store, provider_store
    )
    if item.provider_state != "running" or outcome is not None or item.active_lease_count != 1:
        raise CutPointMatrixError("running provider must keep capacity occupied")
    observations.append(item)

    # 4. Provider terminal state is durable, capacity is still occupied.
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.cut-point.timeout",
        provider_invocation_id=registration.job_id,
    )
    record_reference_terminal(provider_store, key, physical)
    item, outcome, plan = _observe_cut_point(
        "terminal_persisted", context_store, capacity_store, provider_store
    )
    if item.provider_state != "terminal" or outcome is None or plan is None or item.active_lease_count != 1:
        raise CutPointMatrixError("terminal persistence must not release capacity before reconciliation")
    observations.append(item)

    # 5. A reconciliation plan is computed and then treated as volatile/lost.
    volatile_plan_digest = plan.digest
    del plan
    item, outcome, reproduced_plan = _observe_cut_point(
        "reconciliation_planned", context_store, capacity_store, provider_store
    )
    if (
        outcome is None
        or reproduced_plan is None
        or reproduced_plan.digest != volatile_plan_digest
        or item.active_lease_count != 1
    ):
        raise CutPointMatrixError("reconciliation plan did not reproduce from durable terminal state")
    observations.append(item)

    # 6. Only the CAS commit releases canonical capacity.
    binding = _active_binding(context_store, capacity_store)
    if binding is None:
        raise CutPointMatrixError("active binding disappeared before reconciliation commit")
    commit_reconciliation(capacity_store, runner, reproduced_plan)
    item, _, _ = _observe_cut_point(
        "reconciled", context_store, capacity_store, provider_store
    )
    if item.active_binding_count != 0 or item.active_lease_count != 0 or item.provider_state != "terminal":
        raise CutPointMatrixError("reconciled cut point must free capacity while preserving terminal provider state")
    observations.append(item)

    return RestartCutPointMatrixReport(tuple(observations))
