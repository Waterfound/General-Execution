import sqlite3
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
    authorize_retry,
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
from general_execution.physical import PhysicalAttemptError
from general_execution.reconciliation import (
    ReconciliationError,
    prepare_restart_reconciliation,
    verify_reconciliation_candidate,
)

D = "sha256:" + "a" * 64
ZERO = "sha256:" + "0" * 64


def context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-reconciliation-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Restart reconciliation {suffix}",
        source_revision=f"source-reconcile-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://reconcile/{suffix}", D),),
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
        invocation_id=f"gei-reconcile-{suffix}-1",
    )
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(state, spec, registry, plan, session, runner, auth)
    snapshot = build_durable_snapshot(state, runner)
    return runner, spec, registry, plan, session, auth, grant, snapshot


def failure_outcome(ctx, provider_id="provider-timeout-1", code="reference.timeout"):
    runner, spec, registry, plan, session, auth, _, _ = ctx
    observation = observe_failure(
        auth,
        "timed_out",
        failure_code=code,
        provider_invocation_id=provider_id,
    )
    return admit_physical_observation(spec, registry, plan, session, runner, auth, observation)


def completed_outcome(ctx):
    runner, spec, registry, plan, session, auth, _, _ = ctx
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=session.attempt,
        status="completed",
        evidence=(ArtifactRef("reference-probe-digest", "ge+reference://late/completed", D),),
        summary="Late provider completion recovered after restart.",
    )
    observation = observe_completed(auth, result, provider_invocation_id="provider-completed-1")
    return admit_physical_observation(spec, registry, plan, session, runner, auth, observation)


def test_failure_reconciliation_releases_recovered_capacity():
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    outcome = failure_outcome(ctx)
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome)
    assert verify_reconciliation_candidate(candidate, runner)
    assert candidate.successor_snapshot.state.active_leases == ()
    assert candidate.record.transport_status == "timed_out"
    assert candidate.record.result_digest is None


def test_completed_reconciliation_releases_capacity_without_mutating_session():
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    outcome = completed_outcome(ctx)
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome)
    assert candidate.successor_snapshot.state.active_leases == ()
    assert candidate.record.transport_status == "completed"
    assert candidate.record.result_digest == outcome.result.digest
    assert session.state == "running"
    with pytest.raises(PhysicalAttemptError):
        authorize_retry(spec, registry, plan, session, runner, outcome, invocation_id="gei-no-retry")


def test_failure_reconciliation_preserves_retry_lineage():
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    outcome = failure_outcome(ctx)
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome)
    retry = authorize_retry(spec, registry, plan, session, runner, outcome, invocation_id="gei-reconcile-retry-2")
    state, grant, _ = reserve_capacity(candidate.successor_snapshot.state, spec, registry, plan, session, runner, retry)
    assert grant.lease.physical_attempt == 2
    assert grant.lease.previous_receipt_digest == outcome.receipt.digest
    assert len(state.active_leases) == 1


def test_outcome_for_other_authorization_cannot_reconcile_snapshot():
    ctx_a = context("a")
    ctx_b = context("b")
    runner, spec, registry, plan, session, _, _, snapshot = ctx_a
    outcome_b = failure_outcome(ctx_b)
    with pytest.raises(ReconciliationError):
        prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, outcome_b)


def test_reconciliation_record_tamper_is_detected():
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    changed = replace(candidate, record=replace(candidate.record, source_snapshot_digest=ZERO))
    assert not verify_reconciliation_candidate(changed, runner)


def test_changed_session_context_invalidates_candidate(tmp_path):
    ctx = context("base")
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    other_session = context("other")[4]
    changed = replace(candidate, session=other_session)
    assert not verify_reconciliation_candidate(changed, runner)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    with pytest.raises(PersistenceIntegrityError):
        store.commit_reconciliation(changed, runner)


