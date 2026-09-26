import json
import sqlite3
from dataclasses import replace

import pytest

from general_execution import (
    CheckpointEvidence,
    ExecutionCheckpoint,
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioPersistenceError,
    PortfolioState,
    SqlitePortfolioHeadStore,
    WakeCondition,
    deserialize_portfolio_snapshot,
    portfolio_snapshot,
    recover_portfolio_after_restart,
    serialize_checkpoint,
    serialize_portfolio_snapshot,
    verify_portfolio_recovery,
)

D = "sha256:" + "a" * 64


def active(**changes):
    values = dict(
        work_id="ACTIVE",
        role="active",
        state="running",
        objective="Run active work",
        active_gate="ACTIVE_GATE",
        next_action_ref="action://active",
        source_revision="src-a",
        evidence_required=("result",),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def secondary():
    return PortfolioEntry(
        work_id="SECONDARY",
        role="secondary",
        state="ready",
        objective="Prepare secondary work",
        active_gate="SECONDARY_GATE",
        next_action_ref="action://secondary",
        source_revision="src-b",
    )


def passive():
    return PortfolioEntry(
        work_id="PASSIVE",
        role="passive",
        state="passive",
        objective="Wait for external dependency",
        active_gate="PASSIVE_GATE",
        next_action_ref="action://passive",
        source_revision="src-c",
        blockers=(
            PortfolioBlocker(
                kind="external_dependency",
                detail="provider unavailable",
            ),
        ),
        wake_condition=WakeCondition(
            kind="event_received",
            value="provider.available",
        ),
    )


def genesis():
    return PortfolioState(
        portfolio_id="portfolio-1",
        generation=0,
        active=active(),
        secondary=secondary(),
        passive=(passive(),),
    )


def next_state(current, *, active_state="verifying"):
    return PortfolioState(
        portfolio_id=current.portfolio_id,
        generation=current.generation + 1,
        active=replace(current.active, state=active_state),
        secondary=current.secondary,
        passive=current.passive,
        previous_state_digest=current.digest,
    )


def checkpoint(state, *, before="running", after="verifying"):
    return ExecutionCheckpoint(
        portfolio_id=state.portfolio_id,
        portfolio_generation=state.generation,
        portfolio_state_digest=state.digest,
        work_id="ACTIVE",
        role="active",
        state_before=before,
        state_after=after,
        action_ref="action://active",
        source_revision="src-a",
        observed_at="2026-09-23T13:00:00-03:00",
        summary="bounded step completed",
        evidence=(CheckpointEvidence("test", "artifact://proof", D),),
        canonical_refs=("commit:abc",),
        next_transition_refs=("transition://verify",),
    )


def test_snapshot_round_trip_is_exact():
    state = genesis()
    encoded = serialize_portfolio_snapshot(state)
    decoded, snapshot_digest = deserialize_portfolio_snapshot(encoded)
    assert decoded == state
    assert snapshot_digest == portfolio_snapshot(state)["snapshot_digest"]


def test_initialize_and_generation_zero_restart(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    head = store.initialize(state)
    restarted = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    loaded, loaded_head = restarted.load(state.portfolio_id)
    assert loaded == state
    assert loaded_head == head
    assert restarted.latest_checkpoint(state.portfolio_id) is None

    recovered, cp, report = recover_portfolio_after_restart(
        restarted, state.portfolio_id
    )
    assert recovered == state
    assert cp is None
    assert verify_portfolio_recovery(recovered, loaded_head, cp, report)


def test_initialize_is_idempotent_only_for_identical_state(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    assert store.initialize(state) == store.initialize(state)
    changed = replace(state, active=active(objective="different"))
    with pytest.raises(PortfolioPersistenceError, match="different state"):
        store.initialize(changed)


def test_initialize_rejects_nonzero_generation(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    with pytest.raises(PortfolioPersistenceError, match="requires generation zero"):
        store.initialize(next_state(state))


def test_commit_atomically_advances_state_and_checkpoint(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    cp = checkpoint(updated)
    head = store.commit(state.portfolio_id, state.digest, updated, cp)
    loaded, loaded_head = store.load(state.portfolio_id)
    assert loaded == updated
    assert loaded_head == head
    assert head.latest_checkpoint_digest == cp.digest
    assert store.latest_checkpoint(state.portfolio_id) == cp


def test_restart_recovers_latest_state_and_checkpoint(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    cp = checkpoint(updated)
    store.commit(state.portfolio_id, state.digest, updated, cp)

    restarted = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    recovered, recovered_cp, report = recover_portfolio_after_restart(
        restarted, state.portfolio_id
    )
    _, head = restarted.load(state.portfolio_id)
    assert recovered == updated
    assert recovered_cp == cp
    assert report.checkpoint_present
    assert verify_portfolio_recovery(recovered, head, recovered_cp, report)


def test_stale_compare_and_swap_is_rejected(tmp_path):
    state = genesis()
    store_a = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store_a.initialize(state)
    store_b = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")

    first = next_state(state)
    first_cp = checkpoint(first)
    second = next_state(state, active_state="rework")
    second_cp = checkpoint(second, after="rework")
    store_a.commit(state.portfolio_id, state.digest, first, first_cp)

    with pytest.raises(PortfolioPersistenceError, match="stale durable portfolio head"):
        store_b.commit(state.portfolio_id, state.digest, second, second_cp)


def test_generation_skip_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    skipped = PortfolioState(
        portfolio_id=state.portfolio_id,
        generation=2,
        active=state.active,
        secondary=state.secondary,
        passive=state.passive,
        previous_state_digest=state.digest,
    )
    cp = replace(
        checkpoint(next_state(state)),
        portfolio_generation=2,
        portfolio_state_digest=skipped.digest,
    )
    with pytest.raises(PortfolioPersistenceError, match="advance exactly one generation"):
        store.commit(state.portfolio_id, state.digest, skipped, cp)


def test_wrong_predecessor_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = replace(next_state(state), previous_state_digest=D)
    cp = replace(checkpoint(next_state(state)), portfolio_state_digest=updated.digest)
    with pytest.raises(PortfolioPersistenceError, match="predecessor mismatch"):
        store.commit(state.portfolio_id, state.digest, updated, cp)


def test_checkpoint_must_bind_portfolio_identity(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    bad = replace(checkpoint(updated), portfolio_id="other")
    with pytest.raises(PortfolioPersistenceError, match="checkpoint portfolio identity"):
        store.commit(state.portfolio_id, state.digest, updated, bad)


def test_checkpoint_must_bind_generation(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    bad = replace(checkpoint(updated), portfolio_generation=99)
    with pytest.raises(PortfolioPersistenceError, match="checkpoint generation"):
        store.commit(state.portfolio_id, state.digest, updated, bad)


def test_checkpoint_must_bind_resulting_state_digest(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    bad = replace(checkpoint(updated), portfolio_state_digest=D)
    with pytest.raises(PortfolioPersistenceError, match="checkpoint state digest"):
        store.commit(state.portfolio_id, state.digest, updated, bad)


def test_checkpoint_conflict_rolls_back_head_update(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    cp = checkpoint(updated)

    with sqlite3.connect(tmp_path / "portfolio.db") as connection:
        connection.execute(
            """
            INSERT INTO portfolio_checkpoints
                (portfolio_id, generation, checkpoint_id, checkpoint_digest, checkpoint_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                state.portfolio_id,
                1,
                "reserved-conflict",
                "sha256:" + "d" * 64,
                serialize_checkpoint(cp),
            ),
        )

    with pytest.raises(PortfolioPersistenceError, match="checkpoint already exists"):
        store.commit(state.portfolio_id, state.digest, updated, cp)
    loaded, head = store.load(state.portfolio_id)
    assert loaded == state
    assert head.generation == 0


def test_tampered_snapshot_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    with sqlite3.connect(tmp_path / "portfolio.db") as connection:
        raw = connection.execute(
            "SELECT snapshot_json FROM portfolio_heads WHERE portfolio_id = ?",
            (state.portfolio_id,),
        ).fetchone()[0]
        data = json.loads(raw)
        data["state"]["active"]["objective"] = "tampered"
        connection.execute(
            "UPDATE portfolio_heads SET snapshot_json = ? WHERE portfolio_id = ?",
            (json.dumps(data), state.portfolio_id),
        )
    with pytest.raises(PortfolioPersistenceError, match="snapshot digest mismatch"):
        store.load(state.portfolio_id)


def test_tampered_head_metadata_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    with sqlite3.connect(tmp_path / "portfolio.db") as connection:
        connection.execute(
            "UPDATE portfolio_heads SET state_digest = ? WHERE portfolio_id = ?",
            (D, state.portfolio_id),
        )
    with pytest.raises(PortfolioPersistenceError, match="metadata mismatch"):
        store.load(state.portfolio_id)


def test_tampered_checkpoint_digest_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(state)
    cp = checkpoint(updated)
    store.commit(state.portfolio_id, state.digest, updated, cp)
    with sqlite3.connect(tmp_path / "portfolio.db") as connection:
        connection.execute(
            "UPDATE portfolio_checkpoints SET checkpoint_digest = ? "
            "WHERE portfolio_id = ? AND generation = 1",
            (D, state.portfolio_id),
        )
    with pytest.raises(PortfolioPersistenceError, match="checkpoint digest mismatch"):
        store.load_checkpoint(state.portfolio_id, 1)


def test_missing_head_and_checkpoint_fail_closed(tmp_path):
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    with pytest.raises(PortfolioPersistenceError, match="head does not exist"):
        store.load("missing")
    with pytest.raises(PortfolioPersistenceError, match="checkpoint does not exist"):
        store.load_checkpoint("missing", 1)
