from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND
from .canonical import sha256_digest
from .capacity import CapacityRelease, initialize_capacity_state, reserve_capacity
from .cold_bootstrap import bootstrap_active_recovery_contexts
from .durable import RecoveredInFlightLease, build_durable_snapshot, recover_after_restart
from .models import ArtifactRef, ExecutionSpec, ResultEnvelope, RunnerRegistry
from .persistence import SQLiteDurableHeadStore
from .physical import PhysicalOutcomeBundle, authorize_physical_attempt, observe_completed, observe_failure
from .planner import plan_execution
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import commit_reconciliation, plan_provider_outcome_reconciliation
from .recovery_context import SQLiteRecoveryContextStore, build_recovery_context, verify_recovery_context
from .reference_bridge import (
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from .reference_registry import SQLiteReferenceJobRegistry
from .session import bind_session, start_session

CutPoint = Literal[
    "context_persisted",
    "capacity_committed",
    "provider_registered",
    "terminal_persisted",
    "reconciliation_committed",
]
CutPointState = Literal[
    "orphan_context",
    "active_provider_unknown",
    "active_provider_running",
    "terminal_pending_reconciliation",
    "settled_terminal_reconciliation",
    "settled_revocation",
]
ProviderState = Literal["absent", "not_found", "running", "terminal"]
TerminalKind = Literal["timed_out", "completed"]

VALID_CUT_POINTS = (
    "context_persisted",
    "capacity_committed",
    "provider_registered",
    "terminal_persisted",
    "reconciliation_committed",
)


class CutPointMatrixError(ValueError):
    pass


class CutPointMatrixIntegrityError(CutPointMatrixError):
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
        raise CutPointMatrixError("cut-point stores must use distinct filesystem paths")


def _reference_spec(suffix: str) -> ExecutionSpec:
    digest = "sha256:" + "9" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cutpoint-matrix",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cross-store cut-point matrix {suffix}",
        source_revision=f"source-cutpoint-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://cutpoint/{suffix}", digest),),
    )


