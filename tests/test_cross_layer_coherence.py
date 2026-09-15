from dataclasses import replace

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
    observe_failure,
    plan_execution,
    prepare_logical_result_submission,
    prepare_restart_reconciliation,
    reference_runner,
    release_capacity_for_outcome,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.coherence import (
    CoherentSQLiteSessionRegistry,
    assess_execution_coherence,
    inspect_sqlite_execution_coherence,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.session_persistence import SQLiteSessionRegistry, SessionPersistenceConflict
from general_execution.session_registry import (
    register_session_transition,
    revoke_session_transition,
    start_session_transition,
    submit_session_transition,
)

D = "sha256:" + "d" * 64


def context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-coherence",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Cross-layer coherence {suffix}",
        source_revision=f"source-coherence-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://coherence/{suffix}", D),),
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
        invocation_id=f"gei-coherence-{suffix}-1",
    )
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(state, spec, registry, plan, running, runner, auth)
    active = build_durable_snapshot(state, runner)
    return runner, spec, registry, plan, bound, running, auth, grant, state, active


def failed_release(ctx):
    runner, spec, registry, plan, _, running, auth, grant, state, _ = ctx
    observation = observe_failure(
        auth,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-timeout",
    )
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
    return outcome, build_durable_snapshot(released_state, runner)


def completed_handoff(path, ctx):
    runner, spec, registry, plan, _, running, auth, _, _, active = ctx
    result = ResultEnvelope(
        session_id=running.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=running.attempt,
        status="completed",
        evidence=(ArtifactRef("reference-probe-digest", "ge+reference://coherence/completed", D),),
        summary="Completed result for coherence testing.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-coherence-completed")
    outcome = admit_physical_observation(spec, registry, plan, running, runner, auth, observation)
    candidate = prepare_restart_reconciliation(active, runner, spec, registry, plan, running, outcome)
    durable = SQLiteDurableHeadStore(path)
    durable.compare_and_swap(active, runner, expected_head_digest=None)
    durable.commit_reconciliation(candidate, runner)
    pending = durable.load_pending_result(runner, running.session_id, running.attempt)
    return durable, candidate, pending


def register_bound(path, ctx, *, coherent=True):
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    registry = CoherentSQLiteSessionRegistry(path) if coherent else SQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    return registry


def register_running(path, ctx):
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    registry = CoherentSQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    registry.commit_transition(start_session_transition(bound, 2), runner)
    return registry


