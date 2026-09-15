import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    authorize_physical_attempt,
    bind_session,
    build_durable_snapshot,
    initialize_capacity_state,
    plan_execution,
    reference_runner,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.persistence import (
    PersistenceCommitReceipt,
    PersistenceConflict,
    PersistenceIntegrityError,
    SQLiteDurableHeadStore,
)

D = "sha256:" + "f" * 64
ZERO = "sha256:" + "0" * 64


def active_context(runner=None, suffix="1"):
    runner = runner or reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-persistence-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Persistence conformance {suffix}",
        source_revision=f"source-persistence-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://persistence/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-persistence-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(
        state,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    return runner, session, state, grant


def successor(runner, session, state, grant, previous):
    revoked = revoke_session(session)
    next_state, _, _ = release_capacity_for_revocation(
        state,
        runner,
        grant.lease,
        revoked,
    )
    return next_state, build_durable_snapshot(next_state, runner, previous=previous)


def test_initial_commit_survives_reopen(tmp_path):
    path = tmp_path / "heads.db"
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    receipt = SQLiteDurableHeadStore(path).compare_and_swap(
        snapshot,
        runner,
        expected_head_digest=None,
    )
    reopened = SQLiteDurableHeadStore(path)
    assert reopened.load_current(runner) == snapshot
    assert receipt.previous_head_digest is None
    assert receipt.committed_head_digest == snapshot.head.digest
    assert not receipt.idempotent


def test_successor_commit_advances_exact_head(tmp_path):
    path = tmp_path / "heads.db"
    runner, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(first, runner, expected_head_digest=None)
    _, second = successor(runner, session, state, grant, first)
    receipt = store.compare_and_swap(
        second,
        runner,
        expected_head_digest=first.head.digest,
    )
    assert store.load_current(runner) == second
    assert receipt.previous_head_digest == first.head.digest
    assert receipt.committed_head_digest == second.head.digest


def test_two_concurrent_writers_from_same_head_have_one_winner(tmp_path):
    path = tmp_path / "heads.db"
    runner, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    SQLiteDurableHeadStore(path).compare_and_swap(first, runner, expected_head_digest=None)
    _, second = successor(runner, session, state, grant, first)

    def write_once():
        store = SQLiteDurableHeadStore(path)
        try:
            store.compare_and_swap(
                second,
                runner,
                expected_head_digest=first.head.digest,
            )
            return "committed"
        except PersistenceConflict:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(lambda _: write_once(), range(2)))
    assert results == ["committed", "stale"]
    assert SQLiteDurableHeadStore(path).load_current(runner) == second


def test_repeat_after_lost_ack_is_idempotent(tmp_path):
    path = tmp_path / "heads.db"
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    receipt = store.compare_and_swap(
        snapshot,
        runner,
        expected_head_digest=snapshot.head.digest,
    )
    assert receipt.idempotent
    assert receipt.previous_head_digest == snapshot.head.digest
    assert receipt.committed_head_digest == snapshot.head.digest


def test_stale_expected_head_is_rejected(tmp_path):
    path = tmp_path / "heads.db"
    runner, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(first, runner, expected_head_digest=None)
    _, second = successor(runner, session, state, grant, first)
    store.compare_and_swap(second, runner, expected_head_digest=first.head.digest)
    with pytest.raises(PersistenceConflict):
        store.compare_and_swap(second, runner, expected_head_digest=first.head.digest)


def test_empty_store_rejects_snapshot_with_unstored_predecessor(tmp_path):
    runner, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    _, second = successor(runner, session, state, grant, first)
    with pytest.raises(PersistenceConflict):
        SQLiteDurableHeadStore(tmp_path / "empty.db").compare_and_swap(
            second,
            runner,
            expected_head_digest=None,
        )


def test_older_snapshot_cannot_replace_newer_head(tmp_path):
    path = tmp_path / "heads.db"
    runner, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(first, runner, expected_head_digest=None)
    _, second = successor(runner, session, state, grant, first)
    store.compare_and_swap(second, runner, expected_head_digest=first.head.digest)
    with pytest.raises(PersistenceConflict):
        store.compare_and_swap(first, runner, expected_head_digest=second.head.digest)


def test_same_runner_id_with_changed_capabilities_cannot_adopt_head(tmp_path):
    path = tmp_path / "heads.db"
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    changed = replace(runner, adapter_version="2")
    with pytest.raises(PersistenceIntegrityError):
        store.load_current(changed)


def test_runners_have_independent_canonical_heads(tmp_path):
    path = tmp_path / "heads.db"
    runner_a = reference_runner("runner-a")
    runner_b = reference_runner("runner-b")
    _, _, state_a, _ = active_context(runner_a, "a")
    _, _, state_b, _ = active_context(runner_b, "b")
    snapshot_a = build_durable_snapshot(state_a, runner_a)
    snapshot_b = build_durable_snapshot(state_b, runner_b)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot_a, runner_a, expected_head_digest=None)
    store.compare_and_swap(snapshot_b, runner_b, expected_head_digest=None)
    assert store.load_current(runner_a) == snapshot_a
    assert store.load_current(runner_b) == snapshot_b


def test_stored_row_metadata_must_match_snapshot(tmp_path):
    path = tmp_path / "heads.db"
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_durable_heads SET generation = generation + 1 WHERE runner_id = ?",
            (runner.runner_id,),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.load_current(runner)


def test_store_schema_version_is_checked_on_reopen(tmp_path):
    path = tmp_path / "heads.db"
    SQLiteDurableHeadStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_store_metadata SET value = 'unsupported' WHERE key = 'schema_version'"
        )
    with pytest.raises(PersistenceIntegrityError):
        SQLiteDurableHeadStore(path)


def test_initial_commit_with_nonempty_expected_head_is_rejected(tmp_path):
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    with pytest.raises(PersistenceConflict):
        SQLiteDurableHeadStore(tmp_path / "heads.db").compare_and_swap(
            snapshot,
            runner,
            expected_head_digest=ZERO,
        )


def test_memory_database_is_rejected_for_durable_store():
    with pytest.raises(ValueError):
        SQLiteDurableHeadStore(":memory:")


def test_expected_head_digest_must_be_sha256(tmp_path):
    runner, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    store = SQLiteDurableHeadStore(tmp_path / "heads.db")
    with pytest.raises(ValueError):
        store.compare_and_swap(
            snapshot,
            runner,
            expected_head_digest="not-a-digest",
        )


def test_receipt_schema_is_runtime_checked():
    with pytest.raises(ValueError):
        PersistenceCommitReceipt(
            runner_id="runner",
            previous_head_digest=None,
            committed_head_digest=ZERO,
            generation=0,
            snapshot_digest=ZERO,
            idempotent=False,
            schema_version="ge.persistence-commit-receipt.v999",
        )