@dataclass(frozen=True, slots=True)
class CutPointPreparationReceipt:
    cutpoint: CutPoint
    context_id: str
    context_digest: str
    authorization_id: str
    anchor_head_digest: str
    provider_key: str
    provider_job_id: str | None = None
    terminal_observation_digest: str | None = None
    final_head_digest: str | None = None
    schema_version: str = "ge.cutpoint-preparation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cutpoint-preparation-receipt.v1":
            raise ValueError("unsupported cut-point preparation receipt schema")
        if self.cutpoint not in VALID_CUT_POINTS:
            raise ValueError("unsupported cut point")
        for name in ("context_id", "authorization_id", "provider_key"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("context_digest", "anchor_head_digest"):
            _require_sha256(name, getattr(self, name))
        if self.terminal_observation_digest is not None:
            _require_sha256("terminal_observation_digest", self.terminal_observation_digest)
        if self.final_head_digest is not None:
            _require_sha256("final_head_digest", self.final_head_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CutPointAssessment:
    state: CutPointState
    context_id: str
    context_digest: str
    authorization_id: str
    provider_key: str
    provider_state: ProviderState
    current_head_digest: str | None
    recovered_lease_id: str
    outcome_digest: str | None = None
    release_digest: str | None = None
    schema_version: str = "ge.cutpoint-assessment.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cutpoint-assessment.v1":
            raise ValueError("unsupported cut-point assessment schema")
        if self.state not in {
            "orphan_context",
            "active_provider_unknown",
            "active_provider_running",
            "terminal_pending_reconciliation",
            "settled_terminal_reconciliation",
            "settled_revocation",
        }:
            raise ValueError("unsupported cut-point state")
        if self.provider_state not in {"absent", "not_found", "running", "terminal"}:
            raise ValueError("unsupported provider state")
        for name in ("context_id", "authorization_id", "provider_key", "recovered_lease_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        _require_sha256("context_digest", self.context_digest)
        if self.current_head_digest is not None:
            _require_sha256("current_head_digest", self.current_head_digest)
        if self.outcome_digest is not None:
            _require_sha256("outcome_digest", self.outcome_digest)
        if self.release_digest is not None:
            _require_sha256("release_digest", self.release_digest)
        if self.state in {"terminal_pending_reconciliation", "settled_terminal_reconciliation"}:
            if self.provider_state != "terminal" or self.outcome_digest is None:
                raise ValueError("terminal cut-point state requires terminal provider outcome")
        if self.state == "settled_terminal_reconciliation" and self.release_digest is None:
            raise ValueError("settled terminal reconciliation requires release digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _anchor_recovered(context, runner) -> RecoveredInFlightLease:
    _, report = recover_after_restart(context.anchor_snapshot, runner)
    matches = [
        lease
        for lease in report.active_leases
        if lease.lease_id == context.recovered_lease_id
        and lease.lease_digest == context.recovered_lease_digest
    ]
    if len(matches) != 1:
        raise CutPointMatrixIntegrityError("context anchor does not reproduce its recovered lease")
    return matches[0]


def _matching_release(current, context) -> CapacityRelease | None:
    matches = [
        release
        for release in current.state.releases
        if release.lease_id == context.recovered_lease_id
        and release.lease_digest == context.recovered_lease_digest
        and release.authorization_id == context.authorization.authorization_id
    ]
    if len(matches) > 1:
        raise CutPointMatrixIntegrityError("recovered lease has multiple canonical releases")
    return matches[0] if matches else None


def _history_extends_anchor(current, context) -> bool:
    anchor = context.anchor_snapshot
    transitions = current.state.transitions
    prefix = anchor.state.transitions
    return len(transitions) >= len(prefix) and transitions[: len(prefix)] == prefix


def assess_reference_cutpoint(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
) -> CutPointAssessment:
    _require_distinct_paths(capacity_store_path, provider_registry_path, recovery_context_store_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)

    candidates = context_store.bootstrap_candidates()
    if len(candidates) != 1:
        raise CutPointMatrixError("reference cut-point assessment requires exactly one durable context")
    context, runner = candidates[0]
    key = reattachment_key_from_authorization(context.authorization, runner)
    record = provider_store.lookup(key)
    provider_state: ProviderState = "absent" if record is None else record.state  # type: ignore[assignment]
    current = capacity_store.load_current(runner)
    anchor_recovered = _anchor_recovered(context, runner)

    if current is None:
        if record is not None:
            raise CutPointMatrixIntegrityError("provider identity exists without canonical capacity head")
        return CutPointAssessment(
            state="orphan_context",
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=context.authorization.authorization_id,
            provider_key=key.provider_key,
            provider_state="absent",
            current_head_digest=None,
            recovered_lease_id=anchor_recovered.lease_id,
        )

    if not _history_extends_anchor(current, context):
        raise CutPointMatrixIntegrityError("current capacity history does not extend context anchor")

    _, recovery = recover_after_restart(current, runner)
    active = [
        lease
        for lease in recovery.active_leases
        if lease.lease_id == context.recovered_lease_id
        and lease.lease_digest == context.recovered_lease_digest
    ]
    if len(active) > 1:
        raise CutPointMatrixIntegrityError("recovered lease appears multiple times in active state")

    if active:
        if not verify_recovery_context(current, context):
            raise CutPointMatrixIntegrityError("active recovery context failed current-head verification")
        probe = build_status_probe(current, runner, active[0])
        observation = query_reference_status(provider_store, probe)
        assessment, outcome = assess_provider_status(
            current,
            context.spec,
            context.registry,
            context.plan,
            context.session,
            runner,
            context.authorization,
            probe,
            observation,
        )
        if observation.status == "not_found":
            if assessment.disposition != "remain_unknown" or outcome is not None:
                raise CutPointMatrixIntegrityError("not_found provider state was not conservative")
            return CutPointAssessment(
                state="active_provider_unknown",
                context_id=context.context_id,
                context_digest=context.digest,
                authorization_id=context.authorization.authorization_id,
                provider_key=key.provider_key,
                provider_state="not_found",
                current_head_digest=current.head.digest,
                recovered_lease_id=active[0].lease_id,
            )
        if observation.status == "running":
            if assessment.disposition != "keep_running" or outcome is not None:
                raise CutPointMatrixIntegrityError("running provider state did not preserve occupancy")
            return CutPointAssessment(
                state="active_provider_running",
                context_id=context.context_id,
                context_digest=context.digest,
                authorization_id=context.authorization.authorization_id,
                provider_key=key.provider_key,
                provider_state="running",
                current_head_digest=current.head.digest,
                recovered_lease_id=active[0].lease_id,
            )
        if assessment.disposition != "terminal_outcome" or outcome is None:
            raise CutPointMatrixIntegrityError("terminal provider state did not reproduce physical outcome")
        return CutPointAssessment(
            state="terminal_pending_reconciliation",
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=context.authorization.authorization_id,
            provider_key=key.provider_key,
            provider_state="terminal",
            current_head_digest=current.head.digest,
            recovered_lease_id=active[0].lease_id,
            outcome_digest=outcome.digest,
        )

    release = _matching_release(current, context)
    if release is None:
        raise CutPointMatrixIntegrityError("context lease is neither active nor canonically released")

    anchor_probe = build_status_probe(context.anchor_snapshot, runner, anchor_recovered)
    observation = query_reference_status(provider_store, anchor_probe)
    if release.release_kind == "session_revoked":
        return CutPointAssessment(
            state="settled_revocation",
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=context.authorization.authorization_id,
            provider_key=key.provider_key,
            provider_state=observation.status,
            current_head_digest=current.head.digest,
            recovered_lease_id=anchor_recovered.lease_id,
            release_digest=release.digest,
        )

    if observation.status != "terminal":
        raise CutPointMatrixIntegrityError("terminal-outcome release lacks terminal provider evidence")
    _, outcome = assess_provider_status(
        context.anchor_snapshot,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        anchor_probe,
        observation,
    )
    if outcome is None or outcome.digest != release.outcome_digest:
        raise CutPointMatrixIntegrityError("canonical release does not match provider terminal outcome")
    if outcome.receipt.digest != release.receipt_digest:
        raise CutPointMatrixIntegrityError("canonical release receipt does not match provider terminal outcome")
    return CutPointAssessment(
        state="settled_terminal_reconciliation",
        context_id=context.context_id,
        context_digest=context.digest,
        authorization_id=context.authorization.authorization_id,
        provider_key=key.provider_key,
        provider_state="terminal",
        current_head_digest=current.head.digest,
        recovered_lease_id=anchor_recovered.lease_id,
        outcome_digest=outcome.digest,
        release_digest=release.digest,
    )


def _terminal_observation(context, runner, provider_job_id: str, terminal_kind: TerminalKind):
    if terminal_kind == "timed_out":
        return observe_failure(
            context.authorization,
            "timed_out",
            failure_code="reference.cutpoint.timeout",
            provider_invocation_id=provider_job_id,
        )
    result = ResultEnvelope(
        session_id=context.session.session_id,
        spec_id=context.spec.spec_id,
        spec_digest=context.spec.digest,
        runner_id=runner.runner_id,
        attempt=context.session.attempt,
        status="completed",
        evidence=(),
        summary="Reference cut-point provider completion.",
    )
    return observe_completed(
        context.authorization,
        result,
        provider_invocation_id=provider_job_id,
    )


def _reconcile_terminal_from_stores(
    capacity_store: SQLiteDurableHeadStore,
    provider_store: SQLiteReferenceJobRegistry,
    context_store: SQLiteRecoveryContextStore,
) -> str:
    bindings = bootstrap_active_recovery_contexts(context_store, capacity_store)
    if len(bindings) != 1:
        raise CutPointMatrixError("terminal reconciliation requires one active cold binding")
    binding = bindings[0]
    context = binding.context
    runner = binding.runner
    source = binding.current_snapshot
    recovered = binding.recovered_lease
    probe = build_status_probe(source, runner, recovered)
    observation = query_reference_status(provider_store, probe)
    if observation.status != "terminal":
        raise CutPointMatrixError("terminal reconciliation requires persisted terminal provider state")
    assessment, outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        observation,
    )
    if assessment.disposition != "terminal_outcome" or outcome is None:
        raise CutPointMatrixIntegrityError("terminal state failed physical-outcome admission")
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
    committed, _, _ = commit_reconciliation(capacity_store, runner, plan)
    return committed.head.digest


def prepare_reference_cutpoint(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
    *,
    cutpoint: CutPoint,
    terminal_kind: TerminalKind = "timed_out",
    suffix: str = "1",
) -> CutPointPreparationReceipt:
    if cutpoint not in VALID_CUT_POINTS:
        raise CutPointMatrixError("unsupported cut point")
    if terminal_kind not in {"timed_out", "completed"}:
        raise CutPointMatrixError("terminal_kind must be timed_out or completed")
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
        invocation_id=f"gei-cutpoint-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, session, runner, authorization)
    anchor = build_durable_snapshot(state, runner)
    _, recovery = recover_after_restart(anchor, runner)
    if len(recovery.active_leases) != 1:
        raise CutPointMatrixError("cut-point fixture requires exactly one active lease")
    recovered = recovery.active_leases[0]
    context = build_recovery_context(
        anchor, spec, registry, plan, session, runner, authorization, recovered
    )
    key = reattachment_key_from_authorization(authorization, runner)

    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)
    if context_store.list_contexts():
        raise CutPointMatrixError("context store must be empty for a new cut-point fixture")
    if capacity_store.load_current(runner) is not None:
        raise CutPointMatrixError("capacity store must be empty for a new cut-point fixture")
    if provider_store.lookup(key) is not None:
        raise CutPointMatrixError("provider store must be empty for a new cut-point fixture")

    context_store.save(context, anchor)
    if cutpoint == "context_persisted":
        return CutPointPreparationReceipt(
            cutpoint=cutpoint,
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=authorization.authorization_id,
            anchor_head_digest=anchor.head.digest,
            provider_key=key.provider_key,
        )

    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=None)
    if cutpoint == "capacity_committed":
        return CutPointPreparationReceipt(
            cutpoint=cutpoint,
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=authorization.authorization_id,
            anchor_head_digest=anchor.head.digest,
            provider_key=key.provider_key,
            final_head_digest=anchor.head.digest,
        )

    registered_key, registration = register_reference_invocation(provider_store, authorization, runner)
    if registered_key != key or registration.idempotent:
        raise CutPointMatrixError("provider registration did not create expected fresh identity")
    if cutpoint == "provider_registered":
        return CutPointPreparationReceipt(
            cutpoint=cutpoint,
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=authorization.authorization_id,
            anchor_head_digest=anchor.head.digest,
            provider_key=key.provider_key,
            provider_job_id=registration.job_id,
            final_head_digest=anchor.head.digest,
        )

    physical = _terminal_observation(context, runner, registration.job_id, terminal_kind)
    record_reference_terminal(provider_store, key, physical)
    if cutpoint == "terminal_persisted":
        return CutPointPreparationReceipt(
            cutpoint=cutpoint,
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=authorization.authorization_id,
            anchor_head_digest=anchor.head.digest,
            provider_key=key.provider_key,
            provider_job_id=registration.job_id,
            terminal_observation_digest=physical.digest,
            final_head_digest=anchor.head.digest,
        )

    committed_head = _reconcile_terminal_from_stores(capacity_store, provider_store, context_store)
    return CutPointPreparationReceipt(
        cutpoint=cutpoint,
        context_id=context.context_id,
        context_digest=context.digest,
        authorization_id=authorization.authorization_id,
        anchor_head_digest=anchor.head.digest,
        provider_key=key.provider_key,
        provider_job_id=registration.job_id,
        terminal_observation_digest=physical.digest,
        final_head_digest=committed_head,
    )
