import json
import sqlite3
from dataclasses import replace

import pytest

from general_execution import (
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioPersistenceError,
    PortfolioState,
    SqlitePortfolioHeadStore,
    WakeCondition,
    deserialize_portfolio_snapshot,
    portfolio_snapshot,
    serialize_portfolio_snapshot,
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


def secondary(**changes):
    values = dict(
        work_id="SECONDARY",
        role="secondary",
        state="ready",
        objective="Prepare secondary work",
        active_gate="SECONDARY_GATE",
        next_action_ref="action://secondary",
        source_revision="src-b",
    )
    values.update(changes)
    return PortfolioEntry(**values)


def passive(**changes):
    values = dict(
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
    values.update(changes)
    return PortfolioEntry(**values)


def genesis(**changes):
    values = dict(
        portfolio_id="portfolio-1",
        generation=0,
        active=active(),
        secondary=secondary(),
        passive=(passive(),),
    )
    values.update(changes)
    return PortfolioState(**values)


def next_state(current, **changes):
    values = dict(
        portfolio_id=current.portfolio_id,
        generation=current.generation + 1,
        active=current.active,
        secondary=current.secondary,
        passive=current.passive,
        previous_state_digest=current.digest,
    )
    values.update(changes)
    return PortfolioState(**values)


def test_snapshot_round_trip_is_exact():
    state = genesis()
    encoded = serialize_portfolio_snapshot(state)
    decoded, snapshot_digest = deserialize_portfolio_snapshot(encoded)
    assert decoded == state
    assert snapshot_digest == portfolio_snapshot(state)["snapshot_digest"]


def test_initialize_and_reload_survive_restart(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    head = store.initialize(state)

    restarted = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    loaded, loaded_head = restarted.load(state.portfolio_id)
    assert loaded == state
    assert loaded_head == head


def test_initialize_is_idempotent_only_for_identical_state(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    first = store.initialize(state)
    second = store.initialize(state)
    assert first == second

    changed = genesis(active=active(objective="different"))
    with pytest.raises(
        PortfolioPersistenceError,
        match="already exists with different state",
    ):
        store.initialize(changed)


def test_initialize_rejects_nonzero_generation(tmp_path):
    state = genesis()
    nonzero = next_state(state)
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    with pytest.raises(
        PortfolioPersistenceError,
        match="requires generation zero",
    ):
        store.initialize(nonzero)


def test_commit_advances_exactly_one_generation(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = next_state(
        state,
        active=replace(state.active, state="verifying"),
    )
    head = store.commit(state.portfolio_id, state.digest, updated)
    loaded, loaded_head = store.load(state.portfolio_id)
    assert loaded == updated
    assert head == loaded_head
    assert head.generation == 1


def test_stale_compare_and_swap_is_rejected(tmp_path):
    state = genesis()
    store_a = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store_a.initialize(state)
    store_b = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")

    one = next_state(state, active=replace(state.active, state="verifying"))
    two = next_state(state, active=replace(state.active, state="waiting_external", blockers=(PortfolioBlocker(kind="external_dependency", detail="blocked"),), wake_condition=WakeCondition(kind="event_received", value="provider.available")))
    store_a.commit(state.portfolio_id, state.digest, one)

    with pytest.raises(
        PortfolioPersistenceError,
        match="stale durable portfolio head",
    ):
        store_b.commit(state.portfolio_id, state.digest, two)


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
    with pytest.raises(
        PortfolioPersistenceError,
        match="advance exactly one generation",
    ):
        store.commit(state.portfolio_id, state.digest, skipped)


def test_wrong_predecessor_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    updated = PortfolioState(
        portfolio_id=state.portfolio_id,
        generation=1,
        active=state.active,
        secondary=state.secondary,
        passive=state.passive,
        previous_state_digest=D,
    )
    with pytest.raises(
        PortfolioPersistenceError,
        match="predecessor mismatch",
    ):
        store.commit(state.portfolio_id, state.digest, updated)


def test_commit_identity_mismatch_is_rejected(tmp_path):
    state = genesis()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    other = PortfolioState(
        portfolio_id="portfolio-other",
        generation=1,
        active=state.active,
        secondary=state.secondary,
        passive=state.passive,
        previous_state_digest=state.digest,
    )
    with pytest.raises(
        PortfolioPersistenceError,
        match="identity mismatch",
    ):
        store.commit(state.portfolio_id, state.digest, other)


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

    with pytest.raises(
        PortfolioPersistenceError,
        match="snapshot digest mismatch",
    ):
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

    with pytest.raises(
        PortfolioPersistenceError,
        match="metadata mismatch",
    ):
        store.load(state.portfolio_id)


def test_missing_head_fails_closed(tmp_path):
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    with pytest.raises(
        PortfolioPersistenceError,
        match="does not exist",
    ):
        store.load("missing")
