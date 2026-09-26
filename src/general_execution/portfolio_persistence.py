from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, sha256_digest
from .execution_checkpoint import (
    ExecutionCheckpoint,
    deserialize_checkpoint,
    serialize_checkpoint,
)
from .portfolio_state import (
    PortfolioState,
    portfolio_state_from_dict,
    portfolio_state_to_dict,
)

PORTFOLIO_SNAPSHOT_SCHEMA = "ge.portfolio-snapshot.v1"
PORTFOLIO_HEAD_SCHEMA = "ge.durable-portfolio-head.v1"
PORTFOLIO_RECOVERY_SCHEMA = "ge.portfolio-recovery.v1"


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
    latest_checkpoint_digest: str | None = None
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
        if self.latest_checkpoint_digest is not None:
            _digest("latest_checkpoint_digest", self.latest_checkpoint_digest)
        if self.generation == 0 and self.latest_checkpoint_digest is not None:
            raise PortfolioPersistenceError(
                "generation zero cannot have latest checkpoint"
            )
        if self.generation > 0 and self.latest_checkpoint_digest is None:
            raise PortfolioPersistenceError(
                "nonzero durable portfolio head requires checkpoint"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PortfolioRecoveryReport:
    portfolio_id: str
    generation: int
    state_digest: str
    snapshot_digest: str
    latest_checkpoint_digest: str | None
    checkpoint_present: bool
    fabricated_state: bool = False
    fabricated_checkpoint: bool = False
    schema_version: str = PORTFOLIO_RECOVERY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PORTFOLIO_RECOVERY_SCHEMA:
            raise PortfolioPersistenceError("unsupported portfolio recovery schema")
        _nonempty("portfolio_id", self.portfolio_id)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool):
            raise PortfolioPersistenceError("generation must be an integer")
        if self.generation < 0:
            raise PortfolioPersistenceError("generation cannot be negative")
        _digest("state_digest", self.state_digest)
        _digest("snapshot_digest", self.snapshot_digest)
        if self.latest_checkpoint_digest is not None:
            _digest("latest_checkpoint_digest", self.latest_checkpoint_digest)
        if self.fabricated_state or self.fabricated_checkpoint:
            raise PortfolioPersistenceError(
                "portfolio recovery cannot fabricate state or checkpoint"
            )
        if self.generation == 0 and self.checkpoint_present:
            raise PortfolioPersistenceError(
                "generation zero cannot report a checkpoint"
            )
        if self.generation > 0 and not self.checkpoint_present:
            raise PortfolioPersistenceError(
                "nonzero generation requires a checkpoint"
            )

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


def _head(
    state: PortfolioState,
    snapshot_digest: str,
    latest_checkpoint_digest: str | None,
) -> DurablePortfolioHead:
    return DurablePortfolioHead(
        portfolio_id=state.portfolio_id,
        generation=state.generation,
        state_digest=state.digest,
        snapshot_digest=snapshot_digest,
        latest_checkpoint_digest=latest_checkpoint_digest,
    )


def _decode_row(
    row: tuple[Any, ...],
    portfolio_id: str,
) -> tuple[PortfolioState, DurablePortfolioHead]:
    (
        state_digest,
        generation,
        stored_snapshot_digest,
        snapshot_json,
        latest_checkpoint_digest,
    ) = row
    state, snapshot_digest = deserialize_portfolio_snapshot(snapshot_json)
    if state.portfolio_id != portfolio_id:
        raise PortfolioPersistenceError("durable portfolio head identity mismatch")
    if (
        state.digest != state_digest
        or state.generation != generation
        or snapshot_digest != stored_snapshot_digest
    ):
        raise PortfolioPersistenceError("durable portfolio head metadata mismatch")
    return state, _head(state, snapshot_digest, latest_checkpoint_digest)


