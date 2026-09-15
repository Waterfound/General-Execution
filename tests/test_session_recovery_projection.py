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
from general_execution.observed import (
    SqliteDurableObservedOutcomeStore,
    release_observed_capacity_after_restart,
)
from general_execution.session_recovery import project_session_after_restart

D = "sha256:" + "a" * 64


def context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-session-recovery",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Session recovery {suffix}",
        source_revision=f"source-session-recovery-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://session-recovery/{suffix}", D),),
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
        invocation_id=f"gei-session-recovery-{suffix}-1",
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
    intent = prepare_dispatch_intent(state, runner, grant.lease, auth)
    dispatch_state = None
    if dispatch:
        dispatch_state = dispatch_store.initialize(intent)
    if begin:
        dispatch_state, _ = dispatch_store.begin_submission(
            intent.intent_id,
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
        evidence=(ArtifactRef(REFERENCE_EVIDENCE, "ge+reference://session-recovery/completed", D),),
        summary="Completed result recovered from durable physical outcome.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-completed")
    return admit_physical_observation(spec, registry, plan, running, runner, auth, observation)


def project(ctx, capacity_store, dispatch_store):
    runner, spec, registry, plan, *_ = ctx
    return project_session_after_restart(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
    )


def test_no_physical_history_projects_bound_with_safe_start(tmp_path):
    ctx = context("empty")
    capacity_store, dispatch_store, _, _, _ = stores(tmp_path, ctx)
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "recovery_required"
    assert recovery.projected_state == "bound"
    assert recovery.recovery_action == "start_session"


def test_active_lease_without_dispatch_requires_intent_preparation(tmp_path):
    ctx = context("lease-only")
    capacity_store, dispatch_store, state, grant, _ = stores(tmp_path, ctx, reserve=True)
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "recovery_required"
    assert recovery.projected_state == "running"
    assert recovery.active_lease_id == grant.lease.lease_id
    assert recovery.recovery_action == "prepare_dispatch_intent"
    assert recovery.capacity_state_digest == state.digest


def test_prepared_dispatch_projects_begin_submission(tmp_path):
    ctx = context("prepared")
    capacity_store, dispatch_store, _, _, prepared = stores(tmp_path, ctx, reserve=True, dispatch=True)
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.recovery_action == "begin_submission"
    assert recovery.dispatch_intent_id == prepared.intent.intent_id
    assert recovery.dispatch_status == "prepared"


def test_submission_unknown_projects_provider_reconciliation(tmp_path):
    ctx = context("unknown")
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.recovery_action == "reconcile_provider"
    assert recovery.dispatch_status == "submission_unknown"
    assert recovery.dispatch_intent_id == unknown.intent.intent_id


def test_observed_active_lease_projects_capacity_release(tmp_path):
    ctx = context("observed")
    capacity_store, dispatch_store, _, grant, unknown = stores(
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
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.projected_state == "running"
    assert recovery.recovery_action == "release_observed_capacity"
    assert recovery.active_lease_id == grant.lease.lease_id
    assert recovery.durable_outcome_digest == outcome.digest


def test_failed_terminal_release_projects_running_retry_eligible(tmp_path):
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
    release_observed_capacity_after_restart(
        dispatch_store,
        capacity_store,
        unknown.intent.intent_id,
        *ctx[1:4],
        ctx[5],
        ctx[0],
    )
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "coherent"
    assert recovery.projected_state == "running"
    assert recovery.retry_eligible is True
    assert recovery.durable_outcome_digest == outcome.digest
    assert recovery.recovery_action == "none"


def test_completed_terminal_release_reconstructs_result_submitted(tmp_path):
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
    release_observed_capacity_after_restart(
        dispatch_store,
        capacity_store,
        unknown.intent.intent_id,
        *ctx[1:4],
        ctx[5],
        ctx[0],
    )
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "coherent"
    assert recovery.projected_state == "result_submitted"
    assert recovery.projected_session.result_digest == outcome.result.digest
    assert recovery.retry_eligible is False


def test_revocation_release_reconstructs_revoked_session(tmp_path):
    ctx = context("revoked")
    runner, _, _, _, _, running, _ = ctx
    capacity_store, dispatch_store, state, grant, _ = stores(tmp_path, ctx, reserve=True)
    revoked = revoke_session(running)
    released, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    capacity_store.commit(runner, state.digest, released)
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "coherent"
    assert recovery.projected_state == "revoked"
    assert recovery.projected_session == revoked


def test_legacy_terminal_release_without_full_outcome_does_not_invent_result(tmp_path):
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
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "legacy_untracked"
    assert recovery.projected_state == "running"
    assert recovery.retry_eligible is False
    assert recovery.finding == "TERMINAL_RELEASE_LACKS_RESTART_COMPLETE_DURABLE_OUTCOME"


def test_retry_active_lease_projects_latest_physical_attempt(tmp_path):
    ctx = context("retry")
    runner, spec, registry, plan, _, running, _ = ctx
    capacity_store, dispatch_store, _, _, unknown = stores(
        tmp_path, ctx, reserve=True, dispatch=True, begin=True
    )
    first_outcome = failure_outcome(ctx)
    dispatch_store.record_observed(
        unknown.intent.intent_id,
        unknown.digest,
        spec,
        registry,
        plan,
        running,
        runner,
        first_outcome,
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
        first_outcome,
        invocation_id="gei-session-recovery-retry-2",
    )
    retried, grant, _ = reserve_capacity(
        released,
        spec,
        registry,
        plan,
        running,
        runner,
        retry,
    )
    capacity_store.commit(runner, released.digest, retried)
    recovery = project(ctx, capacity_store, dispatch_store)
    assert recovery.status == "recovery_required"
    assert recovery.recovery_action == "prepare_dispatch_intent"
    assert recovery.latest_physical_attempt == 2
    assert recovery.active_lease_id == grant.lease.lease_id