def test_bound_with_active_capacity_requires_start_recovery(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, active = ctx
    register_bound(path, ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(active, runner, expected_head_digest=None)
    report = inspect_sqlite_execution_coherence(path, runner, bound.session_id)
    assert report.status == "recovery_required"
    assert report.findings == ("BOUND_SESSION_HAS_PHYSICAL_HISTORY",)
    assert report.required_actions == ("COMMIT_START_SESSION_TRANSITION",)
    assert report.capacity_transition_count == 1
    assert len(report.active_lease_ids) == 1


def test_bound_with_released_capacity_history_still_requires_start_recovery(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    register_bound(path, ctx)
    _, released = failed_release(ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(released, runner, expected_head_digest=None)
    report = inspect_sqlite_execution_coherence(path, runner, bound.session_id)
    assert report.status == "recovery_required"
    assert report.capacity_transition_count == 2
    assert report.active_lease_ids == ()
    assert report.required_actions == ("COMMIT_START_SESSION_TRANSITION",)


def test_start_catchup_is_allowed_with_active_capacity(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, running, _, _, _, active = ctx
    registry = register_bound(path, ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(active, runner, expected_head_digest=None)
    registry.commit_transition(start_session_transition(bound, 2), runner)
    assert registry.load_current(runner, bound.session_id) == running
    assert inspect_sqlite_execution_coherence(path, runner, bound.session_id).status == "coherent"


def test_registration_over_released_legacy_history_is_rejected_atomically(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    _, released = failed_release(ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(released, runner, expected_head_digest=None)
    registry = CoherentSQLiteSessionRegistry(path)
    with pytest.raises(SessionPersistenceConflict):
        registry.commit_transition(register_session_transition(bound), runner)
    assert registry.load_current(runner, bound.session_id) is None


def test_missing_registry_with_released_physical_history_is_legacy_untracked(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    _, released = failed_release(ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(released, runner, expected_head_digest=None)
    report = inspect_sqlite_execution_coherence(path, runner, bound.session_id)
    assert report.status == "legacy_untracked"
    assert report.capacity_transition_count == 2
    assert report.required_actions == ("KEEP_LEGACY_STATE_UNSYNTHESIZED",)


def test_missing_registry_without_execution_state_is_coherent(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    CoherentSQLiteSessionRegistry(path)
    report = inspect_sqlite_execution_coherence(path, runner, bound.session_id)
    assert report.status == "coherent"
    assert report.capacity_transition_count == 0


def test_revoke_with_active_capacity_is_rejected(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, _, running, _, _, _, active = ctx
    registry = register_running(path, ctx)
    SQLiteDurableHeadStore(path).compare_and_swap(active, runner, expected_head_digest=None)
    with pytest.raises(SessionPersistenceConflict):
        registry.commit_transition(revoke_session_transition(running, 3), runner)
    assert registry.load_current(runner, running.session_id).state == "running"


def test_running_with_pending_result_requires_handoff_completion(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, _, running, _, _, _, _ = ctx
    register_running(path, ctx)
    _, _, pending = completed_handoff(path, ctx)
    report = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert report.status == "recovery_required"
    assert report.pending_id == pending.pending_id
    assert report.required_actions == ("PREPARE_AND_COMMIT_LOGICAL_RESULT_SUBMISSION",)


def test_running_with_durable_submission_requires_registry_catchup(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, _, running, _, _, _, _ = ctx
    register_running(path, ctx)
    durable, _, pending = completed_handoff(path, ctx)
    submission = prepare_logical_result_submission(pending, running, runner)
    durable.commit_result_submission(submission, running, runner)
    report = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert report.status == "recovery_required"
    assert report.submission_id == submission.submission_id
    assert report.required_actions == ("COMMIT_SUBMIT_RESULT_SESSION_TRANSITION",)


def test_result_submitted_is_cross_layer_coherent(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, _, running, _, _, _, _ = ctx
    registry = register_running(path, ctx)
    durable, _, pending = completed_handoff(path, ctx)
    submission = prepare_logical_result_submission(pending, running, runner)
    durable.commit_result_submission(submission, running, runner)
    registry.commit_transition(submit_session_transition(running, submission, runner, 3), runner)
    report = inspect_sqlite_execution_coherence(path, runner, running.session_id)
    assert report.status == "coherent"
    assert report.session_state == "result_submitted"
    assert report.active_lease_ids == ()


def test_revoked_session_with_active_capacity_is_inconsistent_by_model():
    ctx = context()
    runner, _, _, _, _, running, _, _, _, active = ctx
    revoked = revoke_session(running)
    report = assess_execution_coherence(
        runner,
        running.session_id,
        session=revoked,
        capacity_snapshot=active,
        pending=None,
        submission=None,
    )
    assert report.status == "inconsistent"
    assert "REVOKED_SESSION_HAS_ACTIVE_CAPACITY" in report.findings


def test_bound_session_with_result_handoff_state_is_inconsistent(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, _ = ctx
    _, _, pending = completed_handoff(path, ctx)
    report = assess_execution_coherence(
        runner,
        bound.session_id,
        session=bound,
        capacity_snapshot=SQLiteDurableHeadStore(path).load_current(runner),
        pending=pending,
        submission=None,
        raw_pending_exists=True,
    )
    assert report.status == "inconsistent"
    assert "BOUND_SESSION_HAS_RESULT_HANDOFF_STATE" in report.findings


def test_orphan_submission_is_inconsistent_by_model(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, _, running, _, _, _, _ = ctx
    durable, _, pending = completed_handoff(path, ctx)
    submission = prepare_logical_result_submission(pending, running, runner)
    report = assess_execution_coherence(
        runner,
        running.session_id,
        session=running,
        capacity_snapshot=durable.load_current(runner),
        pending=None,
        submission=submission,
        raw_pending_exists=False,
        raw_submission_exists=True,
    )
    assert report.status == "inconsistent"
    assert "ORPHAN_RESULT_SUBMISSION" in report.findings


def test_replaying_old_register_remains_idempotent_after_physical_history(tmp_path):
    path = tmp_path / "coherence.db"
    ctx = context()
    runner, _, _, _, bound, _, _, _, _, active = ctx
    registry = CoherentSQLiteSessionRegistry(path)
    transition = register_session_transition(bound)
    registry.commit_transition(transition, runner)
    SQLiteDurableHeadStore(path).compare_and_swap(active, runner, expected_head_digest=None)
    receipt = registry.commit_transition(transition, runner)
    assert receipt.idempotent


def test_coherence_report_digest_is_deterministic():
    ctx = context()
    runner, _, _, _, _, running, _, _, _, active = ctx
    first = assess_execution_coherence(
        runner,
        running.session_id,
        session=running,
        capacity_snapshot=active,
        pending=None,
        submission=None,
    )
    second = replace(first)
    assert first == second
    assert first.digest == second.digest
