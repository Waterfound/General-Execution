from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .adapter import REFERENCE_CAPABILITY, REFERENCE_EVIDENCE, REFERENCE_TASK_KIND, reference_runner
from .canonical import sha256_digest
from .capacity import RunnerCapacityState, initialize_capacity_state, reserve_capacity
from .cold_guard import bootstrap_cold_coordinator_strict
from .coordinator_context import (
    ColdCoordinatorBinding,
    SqliteCoordinatorContextStore,
    build_coordinator_context,
)
from .dispatch import (
    DispatchIntentError,
    DispatchPermit,
    DispatchRecoveryReport,
    SqliteDispatchIntentStore,
    recover_dispatch_after_restart,
    verify_dispatch_permit,
)
from .durable import DurableCapacityHead, SqliteCapacityHeadStore, recover_capacity_after_restart
from .models import ArtifactRef, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import authorize_physical_attempt
from .planner import plan_execution
from .session import bind_session, start_session


class CanonicalColdError(ValueError):
    pass


def _distinct_paths(*paths: str | Path) -> bool:
    resolved = [Path(path).resolve() for path in paths]
    return len(resolved) == len(set(resolved))


def _capacity_head_exists(store: SqliteCapacityHeadStore, runner_id: str) -> bool:
    try:
        with sqlite3.connect(str(store.path)) as connection:
            return connection.execute(
                "SELECT 1 FROM capacity_heads WHERE runner_id = ?",
                (runner_id,),
            ).fetchone() is not None
    except sqlite3.DatabaseError as exc:
        raise CanonicalColdError("durable capacity store is unreadable") from exc


def _dispatch_intent_exists(store: SqliteDispatchIntentStore, intent_id: str) -> bool:
    try:
        with sqlite3.connect(str(store.path)) as connection:
            return connection.execute(
                "SELECT 1 FROM dispatch_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone() is not None
    except sqlite3.DatabaseError as exc:
        raise CanonicalColdError("durable dispatch store is unreadable") from exc


@dataclass(frozen=True, slots=True)
class CanonicalColdPreparationReceipt:
    context_id: str
    context_digest: str
    intent_id: str
    prepared_state_digest: str
    capacity_head_digest: str
    submission_unknown_state_digest: str
    dispatch_permit_digest: str
    invocation_id: str
    schema_version: str = "ge.canonical-cold-preparation-receipt.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CanonicalColdRecoveryReport:
    context_id: str
    context_digest: str
    runner_id: str
    invocation_id: str
    capacity_recovery_digest: str
    dispatch_recovery_digest: str
    capacity_state_digest: str
    dispatch_state_digest: str
    recovery_action: str
    blind_resubmissions_authorized: int
    provider_outcomes_inferred: int
    context_mode: str = "cold_reconstructed"
    schema_version: str = "ge.canonical-cold-recovery-report.v1"

    def __post_init__(self) -> None:
        if self.context_mode != "cold_reconstructed":
            raise ValueError("canonical cold recovery must reconstruct context")
        if self.recovery_action != "reconcile_provider":
            raise ValueError("submission_unknown must recover as reconcile_provider")
        if self.blind_resubmissions_authorized != 0:
            raise ValueError("cold recovery cannot authorize blind resubmission")
        if self.provider_outcomes_inferred != 0:
            raise ValueError("cold recovery cannot infer provider outcomes")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _spec(suffix: str) -> ExecutionSpec:
    digest = "sha256:" + "d" * 64
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-canonical-cold-bootstrap",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Canonical cold ambiguity recovery {suffix}",
        source_revision=f"source-canonical-cold-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://canonical-cold/{suffix}", digest),),
    )


def _reconstruct_submission_unknown_permit(dispatch_state) -> DispatchPermit:
    if dispatch_state.status != "submission_unknown":
        raise CanonicalColdError("dispatch state is not submission_unknown")
    intent = dispatch_state.intent
    permit = DispatchPermit(
        intent_id=intent.intent_id,
        intent_digest=intent.digest,
        state_digest=dispatch_state.digest,
        invocation_id=intent.invocation_id,
        request_digest=intent.request_digest,
        authorization_id=intent.authorization_id,
        authorization_digest=intent.authorization_digest,
    )
    if not verify_dispatch_permit(dispatch_state, permit):
        raise CanonicalColdError("reconstructed dispatch permit failed verification")
    return permit


def _existing_context_matches(context_store: SqliteCoordinatorContextStore, context) -> bool:
    matches = [
        item
        for item in context_store.candidates()
        if item.authorization.authorization_id == context.authorization.authorization_id
    ]
    if not matches:
        return False
    if len(matches) != 1 or matches[0] != context:
        raise CanonicalColdError("durable coordinator context does not match deterministic preparation")
    return True


