import sqlite3
from concurrent.futures import ThreadPoolExecutor

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
    prepare_logical_result_submission,
    prepare_restart_reconciliation,
    reference_runner,
    reserve_capacity,
    start_session,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.result_handoff import pending_logical_result_from_reconciliation
from general_execution.session_registry import (
    SessionRegistryError,
    register_session_transition,
    revoke_session_transition,
    start_session_transition,
    submit_session_transition,
    verify_session_registry_chain,
)
from general_execution.session_persistence import (
    SESSION_REGISTRY_SCHEMA_VERSION,
    SQLiteSessionRegistry,
    SessionPersistenceConflict,
    SessionPersistenceIntegrityError,
)

D = "sha256:" + "c" * 64


def bound_context(suffix="1", runner=None):
    runner = runner or reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-session-registry",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable Session registry {suffix}",
        source_revision=f"source-session-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://session/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    bound = bind_session(spec, registry, plan)
    return runner, spec, registry, plan, bound


def completed_handoff(path, ctx):
    runner, spec, registry, plan, bound = ctx
    running = start_session(bound)
    auth = authorize_physical_attempt(
        spec,
        registry,
        plan,
        running,
        runner,
        invocation_id=f"gei-registry-{bound.session_id}-1",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, running, runner, auth)
    snapshot = build_durable_snapshot(state, runner)
    result = ResultEnvelope(
        session_id=running.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=running.attempt,
        status="completed",
        evidence=(ArtifactRef("reference-probe-digest", "ge+reference://registry/completed", D),),
        summary="Completed result for durable Session registry.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-registry-completed")
    outcome = admit_physical_observation(spec, registry, plan, running, runner, auth, observation)
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, running, outcome)
    durable = SQLiteDurableHeadStore(path)
    durable.compare_and_swap(snapshot, runner, expected_head_digest=None)
    durable.commit_reconciliation(candidate, runner)
    pending = durable.load_pending_result(runner, running.session_id, running.attempt)
    submission = prepare_logical_result_submission(pending, running, runner)
    durable.commit_result_submission(submission, running, runner)
    return running, submission


def test_register_bound_session_and_recover_after_reopen(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    registry = SQLiteSessionRegistry(path)
    receipt = registry.commit_transition(register_session_transition(bound), runner)
    assert not receipt.idempotent
    reopened = SQLiteSessionRegistry(path)
    assert reopened.load_current(runner, bound.session_id) == bound


def test_start_transition_survives_restart(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    registry = SQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    start = start_session_transition(bound, 2)
    registry.commit_transition(start, runner)
    assert SQLiteSessionRegistry(path).load_current(runner, bound.session_id) == start.target_session


def test_revoke_transition_is_terminal():
    runner, _, _, _, bound = bound_context()
    running = start_session(bound)
    revoked = revoke_session_transition(running, 3)
    with pytest.raises(SessionRegistryError):
        start_session_transition(revoked.target_session, 4)
    with pytest.raises(SessionRegistryError):
        revoke_session_transition(revoked.target_session, 4)


def test_history_replays_exact_lifecycle(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    register = register_session_transition(bound)
    start = start_session_transition(bound, 2)
    revoke = revoke_session_transition(start.target_session, 3)
    for transition in (register, start, revoke):
        store.commit_transition(transition, runner)
    history = store.load_history(runner, bound.session_id)
    assert history == (register, start, revoke)
    assert verify_session_registry_chain(history)
    assert store.load_current(runner, bound.session_id).state == "revoked"


def test_lost_ack_replay_is_idempotent_even_after_later_transition(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    register = register_session_transition(bound)
    start = start_session_transition(bound, 2)
    store.commit_transition(register, runner)
    store.commit_transition(start, runner)
    receipt = store.commit_transition(register, runner)
    assert receipt.idempotent
    assert store.load_current(runner, bound.session_id) == start.target_session


def test_stale_transition_is_rejected(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    register = register_session_transition(bound)
    start = start_session_transition(bound, 2)
    stale_revoke = revoke_session_transition(bound, 2)
    store.commit_transition(register, runner)
    store.commit_transition(start, runner)
    with pytest.raises(SessionPersistenceConflict):
        store.commit_transition(stale_revoke, runner)


def test_submit_result_requires_persisted_handoff(tmp_path):
    path = tmp_path / "sessions.db"
    ctx = bound_context()
    runner, _, _, _, bound = ctx
    running = start_session(bound)
    _, submission = completed_handoff(tmp_path / "other.db", ctx)
    registry = SQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    registry.commit_transition(start_session_transition(bound, 2), runner)
    transition = submit_session_transition(running, submission, runner, 3)
    with pytest.raises(SessionPersistenceConflict):
        registry.commit_transition(transition, runner)


def test_submit_result_transition_recovers_submitted_session(tmp_path):
    path = tmp_path / "sessions.db"
    ctx = bound_context()
    runner, _, _, _, bound = ctx
    running, submission = completed_handoff(path, ctx)
    registry = SQLiteSessionRegistry(path)
    registry.commit_transition(register_session_transition(bound), runner)
    registry.commit_transition(start_session_transition(bound, 2), runner)
    transition = submit_session_transition(running, submission, runner, 3)
    registry.commit_transition(transition, runner)
    reopened = SQLiteSessionRegistry(path)
    recovered = reopened.load_current(runner, bound.session_id)
    assert recovered == submission.submitted_session
    assert recovered.state == "result_submitted"
    assert recovered.result_digest == submission.pending.result.digest


def test_result_submitted_session_is_terminal(tmp_path):
    path = tmp_path / "sessions.db"
    ctx = bound_context()
    runner, _, _, _, bound = ctx
    running, submission = completed_handoff(path, ctx)
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound), runner)
    store.commit_transition(start_session_transition(bound, 2), runner)
    transition = submit_session_transition(running, submission, runner, 3)
    store.commit_transition(transition, runner)
    with pytest.raises(SessionRegistryError):
        revoke_session_transition(transition.target_session, 4)


def test_revoke_and_submit_from_same_running_head_have_one_winner(tmp_path):
    path = tmp_path / "sessions.db"
    ctx = bound_context()
    runner, _, _, _, bound = ctx
    running, submission = completed_handoff(path, ctx)
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound), runner)
    store.commit_transition(start_session_transition(bound, 2), runner)
    revoke = revoke_session_transition(running, 3)
    submit = submit_session_transition(running, submission, runner, 3)

    def commit(transition):
        try:
            SQLiteSessionRegistry(path).commit_transition(transition, runner)
            return "committed"
        except SessionPersistenceConflict:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(commit, (revoke, submit)))
    assert results == ["committed", "stale"]
    assert SQLiteSessionRegistry(path).load_current(runner, bound.session_id).state in {"revoked", "result_submitted"}


