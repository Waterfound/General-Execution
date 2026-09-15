import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    ResultEnvelope,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    admit_physical_observation,
    authorize_physical_attempt,
    authorize_retry,
    bind_session,
    initialize_capacity_state,
    observe_completed,
    observe_failure,
    plan_execution,
    prepare_dispatch_intent,
    reference_runner,
    release_capacity_for_outcome,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.dispatch import DispatchIntentError
from general_execution.observed import (
    SqliteDurableObservedOutcomeStore,
    release_observed_capacity_after_restart,
)
from general_execution.recovery_driver import RecoveryDriverError, apply_recovery_step
from general_execution.session_recovery import project_session_after_restart

D = "sha256:" + "b" * 64


def context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-recovery-driver",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Bounded recovery driver {suffix}",
        source_revision=f"source-recovery-driver-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://recovery-driver/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    bound = bind_session(spec, registry, plan)
    running = start_session(bound)
    auth = authorize_physical_attempt(
        spec,
        registry,
        plan,
        running,
        runner,
        invocation_id=f"gei-recovery-driver-{suffix}-1",
    )
    return runner, spec, registry, plan, bound, running, auth


def stores(tmp_path, ctx, *, reserve=False, dispatch=False, begin=False):
    runner, spec, registry, plan, _, running, auth = ctx
    genesis = initialize_capacity_state(runner)
    capacity_store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    capacity_store.initialize(runner, genesis)
    dispatch_store = SqliteDurableObservedOutcomeStore(tmp_path / "dispatch.db")
    if not reserve:
        return capacity_store, dispatch_store, genesis, None, None
    state, grant, _ = reserve_capacity(genesis, spec, registry, plan, running, runner, auth)
    capacity_store.commit(runner, genesis.digest, state)
    dispatch_state = None
    if dispatch:
        intent = prepare_dispatch_intent(state, runner, grant.lease, auth)
        dispatch_state = dispatch_store.initialize(intent)
    if begin:
        dispatch_state, _ = dispatch_store.begin_submission(
            dispatch_state.intent.intent_id,
            dispatch_state.digest,
            capacity_store,
            runner,
        )
    return capacity_store, dispatch_store, state, grant, dispatch_state


def failure_outcome(ctx, auth=None):
    runner, spec, registry, plan, _, running, default_auth = ctx
    auth = auth or default_auth
    observation = observe_failure(
        auth,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id=f"provider-{auth.request.invocation_id}",
    )
    return admit_physical_observation(spec, registry, plan, running, runner, auth, observation)


def completed_outcome(ctx):
    runner, spec, registry, plan, _, running, auth = ctx
    result = ResultEnvelope(
        session_id=running.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=running.attempt,
        status="completed",
        evidence=(ArtifactRef(REFERENCE_EVIDENCE, "ge+reference://recovery-driver/completed", D),),
        summary="Completed result recovered by bounded recovery driver.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-driver-completed")
    return admit_physical_observation(spec, registry, plan, running, runner, auth, observation)


def projection(ctx, capacity_store, dispatch_store):
    runner, spec, registry, plan, *_ = ctx
    return project_session_after_restart(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
    )


def apply(ctx, capacity_store, dispatch_store, projected):
    runner, spec, registry, plan, *_ = ctx
    return apply_recovery_step(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
        projected,
    )


def test_start_session_step_is_bounded_and_grants_no_transport(tmp_path):
    ctx = context("start")
    capacity_store, dispatch_store, _, _, _ = stores(tmp_path, ctx)
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    assert result.status == "applied"
    assert result.action == "start_session"
    assert result.resulting_session.state == "running"
    assert result.transport_authority is False
    assert result.automatic_retry_authorized is False
    assert result.next_projection_digest is None


def test_prepare_dispatch_intent_step_moves_to_begin_submission(tmp_path):
    ctx = context("prepare")
    capacity_store, dispatch_store, _, grant, _ = stores(tmp_path, ctx, reserve=True)
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    states = dispatch_store.load_for_runner(ctx[0].runner_id)
    assert len(states) == 1
    assert states[0].status == "prepared"
    assert states[0].intent.lease_id == grant.lease.lease_id
    next_projected = projection(ctx, capacity_store, dispatch_store)
    assert next_projected.recovery_action == "begin_submission"
    assert result.next_projection_digest == next_projected.digest
    assert result.resulting_session == next_projected.projected_session
    assert result.transport_authority is False