def _preparation_candidate(suffix: str):
    runner = reference_runner()
    spec = _spec(suffix)
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-canonical-cold-{suffix}",
    )
    genesis = initialize_capacity_state(runner)
    reserved_state, grant, _ = reserve_capacity(
        genesis,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    context = build_coordinator_context(
        reserved_state,
        spec,
        registry,
        plan,
        session,
        runner,
        grant.lease,
        authorization,
    )
    return runner, genesis, reserved_state, context, authorization


def prepare_canonical_cold_ambiguity(
    capacity_path: str | Path,
    context_path: str | Path,
    dispatch_path: str | Path,
    *,
    suffix: str = "1",
) -> CanonicalColdPreparationReceipt:
    """Persist one deterministic ambiguous invocation with lost-ack replay safety."""
    if not _distinct_paths(capacity_path, context_path, dispatch_path):
        raise CanonicalColdError("capacity, context, and dispatch stores must use distinct files")

    runner, genesis, reserved_state, context, authorization = _preparation_candidate(suffix)
    capacity_store = SqliteCapacityHeadStore(capacity_path)
    context_store = SqliteCoordinatorContextStore(context_path)
    dispatch_store = SqliteDispatchIntentStore(dispatch_path)

    head_exists = _capacity_head_exists(capacity_store, runner.runner_id)
    if head_exists:
        current_state, current_head = capacity_store.load(runner)
    else:
        current_state, current_head = None, None

    replaying_active_reservation = current_state == reserved_state
    if current_state is not None and current_state not in (genesis, reserved_state):
        raise CanonicalColdError(
            "canonical preparation cannot replay after capacity advanced beyond its reservation"
        )

    context_exists = _existing_context_matches(context_store, context)
    dispatch_exists = _dispatch_intent_exists(dispatch_store, context.dispatch_intent.intent_id)

    if replaying_active_reservation:
        if not context_exists:
            raise CanonicalColdError("active canonical reservation is missing its prior durable context")
        if not dispatch_exists:
            raise CanonicalColdError("active canonical reservation is missing its prior dispatch intent")
    else:
        # Safe pre-reservation recovery: context and PREPARED may be created or replayed.
        context_store.save(context)

    if dispatch_exists:
        dispatch_state = dispatch_store.load(context.dispatch_intent.intent_id)
        if dispatch_state.intent != context.dispatch_intent:
            raise CanonicalColdError("durable dispatch intent differs from deterministic preparation")
    else:
        if replaying_active_reservation:
            raise CanonicalColdError("active reservation cannot create dispatch identity retroactively")
        dispatch_state = dispatch_store.initialize(context.dispatch_intent)

    if current_state is None:
        capacity_store.initialize(runner, genesis)
        current_state, current_head = capacity_store.load(runner)

    if current_state == genesis:
        if dispatch_state.status != "prepared":
            raise CanonicalColdError("pre-reservation state cannot already claim submission ambiguity")
        capacity_head = capacity_store.commit(runner, genesis.digest, reserved_state)
        current_state = reserved_state
    elif current_state == reserved_state:
        assert current_head is not None
        capacity_head = current_head
    else:  # guarded above; keeps the control flow fail closed if changed later.
        raise CanonicalColdError("unexpected canonical capacity state during preparation")

    if dispatch_state.status == "prepared":
        prepared_state_digest = dispatch_state.digest
        submission_unknown, permit = dispatch_store.begin_submission(
            context.dispatch_intent.intent_id,
            dispatch_state.digest,
            capacity_store,
            runner,
        )
    elif dispatch_state.status == "submission_unknown":
        if dispatch_state.previous_state_digest is None:
            raise CanonicalColdError("submission_unknown state is missing PREPARED predecessor")
        prepared_state_digest = dispatch_state.previous_state_digest
        submission_unknown = dispatch_state
        permit = _reconstruct_submission_unknown_permit(dispatch_state)
    else:
        raise CanonicalColdError("canonical preparation cannot replay after provider observation")

    return CanonicalColdPreparationReceipt(
        context_id=context.context_id,
        context_digest=context.digest,
        intent_id=context.dispatch_intent.intent_id,
        prepared_state_digest=prepared_state_digest,
        capacity_head_digest=capacity_head.digest,
        submission_unknown_state_digest=submission_unknown.digest,
        dispatch_permit_digest=permit.digest,
        invocation_id=authorization.request.invocation_id,
    )


def _single_binding(
    capacity_path: str | Path,
    context_path: str | Path,
    dispatch_path: str | Path,
) -> ColdCoordinatorBinding:
    bindings = bootstrap_cold_coordinator_strict(
        SqliteCoordinatorContextStore(context_path),
        SqliteCapacityHeadStore(capacity_path),
        SqliteDispatchIntentStore(dispatch_path),
    )
    if len(bindings) != 1:
        raise CanonicalColdError("cold recovery requires exactly one active coordinator binding")
    return bindings[0]


def recover_canonical_cold_ambiguity(
    capacity_path: str | Path,
    context_path: str | Path,
    dispatch_path: str | Path,
) -> CanonicalColdRecoveryReport:
    if not _distinct_paths(capacity_path, context_path, dispatch_path):
        raise CanonicalColdError("capacity, context, and dispatch stores must use distinct files")

    binding = _single_binding(capacity_path, context_path, dispatch_path)
    runner: RunnerCapabilities = binding.runner
    capacity_store = SqliteCapacityHeadStore(capacity_path)
    dispatch_store = SqliteDispatchIntentStore(dispatch_path)

    _, capacity_report = recover_capacity_after_restart(capacity_store, runner)
    dispatch_report: DispatchRecoveryReport = recover_dispatch_after_restart(
        dispatch_store,
        runner.runner_id,
    )
    items = [
        item
        for item in dispatch_report.items
        if item.intent_id == binding.context.dispatch_intent.intent_id
    ]
    if len(items) != 1:
        raise CanonicalColdError("dispatch recovery does not contain the reconstructed intent")
    item = items[0]
    if item.state_digest != binding.dispatch_state.digest:
        raise CanonicalColdError("dispatch recovery state changed during cold bootstrap")

    return CanonicalColdRecoveryReport(
        context_id=binding.context.context_id,
        context_digest=binding.context.digest,
        runner_id=runner.runner_id,
        invocation_id=binding.context.authorization.request.invocation_id,
        capacity_recovery_digest=capacity_report.digest,
        dispatch_recovery_digest=dispatch_report.digest,
        capacity_state_digest=binding.capacity_state.digest,
        dispatch_state_digest=binding.dispatch_state.digest,
        recovery_action=item.recovery_action,
        blind_resubmissions_authorized=dispatch_report.blind_resubmissions_authorized,
        provider_outcomes_inferred=dispatch_report.provider_outcomes_inferred,
    )