def test_changed_provider_outcome_invalidates_existing_release_binding():
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    first_outcome = failure_outcome(ctx, "provider-a", "a.timeout")
    second_outcome = failure_outcome(ctx, "provider-b", "b.timeout")
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, first_outcome)
    changed = replace(candidate, outcome=second_outcome)
    assert not verify_reconciliation_candidate(changed, runner)


def test_atomic_commit_persists_record_and_successor_head(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    receipt = store.commit_reconciliation(candidate, runner)
    assert not receipt.idempotent
    assert store.load_current(runner) == candidate.successor_snapshot
    assert store.load_reconciliation(runner, candidate.record.authorization_id) == candidate.record


def test_repeat_after_lost_reconciliation_ack_is_idempotent(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    store.commit_reconciliation(candidate, runner)
    receipt = store.commit_reconciliation(candidate, runner)
    assert receipt.idempotent
    assert receipt.reconciliation_id == candidate.record.reconciliation_id


def test_same_authorization_cannot_have_two_canonical_outcomes(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    first = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx, "provider-a", "a.timeout"))
    second = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx, "provider-b", "b.timeout"))
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    store.commit_reconciliation(first, runner)
    with pytest.raises(PersistenceConflict):
        store.commit_reconciliation(second, runner)


def test_stale_source_head_cannot_be_reconciled(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    retry = authorize_retry(spec, registry, plan, session, runner, candidate.outcome, invocation_id="gei-stale-retry")
    next_state, _, _ = reserve_capacity(candidate.successor_snapshot.state, spec, registry, plan, session, runner, retry)
    advanced = build_durable_snapshot(next_state, runner, previous=candidate.successor_snapshot)
    store.compare_and_swap(candidate.successor_snapshot, runner, expected_head_digest=snapshot.head.digest)
    store.compare_and_swap(advanced, runner, expected_head_digest=candidate.successor_snapshot.head.digest)
    with pytest.raises(PersistenceConflict):
        store.commit_reconciliation(candidate, runner)


def test_idempotent_replay_still_works_after_head_advances(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    store.commit_reconciliation(candidate, runner)
    retry = authorize_retry(spec, registry, plan, session, runner, candidate.outcome, invocation_id="gei-after-ack-retry")
    next_state, _, _ = reserve_capacity(candidate.successor_snapshot.state, spec, registry, plan, session, runner, retry)
    advanced = build_durable_snapshot(next_state, runner, previous=candidate.successor_snapshot)
    store.compare_and_swap(advanced, runner, expected_head_digest=candidate.successor_snapshot.head.digest)
    receipt = store.commit_reconciliation(candidate, runner)
    assert receipt.idempotent
    assert store.load_current(runner) == advanced


def test_v1_store_metadata_migrates_to_v2(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE ge_store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO ge_store_metadata VALUES ('schema_version', 'ge.sqlite-durable-head-store.v1')")
        connection.execute(
            "CREATE TABLE ge_durable_heads (runner_id TEXT PRIMARY KEY, head_digest TEXT NOT NULL, generation INTEGER NOT NULL, snapshot_digest TEXT NOT NULL, snapshot_payload TEXT NOT NULL)"
        )
    SQLiteDurableHeadStore(path)
    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT value FROM ge_store_metadata WHERE key='schema_version'").fetchone()[0]
        table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ge_reconciliations'").fetchone()
    assert version == STORE_SCHEMA_VERSION
    assert table is not None


def test_reconciliation_survives_store_reopen(tmp_path):
    ctx = context()
    runner, spec, registry, plan, session, _, _, snapshot = ctx
    candidate = prepare_restart_reconciliation(snapshot, runner, spec, registry, plan, session, failure_outcome(ctx))
    path = tmp_path / "heads.db"
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    store.commit_reconciliation(candidate, runner)
    reopened = SQLiteDurableHeadStore(path)
    assert reopened.load_current(runner) == candidate.successor_snapshot
    assert reopened.load_reconciliation(runner, candidate.record.authorization_id) == candidate.record