def test_retry_dispatch_reconstruction_uses_exact_durable_predecessor(tmp_path):
    ctx = context("retry")
    runner, spec, registry, plan, _, running, _ = ctx
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    first = failure_outcome(ctx)
    dispatch_store.record_observed(
        unknown.intent.intent_id,
        unknown.digest,
        spec,
        registry,
        plan,
        running,
        runner,
        first,
    )
    release_observed_capacity_after_restart(
        dispatch_store,
        capacity_store,
        unknown.intent.intent_id,
        spec,
        registry,
        plan,
        running,
        runner,
    )
    released, _ = capacity_store.load(runner)
    retry = authorize_retry(
        spec,
        registry,
        plan,
        running,
        runner,
        first,
        invocation_id="gei-recovery-driver-retry-2",
    )
    retried, grant, _ = reserve_capacity(released, spec, registry, plan, running, runner, retry)
    capacity_store.commit(runner, released.digest, retried)

    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    states = dispatch_store.load_for_runner(runner.runner_id)
    retry_states = [state for state in states if state.intent.lease_id == grant.lease.lease_id]
    assert len(retry_states) == 1
    assert retry_states[0].intent.authorization_id == retry.authorization_id
    assert retry_states[0].intent.authorization_digest == retry.digest
    assert retry_states[0].intent.physical_attempt == 2
    assert retry_states[0].intent.invocation_id == retry.request.invocation_id
    assert result.automatic_retry_authorized is False


def test_begin_submission_step_produces_non_transport_dispatch_permit(tmp_path):
    ctx = context("begin")
    capacity_store, dispatch_store, _, _, prepared = stores(
        tmp_path, ctx, reserve=True, dispatch=True
    )
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    current = dispatch_store.load(prepared.intent.intent_id)
    next_projected = projection(ctx, capacity_store, dispatch_store)
    assert current.status == "submission_unknown"
    assert next_projected.recovery_action == "reconcile_provider"
    assert result.dispatch_permit_digest is not None
    assert result.transport_authority is False
    assert result.automatic_retry_authorized is False
    assert result.next_projection_digest == next_projected.digest


def test_reconcile_provider_requires_external_input_and_does_not_mutate(tmp_path):
    ctx = context("reconcile")
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    projected = projection(ctx, capacity_store, dispatch_store)
    before = dispatch_store.load(unknown.intent.intent_id)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    after = dispatch_store.load(unknown.intent.intent_id)
    assert result.status == "external_input_required"
    assert result.action == "reconcile_provider"
    assert before == after
    assert result.transport_authority is False
    assert result.automatic_retry_authorized is False


def test_failed_observed_outcome_release_finishes_without_auto_retry(tmp_path):
    ctx = context("failure-release")
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    outcome = failure_outcome(ctx)
    dispatch_store.record_observed(
        unknown.intent.intent_id,
        unknown.digest,
        *ctx[1:4],
        ctx[5],
        ctx[0],
        outcome,
    )
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    next_projected = projection(ctx, capacity_store, dispatch_store)
    assert result.status == "applied"
    assert result.capacity_recovery_digest is not None
    assert next_projected.status == "coherent"
    assert next_projected.projected_state == "running"
    assert next_projected.retry_eligible is True
    assert result.resulting_session == next_projected.projected_session
    assert result.automatic_retry_authorized is False


def test_completed_observed_outcome_release_projects_result_submitted(tmp_path):
    ctx = context("completed-release")
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    outcome = completed_outcome(ctx)
    dispatch_store.record_observed(
        unknown.intent.intent_id,
        unknown.digest,
        *ctx[1:4],
        ctx[5],
        ctx[0],
        outcome,
    )
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    next_projected = projection(ctx, capacity_store, dispatch_store)
    assert next_projected.projected_state == "result_submitted"
    assert next_projected.projected_session.result_digest == outcome.result.digest
    assert result.resulting_session == next_projected.projected_session
    assert result.automatic_retry_authorized is False


