from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .canonical import sha256_digest
from .durable import (
    DurableCapacitySnapshot,
    DurableStateError,
    load_durable_snapshot,
    serialize_durable_snapshot,
    verify_durable_snapshot,
    verify_durable_successor,
)
from .models import RunnerCapabilities

STORE_SCHEMA_VERSION = "ge.sqlite-durable-head-store.v1"


class PersistenceError(ValueError):
    pass


class PersistenceConflict(PersistenceError):
    pass


class PersistenceIntegrityError(PersistenceError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class PersistenceCommitReceipt:
    runner_id: str
    previous_head_digest: str | None
    committed_head_digest: str
    generation: int
    snapshot_digest: str
    idempotent: bool
    schema_version: str = "ge.persistence-commit-receipt.v1"

    def __post_init__(self) -> None:
        if not self.runner_id or not self.runner_id.strip():
            raise ValueError("runner_id must be non-empty")
        if self.generation < 0:
            raise ValueError("generation must be >= 0")
        if self.schema_version != "ge.persistence-commit-receipt.v1":
            raise ValueError("unsupported persistence commit receipt schema")
        _require_sha256("committed_head_digest", self.committed_head_digest)
        _require_sha256("snapshot_digest", self.snapshot_digest)
        if self.previous_head_digest is not None:
            _require_sha256("previous_head_digest", self.previous_head_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteDurableHeadStore:
    """Concrete durable-head adapter using SQLite transactions and compare-and-swap."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.path == ":memory:":
            raise ValueError("durable SQLite store requires a filesystem-backed database")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            isolation_level=None,
            timeout=self.timeout_seconds,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_store_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_durable_heads (
                    runner_id TEXT PRIMARY KEY,
                    head_digest TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    snapshot_payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO ge_store_metadata(key, value) "
                "VALUES('schema_version', ?)",
                (STORE_SCHEMA_VERSION,),
            )
            self._verify_store_schema(connection)

    def _verify_store_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_store_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != STORE_SCHEMA_VERSION:
            raise PersistenceIntegrityError("SQLite durable-head store schema mismatch")

    @staticmethod
    def _decode_row(row: sqlite3.Row, runner: RunnerCapabilities) -> DurableCapacitySnapshot:
        try:
            snapshot = load_durable_snapshot(
                row["snapshot_payload"],
                runner,
                expected_head_digest=row["head_digest"],
            )
        except DurableStateError as exc:
            raise PersistenceIntegrityError("stored durable snapshot failed verification") from exc
        if (
            snapshot.head.generation != row["generation"]
            or snapshot.digest != row["snapshot_digest"]
        ):
            raise PersistenceIntegrityError("stored durable-head metadata does not match snapshot")
        return snapshot

    def load_current(self, runner: RunnerCapabilities) -> DurableCapacitySnapshot | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            if row is None:
                return None
            return self._decode_row(row, runner)

    def compare_and_swap(
        self,
        snapshot: DurableCapacitySnapshot,
        runner: RunnerCapabilities,
        *,
        expected_head_digest: str | None,
    ) -> PersistenceCommitReceipt:
        if expected_head_digest is not None:
            _require_sha256("expected_head_digest", expected_head_digest)
        if not verify_durable_snapshot(snapshot, runner):
            raise PersistenceIntegrityError("candidate durable snapshot failed verification")

        payload = serialize_durable_snapshot(snapshot)
        snapshot_digest = snapshot.digest
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()

            if row is None:
                if expected_head_digest is not None:
                    raise PersistenceConflict("durable head is absent but a previous head was expected")
                if snapshot.head.previous_head_digest is not None:
                    raise PersistenceConflict("first stored snapshot cannot depend on an unstored predecessor")
                connection.execute(
                    "INSERT INTO ge_durable_heads "
                    "(runner_id, head_digest, generation, snapshot_digest, snapshot_payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        runner.runner_id,
                        snapshot.head.digest,
                        snapshot.head.generation,
                        snapshot_digest,
                        payload,
                    ),
                )
                previous_head_digest = None
                idempotent = False
            else:
                current = self._decode_row(row, runner)
                current_head_digest = current.head.digest
                if expected_head_digest != current_head_digest:
                    raise PersistenceConflict("expected durable head does not match canonical head")

                if snapshot.head.digest == current_head_digest:
                    if (
                        snapshot != current
                        or snapshot_digest != row["snapshot_digest"]
                        or payload != row["snapshot_payload"]
                    ):
                        raise PersistenceIntegrityError("same head digest maps to different stored snapshot")
                    previous_head_digest = current_head_digest
                    idempotent = True
                else:
                    if not verify_durable_successor(current, snapshot, runner):
                        raise PersistenceConflict("candidate snapshot is not a valid successor of canonical head")
                    cursor = connection.execute(
                        "UPDATE ge_durable_heads SET head_digest = ?, generation = ?, "
                        "snapshot_digest = ?, snapshot_payload = ? "
                        "WHERE runner_id = ? AND head_digest = ?",
                        (
                            snapshot.head.digest,
                            snapshot.head.generation,
                            snapshot_digest,
                            payload,
                            runner.runner_id,
                            current_head_digest,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise PersistenceConflict("canonical durable head changed before commit")
                    previous_head_digest = current_head_digest
                    idempotent = False

            committed_row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            if committed_row is None:
                raise PersistenceIntegrityError("durable head disappeared before commit")
            committed = self._decode_row(committed_row, runner)
            if committed != snapshot:
                raise PersistenceIntegrityError("transaction does not contain the exact candidate snapshot")
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

        return PersistenceCommitReceipt(
            runner_id=runner.runner_id,
            previous_head_digest=previous_head_digest,
            committed_head_digest=snapshot.head.digest,
            generation=snapshot.head.generation,
            snapshot_digest=snapshot.digest,
            idempotent=idempotent,
        )
