import sqlite3

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
    reference_runner,
    reserve_capacity,
    start_session,
)
from general_execution.persistence import (
    PersistenceConflict,
    PersistenceIntegrityError,
    SQLiteDurableHeadStore,
    STORE_SCHEMA_VERSION,
)
from general_execution.reconciliation import prepare_restart_reconciliation
from general_execution.result_handoff import (
    ResultHandoffError,
    pending_logical_result_from_reconciliation,
    prepare_logical_result_submission,
    verify_logical_result_submission,
)

D = "sha256:" + "b" * 64


def context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-result-handoff",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable logical result {suffix}",
        source_revision=f"source-result-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://result/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    auth = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-result-{suffix}-1",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, spec, registry, plan, session, runner, auth)
    snapshot = build_durable_snapshot(state, runner)
    return runner, spec, registry, plan, session, auth, snapshot


def completed_candidate(ctx, *, result_status="completed"):
    runner, spec, registry, plan, session, auth, snapshot = ctx
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=session.attempt,
        status=result_status,
        evidence=(ArtifactRef("reference-probe-digest", f"ge+reference://result/{result_status}", D),),
        summary=f"Recovered logical result with status {result_status}.",
    )
    observation = observe_completed(auth, result, provider_invocation_id=f"provider-{result_status}")
    outcome = admit_physical_observation(spec, registry, plan, session, runner, auth, observation)
    return prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome)


def failure_candidate(ctx):
    runner, spec, registry, plan, session, auth, snapshot = ctx
    observation = observe_failure(
        auth,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-timeout",
    )
    outcome = admit_physical_observation(spec, registry, plan, session, runner, auth, observation)
    return prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome)


def persist_source(store, ctx):
    runner, _, _, _, _, _, snapshot = ctx
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)


