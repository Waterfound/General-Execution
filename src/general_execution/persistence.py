from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .canonical import canonical_json, sha256_digest
from .durable import (
    DurableCapacitySnapshot,
    DurableStateError,
    load_durable_snapshot,
    serialize_durable_snapshot,
    verify_durable_snapshot,
    verify_durable_successor,
)
from .models import RunnerCapabilities
from .reconciliation import (
    ReconciliationCandidate,
    ReconciliationRecord,
    reconciliation_record_from_dict,
    reconciliation_record_to_dict,
    verify_reconciliation_candidate,
)

STORE_SCHEMA_VERSION = "ge.sqlite-durable-head-store.v2"
PREVIOUS_STORE_SCHEMA_VERSION = "ge.sqlite-durable-head-store.v1"


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


@dataclass(frozen=True, slots=True)
class ReconciliationPersistenceReceipt:
    runner_id: str
    authorization_id: str
    reconciliation_id: str
    reconciliation_digest: str
    previous_head_digest: str
    committed_head_digest: str
    generation: int
    idempotent: bool
    schema_version: str = "ge.reconciliation-persistence-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reconciliation-persistence-receipt.v1":
            raise ValueError("unsupported reconciliation persistence receipt schema")
        if not self.runner_id or not self.runner_id.strip():
            raise ValueError("runner_id must be non-empty")
        if not self.authorization_id or not self.authorization_id.strip():
            raise ValueError("authorization_id must be non-empty")
        if not self.reconciliation_id or not self.reconciliation_id.strip():
            raise ValueError("reconciliation_id must be non-empty")
        if self.generation < 1:
            raise ValueError("generation must be >= 1")
        for name in ("reconciliation_digest", "previous_head_digest", "committed_head_digest"):
            _require_sha256(name, getattr(self, name))

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
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ge_store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
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
                """
                CREATE TABLE IF NOT EXISTS ge_reconciliations (
                    runner_id TEXT NOT NULL,
                    authorization_id TEXT NOT NULL,
                    reconciliation_id TEXT NOT NULL UNIQUE,
                    reconciliation_digest TEXT NOT NULL,
                    previous_head_digest TEXT NOT NULL,
                    committed_head_digest TEXT NOT NULL,
                    record_payload TEXT NOT NULL,
                    PRIMARY KEY (runner_id, authorization_id)
                )
                """
            )
            row = connection.execute(
                "SELECT value FROM ge_store_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO ge_store_metadata(key, value) VALUES('schema_version', ?)",
                    (STORE_SCHEMA_VERSION,),
                )
            elif row["value"] == PREVIOUS_STORE_SCHEMA_VERSION:
                connection.execute(
                    "UPDATE ge_store_metadata SET value = ? WHERE key = 'schema_version'",
                    (STORE_SCHEMA_VERSION,),
                )
            elif row["value"] != STORE_SCHEMA_VERSION:
                raise PersistenceIntegrityError("unsupported SQLite durable-head store schema")
            self._verify_store_schema(connection)
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

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
        if snapshot.head.generation != row["generation"] or snapshot.digest != row["snapshot_digest"]:
            raise PersistenceIntegrityError("stored durable-head metadata does not match snapshot")
        return snapshot

    @staticmethod
    def _decode_reconciliation_row(row: sqlite3.Row) -> ReconciliationRecord:
        import json

        try:
            data = json.loads(row["record_payload"])
            record = reconciliation_record_from_dict(data)
        except (ValueError, TypeError) as exc:
            raise PersistenceIntegrityError("stored reconciliation record is invalid") from exc
        if (
            record.runner_id != row["runner_id"]
            or record.authorization_id != row["authorization_id"]
            or record.reconciliation_id != row["reconciliation_id"]
            or record.digest != row["reconciliation_digest"]
            or record.source_head_digest != row["previous_head_digest"]
            or record.successor_head_digest != row["committed_head_digest"]
        ):
            raise PersistenceIntegrityError("stored reconciliation metadata does not match record")
        return record

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

    def load_reconciliation(self, runner: RunnerCapabilities, authorization_id: str) -> ReconciliationRecord | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, "
                "previous_head_digest, committed_head_digest, record_payload "
                "FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, authorization_id),
            ).fetchone()
            if row is None:
                return None
            return self._decode_reconciliation_row(row)

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
                    (runner.runner_id, snapshot.head.digest, snapshot.head.generation, snapshot_digest, payload),
                )
                previous_head_digest = None
                idempotent = False
            else:
                current = self._decode_row(row, runner)
                current_head_digest = current.head.digest
                if expected_head_digest != current_head_digest:
                    raise PersistenceConflict("expected durable head does not match canonical head")

                if snapshot.head.digest == current_head_digest:
                    if snapshot != current or snapshot_digest != row["snapshot_digest"] or payload != row["snapshot_payload"]:
                        raise PersistenceIntegrityError("same head digest maps to different stored snapshot")
                    previous_head_digest = current_head_digest
                    idempotent = True
                else:
                    if not verify_durable_successor(current, snapshot, runner):
                        raise PersistenceConflict("candidate snapshot is not a valid successor of canonical head")
                    cursor = connection.execute(
                        "UPDATE ge_durable_heads SET head_digest = ?, generation = ?, snapshot_digest = ?, "
                        "snapshot_payload = ? WHERE runner_id = ? AND head_digest = ?",
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

    def commit_reconciliation(
        self,
        candidate: ReconciliationCandidate,
        runner: RunnerCapabilities,
    ) -> ReconciliationPersistenceReceipt:
        if not verify_reconciliation_candidate(candidate, runner):
            raise PersistenceIntegrityError("reconciliation candidate failed intrinsic verification")

        record = candidate.record
        record_payload = canonical_json(reconciliation_record_to_dict(record))
        successor = candidate.successor_snapshot
        successor_payload = serialize_durable_snapshot(successor)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)

            existing_row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, "
                "previous_head_digest, committed_head_digest, record_payload "
                "FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, record.authorization_id),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode_reconciliation_row(existing_row)
                if existing != record or existing_row["record_payload"] != record_payload:
                    raise PersistenceConflict("authorization already has a different canonical reconciliation")
                connection.commit()
                return ReconciliationPersistenceReceipt(
                    runner_id=runner.runner_id,
                    authorization_id=record.authorization_id,
                    reconciliation_id=record.reconciliation_id,
                    reconciliation_digest=record.digest,
                    previous_head_digest=record.source_head_digest,
                    committed_head_digest=record.successor_head_digest,
                    generation=successor.head.generation,
                    idempotent=True,
                )

            current_row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            if current_row is None:
                raise PersistenceConflict("reconciliation requires an existing canonical durable head")
            current = self._decode_row(current_row, runner)
            if current != candidate.source_snapshot:
                raise PersistenceConflict("reconciliation source is not the canonical durable head")
            if not verify_durable_successor(current, successor, runner):
                raise PersistenceIntegrityError("reconciliation successor is not a valid durable successor")

            cursor = connection.execute(
                "UPDATE ge_durable_heads SET head_digest = ?, generation = ?, snapshot_digest = ?, "
                "snapshot_payload = ? WHERE runner_id = ? AND head_digest = ?",
                (
                    successor.head.digest,
                    successor.head.generation,
                    successor.digest,
                    successor_payload,
                    runner.runner_id,
                    current.head.digest,
                ),
            )
            if cursor.rowcount != 1:
                raise PersistenceConflict("canonical durable head changed before reconciliation commit")

            connection.execute(
                "INSERT INTO ge_reconciliations "
                "(runner_id, authorization_id, reconciliation_id, reconciliation_digest, "
                "previous_head_digest, committed_head_digest, record_payload) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    runner.runner_id,
                    record.authorization_id,
                    record.reconciliation_id,
                    record.digest,
                    record.source_head_digest,
                    record.successor_head_digest,
                    record_payload,
                ),
            )

            committed_head_row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            committed_record_row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, "
                "previous_head_digest, committed_head_digest, record_payload "
                "FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, record.authorization_id),
            ).fetchone()
            if committed_head_row is None or committed_record_row is None:
                raise PersistenceIntegrityError("reconciliation transaction is incomplete")
            if self._decode_row(committed_head_row, runner) != successor:
                raise PersistenceIntegrityError("reconciliation transaction head does not match successor")
            if self._decode_reconciliation_row(committed_record_row) != record:
                raise PersistenceIntegrityError("reconciliation transaction record does not match candidate")
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise PersistenceConflict("reconciliation uniqueness constraint rejected the commit") from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

        return ReconciliationPersistenceReceipt(
            runner_id=runner.runner_id,
            authorization_id=record.authorization_id,
            reconciliation_id=record.reconciliation_id,
            reconciliation_digest=record.digest,
            previous_head_digest=record.source_head_digest,
            committed_head_digest=record.successor_head_digest,
            generation=successor.head.generation,
            idempotent=False,
        )