def test_retry_eligible_coherent_projection_never_authorizes_retry(tmp_path):
    ctx = context("retry-eligible")
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    outcome = failure_outcome(ctx)
    dispatch_store.record_observed(
        unknown.intent.intent_id,
        unknown.digest,
        *ctx[1:4],
        ctx[5],
        ctx[0],
        outcome,
    )
    release_observed_capacity_after_restart(
        dispatch_store,
        capacity_store,
        unknown.intent.intent_id,
        *ctx[1:4],
        ctx[5],
        ctx[0],
    )
    projected = projection(ctx, capacity_store, dispatch_store)
    assert projected.retry_eligible is True
    result = apply(ctx, capacity_store, dispatch_store, projected)
    assert result.status == "no_action"
    assert result.action == "none"
    assert result.automatic_retry_authorized is False
    assert result.transport_authority is False


def test_revoked_coherent_projection_is_no_action(tmp_path):
    ctx = context("revoked")
    runner, _, _, _, _, running, _ = ctx
    capacity_store, dispatch_store, state, grant, _ = stores(tmp_path, ctx, reserve=True)
    revoked = revoke_session(running)
    released, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    capacity_store.commit(runner, state.digest, released)
    projected = projection(ctx, capacity_store, dispatch_store)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    assert projected.projected_state == "revoked"
    assert result.status == "no_action"
    assert result.resulting_session == revoked


def test_legacy_projection_is_refused(tmp_path):
    ctx = context("legacy")
    runner, spec, registry, plan, _, running, _ = ctx
    capacity_store, dispatch_store, state, grant, _ = stores(tmp_path, ctx, reserve=True)
    outcome = failure_outcome(ctx)
    released, _, _ = release_capacity_for_outcome(
        state,
        spec,
        registry,
        plan,
        running,
        runner,
        grant.lease,
        outcome,
    )
    capacity_store.commit(runner, state.digest, released)
    projected = projection(ctx, capacity_store, dispatch_store)
    assert projected.status == "legacy_untracked"
    with pytest.raises(RecoveryDriverError, match="refuses non-recoverable"):
        apply(ctx, capacity_store, dispatch_store, projected)


def test_old_projection_is_rejected_after_another_coordinator_advances_dispatch(tmp_path):
    ctx = context("stale")
    runner, _, _, _, _, _, auth = ctx
    capacity_store, dispatch_store, state, grant, _ = stores(tmp_path, ctx, reserve=True)
    projected = projection(ctx, capacity_store, dispatch_store)
    intent = prepare_dispatch_intent(state, runner, grant.lease, auth)
    dispatch_store.initialize(intent)
    with pytest.raises(RecoveryDriverError, match="projection is stale"):
        apply(ctx, capacity_store, dispatch_store, projected)


def test_revocation_race_wins_over_prepared_recovery_without_transport_authority(tmp_path, monkeypatch):
    ctx = context("revoke-race")
    runner, _, _, _, _, running, _ = ctx
    capacity_store, dispatch_store, _, grant, _ = stores(tmp_path, ctx, reserve=True)
    projected = projection(ctx, capacity_store, dispatch_store)
    original_initialize = dispatch_store.initialize
    raced = {"done": False}

    def initialize_after_revocation(intent):
        if not raced["done"]:
            current, _ = capacity_store.load(runner)
            revoked = revoke_session(running)
            released, _, _ = release_capacity_for_revocation(current, runner, grant.lease, revoked)
            capacity_store.commit(runner, current.digest, released)
            raced["done"] = True
        return original_initialize(intent)

    monkeypatch.setattr(dispatch_store, "initialize", initialize_after_revocation)
    result = apply(ctx, capacity_store, dispatch_store, projected)
    next_projected = projection(ctx, capacity_store, dispatch_store)
    assert next_projected.status == "coherent"
    assert next_projected.projected_state == "revoked"
    assert result.resulting_session == next_projected.projected_session
    assert result.transport_authority is False
    assert result.automatic_retry_authorized is False

    prepared = dispatch_store.load_for_runner(runner.runner_id)[0]
    assert prepared.status == "prepared"
    with pytest.raises(DispatchIntentError):
        dispatch_store.begin_submission(
            prepared.intent.intent_id,
            prepared.digest,
            capacity_store,
            runner,
        )
