from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, sha256_digest
from .portfolio_state import (
    PortfolioState,
    portfolio_state_from_dict,
    portfolio_state_to_dict,
)

PORTFOLIO_SNAPSHOT_SCHEMA = "ge.portfolio-snapshot.v1"
PORTFOLIO_HEAD_SCHEMA = "ge.durable-portfolio-head.v1"


class PortfolioPersistenceError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioPersistenceError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise PortfolioPersistenceError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PortfolioPersistenceError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _require_exact_fields(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PortfolioPersistenceError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise PortfolioPersistenceError(
            f"{label} fields mismatch: missing={sorted(expected - actual)} "
            f"unknown={sorted(actual - expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class DurablePortfolioHead:
    portfolio_id: str
    generation: int
    state_digest: str
    snapshot_digest: str
    schema_version: str = PORTFOLIO_HEAD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PORTFOLIO_HEAD_SCHEMA:
            raise PortfolioPersistenceError("unsupported durable portfolio head schema")
        _nonempty("portfolio_id", self.portfolio_id)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool):
            raise PortfolioPersistenceError("generation must be an integer")
        if self.generation < 0:
            raise PortfolioPersistenceError("generation cannot be negative")
        _digest("state_digest", self.state_digest)
        _digest("snapshot_digest", self.snapshot_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def portfolio_snapshot(state: PortfolioState) -> dict[str, Any]:
    payload = {
        "schema_version": PORTFOLIO_SNAPSHOT_SCHEMA,
        "state": portfolio_state_to_dict(state),
        "state_digest": state.digest,
    }
    return {**payload, "snapshot_digest": sha256_digest(payload)}


def serialize_portfolio_snapshot(state: PortfolioState) -> str:
    return canonical_json(portfolio_snapshot(state))


def deserialize_portfolio_snapshot(payload: str) -> tuple[PortfolioState, str]:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PortfolioPersistenceError("portfolio snapshot is not valid JSON") from exc

    obj = _require_exact_fields(
        data,
        {"schema_version", "state", "state_digest", "snapshot_digest"},
        "portfolio snapshot",
    )
    if obj["schema_version"] != PORTFOLIO_SNAPSHOT_SCHEMA:
        raise PortfolioPersistenceError("unsupported portfolio snapshot schema")

    snapshot_digest = obj["snapshot_digest"]
    _digest("snapshot_digest", snapshot_digest)
    material = dict(obj)
    del material["snapshot_digest"]
    if sha256_digest(material) != snapshot_digest:
        raise PortfolioPersistenceError("portfolio snapshot digest mismatch")

    if not isinstance(obj["state"], dict):
        raise PortfolioPersistenceError("portfolio snapshot state must be an object")
    try:
        state = portfolio_state_from_dict(obj["state"])
    except ValueError as exc:
        raise PortfolioPersistenceError("invalid portfolio state in snapshot") from exc

    _digest("state_digest", obj["state_digest"])
    if state.digest != obj["state_digest"]:
        raise PortfolioPersistenceError("portfolio snapshot state digest mismatch")

    return state, snapshot_digest


def _head(state: PortfolioState, snapshot_digest: str) -> DurablePortfolioHead:
    return DurablePortfolioHead(
        portfolio_id=state.portfolio_id,
        generation=state.generation,
        state_digest=state.digest,
        snapshot_digest=snapshot_digest,
    )


def _decode_row(
    row: tuple[Any, ...],
    portfolio_id: str,
) -> tuple[PortfolioState, DurablePortfolioHead]:
    state_digest, generation, stored_snapshot_digest, snapshot_json = row
    state, snapshot_digest = deserialize_portfolio_snapshot(snapshot_json)
    if state.portfolio_id != portfolio_id:
        raise PortfolioPersistenceError("durable portfolio head identity mismatch")
    if (
        state.digest != state_digest
        or state.generation != generation
        or snapshot_digest != stored_snapshot_digest
    ):
        raise PortfolioPersistenceError("durable portfolio head metadata mismatch")
    return state, _head(state, snapshot_digest)


class SqlitePortfolioHeadStore:
    """Durable one-head-per-portfolio store with transactional compare-and-swap."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_heads (
                    portfolio_id TEXT PRIMARY KEY,
                    state_digest TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )

    def initialize(self, state: PortfolioState) -> DurablePortfolioHead:
        if state.generation != 0 or state.previous_state_digest is not None:
            raise PortfolioPersistenceError(
                "durable portfolio initialization requires generation zero"
            )

        snapshot_json = serialize_portfolio_snapshot(state)
        _, snapshot_digest = deserialize_portfolio_snapshot(snapshot_json)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT state_digest, generation, snapshot_digest, snapshot_json
                FROM portfolio_heads WHERE portfolio_id = ?
                """,
                (state.portfolio_id,),
            ).fetchone()

            if row is not None:
                existing_state, existing_head = _decode_row(row, state.portfolio_id)
                if existing_state != state:
                    raise PortfolioPersistenceError(
                        "durable portfolio head already exists with different state"
                    )
                connection.commit()
                return existing_head

            connection.execute(
                """
                INSERT INTO portfolio_heads
                    (portfolio_id, state_digest, generation, snapshot_digest, snapshot_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state.portfolio_id,
                    state.digest,
                    state.generation,
                    snapshot_digest,
                    snapshot_json,
                ),
            )
            connection.commit()
            return _head(state, snapshot_digest)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, portfolio_id: str) -> tuple[PortfolioState, DurablePortfolioHead]:
        _nonempty("portfolio_id", portfolio_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT state_digest, generation, snapshot_digest, snapshot_json
                FROM portfolio_heads WHERE portfolio_id = ?
                """,
                (portfolio_id,),
            ).fetchone()
        if row is None:
            raise PortfolioPersistenceError("durable portfolio head does not exist")
        return _decode_row(row, portfolio_id)

    def commit(
        self,
        portfolio_id: str,
        expected_state_digest: str,
        new_state: PortfolioState,
    ) -> DurablePortfolioHead:
        _nonempty("portfolio_id", portfolio_id)
        _digest("expected_state_digest", expected_state_digest)
        if new_state.portfolio_id != portfolio_id:
            raise PortfolioPersistenceError("portfolio commit identity mismatch")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT state_digest, generation, snapshot_digest, snapshot_json
                FROM portfolio_heads WHERE portfolio_id = ?
                """,
                (portfolio_id,),
            ).fetchone()
            if row is None:
                raise PortfolioPersistenceError("durable portfolio head does not exist")

            current_state, _ = _decode_row(row, portfolio_id)
            if current_state.digest != expected_state_digest:
                raise PortfolioPersistenceError("stale durable portfolio head")
            if new_state.generation != current_state.generation + 1:
                raise PortfolioPersistenceError(
                    "durable portfolio commit must advance exactly one generation"
                )
            if new_state.previous_state_digest != current_state.digest:
                raise PortfolioPersistenceError(
                    "durable portfolio commit predecessor mismatch"
                )

            snapshot_json = serialize_portfolio_snapshot(new_state)
            _, snapshot_digest = deserialize_portfolio_snapshot(snapshot_json)
            cursor = connection.execute(
                """
                UPDATE portfolio_heads
                SET state_digest = ?, generation = ?, snapshot_digest = ?, snapshot_json = ?
                WHERE portfolio_id = ? AND state_digest = ? AND generation = ?
                """,
                (
                    new_state.digest,
                    new_state.generation,
                    snapshot_digest,
                    snapshot_json,
                    portfolio_id,
                    expected_state_digest,
                    current_state.generation,
                ),
            )
            if cursor.rowcount != 1:
                raise PortfolioPersistenceError(
                    "durable portfolio compare-and-swap failed"
                )
            connection.commit()
            return _head(new_state, snapshot_digest)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
