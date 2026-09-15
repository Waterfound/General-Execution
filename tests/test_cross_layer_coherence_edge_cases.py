import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    ResultEnvelope,
    RunnerRegistry,
    admit_physical_observation,
    authorize_physical_attempt,
    bind_session,
    build_durable_snapshot,
    initialize_capacity_state,
    observe_completed,
    plan_execution,
    reference_runner,
    release_capacity_for_outcome,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.coherence import (
    CoherentSQLiteSessionRegistry,
    inspect_sqlite_execution_coherence,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.session_persistence import SessionPersistenceConflict
from general_execution.session_registry import (
    register_session_transition,
    revoke_session_transition,
    start_session_transition,
)

D = "sha256:" + "e" * 64


def context(suffix="edge"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-coherence-edge",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cross-layer coherence edge {suffix}",
        source_revision=f"source-coherence-edge-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://coherence-edge/{suffix}", D),),
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
        invocation_id=f"gei-coherence-edge-{suffix}-1",
    )
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(state, spec, registry, plan, running, runner, auth)
    return runner, spec, registry, plan, bound, running, auth, grant, state


def register_running(path, ctx):
    runner, _, _, _, bound, _, _, _, _ = ctx
    registry = CoherentSQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    registry.commit_transition(start_session_transition(bound, 2), runner)
    return registry


def test_revocation_release_requires_registry_revoke_catchup(tmp_path):
    path = tmp_path / "revocation.db"
    ctx = context("revocation")
    runner, _, _, _, _, running, _, grant, state = ctx
    registry = register_running(path, ctx)
    revoked = revoke_session(running)
    released_state, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    released = build_durable_snapshot(released_state, runner)
    SQLiteDurableHeadStore(path).compare_and_swap(released, runner, expected_head_digest=None)

    report = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert report.status == "recovery_required"
    assert report.findings == ("REVOCATION_RELEASE_NOT_YET_IN_SESSION_REGISTRY",)
    assert report.required_actions == ("COMMIT_REVOKE_SESSION_TRANSITION",)

    registry.commit_transition(revoke_session_transition(running, 3), runner)
    after = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert after.status == "coherent"
    assert after.session_state == "revoked"


def test_completed_release_without_durable_result_handoff_fails_closed(tmp_path):
    path = tmp_path / "completed-missing-handoff.db"
    ctx = context("completed")
    runner, spec, registry, plan, _, running, auth, grant, state = ctx
    session_registry = register_running(path, ctx)
    result = ResultEnvelope(
        session_id=running.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=running.attempt,
        status="completed",
        evidence=(ArtifactRef("reference-probe-digest", "ge+reference://coherence-edge/completed", D),),
        summary="Completed physical result intentionally persisted without handoff.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-edge-completed")
    outcome = admit_physical_observation(spec, registry, plan, running, runner, auth, observation)
    released_state, _, _ = release_capacity_for_outcome(
        state,
        spec,
        registry,
        plan,
        running,
        runner,
        grant.lease,
        outcome,
    )
    released = build_durable_snapshot(released_state, runner)
    SQLiteDurableHeadStore(path).compare_and_swap(released, runner, expected_head_digest=None)

    report = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert report.status == "inconsistent"
    assert "COMPLETED_RELEASE_MISSING_DURABLE_RESULT_HANDOFF" in report.findings

    with pytest.raises(SessionPersistenceConflict):
        session_registry.commit_transition(revoke_session_transition(running, 3), runner)