class SqlitePortfolioHeadStore:
    """Durable portfolio head plus atomic checkpoint history using CAS commits."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
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
                    snapshot_json TEXT NOT NULL,
                    latest_checkpoint_digest TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(portfolio_heads)"
                ).fetchall()
            }
            if "latest_checkpoint_digest" not in columns:
                connection.execute(
                    "ALTER TABLE portfolio_heads "
                    "ADD COLUMN latest_checkpoint_digest TEXT"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_checkpoints (
                    portfolio_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    checkpoint_id TEXT NOT NULL UNIQUE,
                    checkpoint_digest TEXT NOT NULL UNIQUE,
                    checkpoint_json TEXT NOT NULL,
                    PRIMARY KEY (portfolio_id, generation),
                    FOREIGN KEY (portfolio_id)
                        REFERENCES portfolio_heads(portfolio_id)
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
                SELECT state_digest, generation, snapshot_digest, snapshot_json,
                       latest_checkpoint_digest
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
                    (portfolio_id, state_digest, generation, snapshot_digest,
                     snapshot_json, latest_checkpoint_digest)
                VALUES (?, ?, ?, ?, ?, NULL)
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
            return _head(state, snapshot_digest, None)
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
                SELECT state_digest, generation, snapshot_digest, snapshot_json,
                       latest_checkpoint_digest
                FROM portfolio_heads WHERE portfolio_id = ?
                """,
                (portfolio_id,),
            ).fetchone()
        if row is None:
            raise PortfolioPersistenceError("durable portfolio head does not exist")
        return _decode_row(row, portfolio_id)

    def load_checkpoint(
        self,
        portfolio_id: str,
        generation: int,
    ) -> ExecutionCheckpoint:
        _nonempty("portfolio_id", portfolio_id)
        if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
            raise PortfolioPersistenceError(
                "checkpoint generation must be an integer >= 1"
            )
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT checkpoint_id, checkpoint_digest, checkpoint_json
                FROM portfolio_checkpoints
                WHERE portfolio_id = ? AND generation = ?
                """,
                (portfolio_id, generation),
            ).fetchone()
        if row is None:
            raise PortfolioPersistenceError(
                "durable portfolio checkpoint does not exist"
            )
        checkpoint_id, checkpoint_digest, checkpoint_json = row
        try:
            checkpoint = deserialize_checkpoint(checkpoint_json)
        except ValueError as exc:
            raise PortfolioPersistenceError(
                "invalid durable portfolio checkpoint"
            ) from exc
        if checkpoint.checkpoint_id != checkpoint_id:
            raise PortfolioPersistenceError("durable checkpoint id mismatch")
        if checkpoint.digest != checkpoint_digest:
            raise PortfolioPersistenceError("durable checkpoint digest mismatch")
        if (
            checkpoint.portfolio_id != portfolio_id
            or checkpoint.portfolio_generation != generation
        ):
            raise PortfolioPersistenceError("durable checkpoint metadata mismatch")
        return checkpoint

    def latest_checkpoint(self, portfolio_id: str) -> ExecutionCheckpoint | None:
        state, head = self.load(portfolio_id)
        if state.generation == 0:
            return None
        checkpoint = self.load_checkpoint(portfolio_id, state.generation)
        if checkpoint.digest != head.latest_checkpoint_digest:
            raise PortfolioPersistenceError("latest checkpoint digest mismatch")
        return checkpoint

    def commit(
        self,
        portfolio_id: str,
        expected_state_digest: str,
        new_state: PortfolioState,
        checkpoint: ExecutionCheckpoint,
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
                SELECT state_digest, generation, snapshot_digest, snapshot_json,
                       latest_checkpoint_digest
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
            if checkpoint.portfolio_id != portfolio_id:
                raise PortfolioPersistenceError(
                    "checkpoint portfolio identity does not bind new state"
                )
            if checkpoint.portfolio_generation != new_state.generation:
                raise PortfolioPersistenceError(
                    "checkpoint generation does not bind new state"
                )
            if checkpoint.portfolio_state_digest != new_state.digest:
                raise PortfolioPersistenceError(
                    "checkpoint state digest does not bind new state"
                )

            snapshot_json = serialize_portfolio_snapshot(new_state)
            _, snapshot_digest = deserialize_portfolio_snapshot(snapshot_json)
            checkpoint_json = serialize_checkpoint(checkpoint)
            try:
                decoded_checkpoint = deserialize_checkpoint(checkpoint_json)
            except ValueError as exc:
                raise PortfolioPersistenceError(
                    "checkpoint does not round-trip canonically"
                ) from exc
            if decoded_checkpoint != checkpoint:
                raise PortfolioPersistenceError(
                    "checkpoint does not round-trip canonically"
                )

            try:
                connection.execute(
                    """
                    INSERT INTO portfolio_checkpoints
                        (portfolio_id, generation, checkpoint_id,
                         checkpoint_digest, checkpoint_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        portfolio_id,
                        new_state.generation,
                        checkpoint.checkpoint_id,
                        checkpoint.digest,
                        checkpoint_json,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise PortfolioPersistenceError(
                    "durable portfolio checkpoint already exists"
                ) from exc

            cursor = connection.execute(
                """
                UPDATE portfolio_heads
                SET state_digest = ?, generation = ?, snapshot_digest = ?,
                    snapshot_json = ?, latest_checkpoint_digest = ?
                WHERE portfolio_id = ? AND state_digest = ? AND generation = ?
                """,
                (
                    new_state.digest,
                    new_state.generation,
                    snapshot_digest,
                    snapshot_json,
                    checkpoint.digest,
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
            return _head(new_state, snapshot_digest, checkpoint.digest)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def verify_portfolio_recovery(
    state: PortfolioState,
    head: DurablePortfolioHead,
    checkpoint: ExecutionCheckpoint | None,
    report: PortfolioRecoveryReport,
) -> bool:
    if (
        state.portfolio_id != head.portfolio_id
        or state.digest != head.state_digest
        or state.generation != head.generation
    ):
        return False
    if (
        report.portfolio_id != state.portfolio_id
        or report.generation != state.generation
        or report.state_digest != state.digest
        or report.snapshot_digest != head.snapshot_digest
        or report.latest_checkpoint_digest != head.latest_checkpoint_digest
    ):
        return False
    if state.generation == 0:
        return checkpoint is None and not report.checkpoint_present
    if checkpoint is None:
        return False
    return (
        report.checkpoint_present
        and checkpoint.portfolio_id == state.portfolio_id
        and checkpoint.portfolio_generation == state.generation
        and checkpoint.portfolio_state_digest == state.digest
        and checkpoint.digest == head.latest_checkpoint_digest
    )


def recover_portfolio_after_restart(
    store: SqlitePortfolioHeadStore,
    portfolio_id: str,
) -> tuple[PortfolioState, ExecutionCheckpoint | None, PortfolioRecoveryReport]:
    state, head = store.load(portfolio_id)
    checkpoint = store.latest_checkpoint(portfolio_id)
    report = PortfolioRecoveryReport(
        portfolio_id=state.portfolio_id,
        generation=state.generation,
        state_digest=state.digest,
        snapshot_digest=head.snapshot_digest,
        latest_checkpoint_digest=head.latest_checkpoint_digest,
        checkpoint_present=checkpoint is not None,
    )
    if not verify_portfolio_recovery(state, head, checkpoint, report):
        raise PortfolioPersistenceError(
            "portfolio restart recovery does not reproduce"
        )
    return state, checkpoint, report