def test_head_metadata_corruption_is_detected(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound), runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_session_heads SET session_digest = ? WHERE runner_id = ? AND session_id = ?",
            (D, runner.runner_id, bound.session_id),
        )
    with pytest.raises(SessionPersistenceIntegrityError):
        store.load_current(runner, bound.session_id)


def test_transition_history_corruption_is_detected(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound), runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_session_transitions SET transition_digest = ? WHERE runner_id = ? AND session_id = ?",
            (D, runner.runner_id, bound.session_id),
        )
    with pytest.raises(SessionPersistenceIntegrityError):
        store.load_history(runner, bound.session_id)


def test_runner_capability_change_cannot_adopt_registered_session(tmp_path):
    path = tmp_path / "sessions.db"
    runner, _, _, _, bound = bound_context()
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound), runner)
    changed = reference_runner(runner.runner_id)
    changed = type(changed)(
        runner_id=changed.runner_id,
        provider=changed.provider,
        adapter=changed.adapter,
        adapter_version="2",
        capabilities=changed.capabilities,
        modes=changed.modes,
        max_parallelism=changed.max_parallelism,
    )
    with pytest.raises(SessionPersistenceIntegrityError):
        store.load_current(changed, bound.session_id)


def test_independent_sessions_have_independent_heads(tmp_path):
    path = tmp_path / "sessions.db"
    runner = reference_runner()
    ctx_a = bound_context("a", runner)
    ctx_b = bound_context("b", runner)
    bound_a = ctx_a[4]
    bound_b = ctx_b[4]
    store = SQLiteSessionRegistry(path)
    store.commit_transition(register_session_transition(bound_a), runner)
    store.commit_transition(register_session_transition(bound_b), runner)
    store.commit_transition(start_session_transition(bound_a, 2), runner)
    assert store.load_current(runner, bound_a.session_id).state == "running"
    assert store.load_current(runner, bound_b.session_id).state == "bound"


def test_legacy_durable_store_is_not_retroactively_synthesized(tmp_path):
    path = tmp_path / "legacy.db"
    runner, spec, registry, plan, bound = bound_context()
    running = start_session(bound)
    auth = authorize_physical_attempt(spec, registry, plan, running, runner, invocation_id="gei-legacy-registry")
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, running, runner, auth)
    snapshot = build_durable_snapshot(state, runner)
    SQLiteDurableHeadStore(path).compare_and_swap(snapshot, runner, expected_head_digest=None)
    session_registry = SQLiteSessionRegistry(path)
    assert session_registry.load_current(runner, running.session_id) is None
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM ge_session_registry_metadata WHERE key='schema_version'"
        ).fetchone()[0]
    assert version == SESSION_REGISTRY_SCHEMA_VERSION