def test_completed_reconciliation_atomically_creates_pending_result(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    pending = store.load_pending_result(runner, session.session_id, session.attempt)
    assert pending == pending_logical_result_from_reconciliation(candidate, runner)
    assert store.load_result_submission(runner, session.session_id, session.attempt) is None


def test_failed_transport_reconciliation_creates_no_pending_result(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = failure_candidate(ctx)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    assert store.load_pending_result(runner, session.session_id, session.attempt) is None


def test_pending_result_survives_store_reopen(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    expected = store.load_pending_result(runner, session.session_id, session.attempt)
    reopened = SQLiteDurableHeadStore(path)
    assert reopened.load_pending_result(runner, session.session_id, session.attempt) == expected


def test_pending_result_submits_to_exact_running_session():
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    pending = pending_logical_result_from_reconciliation(candidate, runner)
    submission = prepare_logical_result_submission(pending, session, runner)
    assert verify_logical_result_submission(submission, session, runner)
    assert submission.submitted_session.state == "result_submitted"
    assert submission.submitted_session.result_digest == pending.result.digest


def test_wrong_session_cannot_consume_pending_result():
    ctx = context("base")
    runner, _, _, _, _, _, _ = ctx
    pending = pending_logical_result_from_reconciliation(completed_candidate(ctx), runner)
    other_session = context("other")[4]
    with pytest.raises(ResultHandoffError):
        prepare_logical_result_submission(pending, other_session, runner)


def test_submission_commit_survives_second_restart(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    pending = store.load_pending_result(runner, session.session_id, session.attempt)
    submission = prepare_logical_result_submission(pending, session, runner)
    receipt = store.commit_result_submission(submission, session, runner)
    assert not receipt.idempotent
    reopened = SQLiteDurableHeadStore(path)
    recovered = reopened.load_result_submission(runner, session.session_id, session.attempt)
    assert recovered == submission
    assert recovered.submitted_session == submission.submitted_session


def test_lost_submission_ack_replay_is_idempotent(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    pending = store.load_pending_result(runner, session.session_id, session.attempt)
    submission = prepare_logical_result_submission(pending, session, runner)
    store.commit_result_submission(submission, session, runner)
    receipt = store.commit_result_submission(submission, session, runner)
    assert receipt.idempotent
    assert receipt.submission_id == submission.submission_id


def test_submission_without_persisted_pending_is_rejected(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    pending = pending_logical_result_from_reconciliation(candidate, runner)
    submission = prepare_logical_result_submission(pending, session, runner)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    with pytest.raises(PersistenceConflict):
        store.commit_result_submission(submission, session, runner)


def test_missing_pending_breaks_idempotent_completed_reconciliation(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
            (runner.runner_id, session.session_id, session.attempt),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.commit_reconciliation(candidate, runner)


def test_pending_metadata_corruption_is_detected(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_pending_results SET result_digest = ? WHERE runner_id = ? AND session_id = ?",
            (D, runner.runner_id, session.session_id),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.load_pending_result(runner, session.session_id, session.attempt)


def test_submission_metadata_corruption_is_detected(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    pending = store.load_pending_result(runner, session.session_id, session.attempt)
    submission = prepare_logical_result_submission(pending, session, runner)
    store.commit_result_submission(submission, session, runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_result_submissions SET submitted_session_digest = ? WHERE runner_id = ? AND session_id = ?",
            (D, runner.runner_id, session.session_id),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.load_result_submission(runner, session.session_id, session.attempt)


def test_result_status_failed_is_still_a_durable_logical_result(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx, result_status="failed")
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    pending = store.load_pending_result(runner, session.session_id, session.attempt)
    assert pending.result.status == "failed"
    submission = prepare_logical_result_submission(pending, session, runner)
    assert submission.submitted_session.result_digest == pending.result.digest


def test_v2_store_migrates_to_v3(tmp_path):
    path = tmp_path / "legacy-v2.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE ge_store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO ge_store_metadata VALUES ('schema_version', 'ge.sqlite-durable-head-store.v2')")
        connection.execute(
            "CREATE TABLE ge_durable_heads (runner_id TEXT PRIMARY KEY, head_digest TEXT NOT NULL, generation INTEGER NOT NULL, snapshot_digest TEXT NOT NULL, snapshot_payload TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE ge_reconciliations (runner_id TEXT NOT NULL, authorization_id TEXT NOT NULL, reconciliation_id TEXT NOT NULL UNIQUE, reconciliation_digest TEXT NOT NULL, previous_head_digest TEXT NOT NULL, committed_head_digest TEXT NOT NULL, record_payload TEXT NOT NULL, PRIMARY KEY (runner_id, authorization_id))"
        )
    SQLiteDurableHeadStore(path)
    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT value FROM ge_store_metadata WHERE key='schema_version'").fetchone()[0]
        pending_table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ge_pending_results'").fetchone()
        submissions_table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ge_result_submissions'").fetchone()
    assert version == STORE_SCHEMA_VERSION
    assert pending_table is not None
    assert submissions_table is not None


def test_orphan_pending_without_reconciliation_is_rejected(tmp_path):
    ctx = context()
    runner, _, _, _, session, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
            (runner.runner_id, candidate.record.authorization_id),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.load_pending_result(runner, session.session_id, session.attempt)


def test_v2_completed_reconciliation_migration_fails_closed(tmp_path):
    ctx = context()
    runner, _, _, _, _, _, _ = ctx
    candidate = completed_candidate(ctx)
    path = tmp_path / "completed-v2.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE ge_pending_results")
        connection.execute("DROP TABLE ge_result_submissions")
        connection.execute(
            "UPDATE ge_store_metadata SET value = 'ge.sqlite-durable-head-store.v2' WHERE key = 'schema_version'"
        )
    with pytest.raises(PersistenceIntegrityError):
        SQLiteDurableHeadStore(path)


def test_v2_failure_only_reconciliation_migrates_safely(tmp_path):
    ctx = context()
    runner, _, _, _, _, _, _ = ctx
    candidate = failure_candidate(ctx)
    path = tmp_path / "failure-v2.db"
    store = SQLiteDurableHeadStore(path)
    persist_source(store, ctx)
    store.commit_reconciliation(candidate, runner)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE ge_pending_results")
        connection.execute("DROP TABLE ge_result_submissions")
        connection.execute(
            "UPDATE ge_store_metadata SET value = 'ge.sqlite-durable-head-store.v2' WHERE key = 'schema_version'"
        )
    reopened = SQLiteDurableHeadStore(path)
    assert reopened.load_reconciliation(runner, candidate.record.authorization_id) == candidate.record
    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT value FROM ge_store_metadata WHERE key='schema_version'").fetchone()[0]
        pending_table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ge_pending_results'").fetchone()
        submissions_table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ge_result_submissions'").fetchone()
    assert version == STORE_SCHEMA_VERSION
    assert pending_table is not None
    assert submissions_table is not None
