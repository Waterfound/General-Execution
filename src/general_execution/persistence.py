from __future__ import annotations

import json
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
from .models import ExecutionSession, RunnerCapabilities
from .reconciliation import (
    ReconciliationCandidate,
    ReconciliationRecord,
    reconciliation_record_from_dict,
    reconciliation_record_to_dict,
    verify_reconciliation_candidate,
)
from .result_handoff import (
    LogicalResultSubmission,
    PendingLogicalResult,
    logical_result_submission_from_dict,
    logical_result_submission_to_dict,
    pending_logical_result_from_dict,
    pending_logical_result_from_reconciliation,
    pending_logical_result_to_dict,
    verify_logical_result_submission,
    verify_pending_logical_result,
)

STORE_SCHEMA_VERSION = "ge.sqlite-durable-head-store.v3"
PREVIOUS_STORE_SCHEMA_VERSIONS = frozenset({
    "ge.sqlite-durable-head-store.v1",
    "ge.sqlite-durable-head-store.v2",
})


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


@dataclass(frozen=True, slots=True)
class LogicalResultPersistenceReceipt:
    runner_id: str
    session_id: str
    logical_attempt: int
    pending_id: str
    submission_id: str
    submission_digest: str
    result_digest: str
    submitted_session_digest: str
    idempotent: bool
    schema_version: str = "ge.logical-result-persistence-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.logical-result-persistence-receipt.v1":
            raise ValueError("unsupported logical result persistence receipt schema")
        for name in ("runner_id", "session_id", "pending_id", "submission_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.logical_attempt < 1:
            raise ValueError("logical_attempt must be >= 1")
        for name in ("submission_digest", "result_digest", "submitted_session_digest"):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteDurableHeadStore:
    """Concrete SQLite adapter for durable heads, reconciliations, and result handoff."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.path == ":memory:":
            raise ValueError("durable SQLite store requires a filesystem-backed database")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=self.timeout_seconds)
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_pending_results (
                    runner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    logical_attempt INTEGER NOT NULL,
                    pending_id TEXT NOT NULL UNIQUE,
                    pending_digest TEXT NOT NULL,
                    reconciliation_id TEXT NOT NULL UNIQUE,
                    result_digest TEXT NOT NULL,
                    pending_payload TEXT NOT NULL,
                    PRIMARY KEY (runner_id, session_id, logical_attempt)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_result_submissions (
                    runner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    logical_attempt INTEGER NOT NULL,
                    pending_id TEXT NOT NULL UNIQUE,
                    submission_id TEXT NOT NULL UNIQUE,
                    submission_digest TEXT NOT NULL,
                    result_digest TEXT NOT NULL,
                    submitted_session_digest TEXT NOT NULL,
                    submission_payload TEXT NOT NULL,
                    PRIMARY KEY (runner_id, session_id, logical_attempt)
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
            elif row["value"] in PREVIOUS_STORE_SCHEMA_VERSIONS:
                if row["value"] == "ge.sqlite-durable-head-store.v2":
                    self._verify_v2_migration_safety(connection)
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

    def _verify_v2_migration_safety(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("SELECT record_payload FROM ge_reconciliations").fetchall()
        for row in rows:
            try:
                record = reconciliation_record_from_dict(json.loads(row["record_payload"]))
            except (ValueError, TypeError) as exc:
                raise PersistenceIntegrityError("v2 reconciliation record is not decodable") from exc
            if record.result_digest is not None:
                raise PersistenceIntegrityError(
                    "cannot migrate v2 completed reconciliation without its original ResultEnvelope"
                )

    def _verify_store_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_store_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != STORE_SCHEMA_VERSION:
            raise PersistenceIntegrityError("SQLite durable-head store schema mismatch")

    @staticmethod
    def _decode_row(row: sqlite3.Row, runner: RunnerCapabilities) -> DurableCapacitySnapshot:
        try:
            snapshot = load_durable_snapshot(row["snapshot_payload"], runner, expected_head_digest=row["head_digest"])
        except DurableStateError as exc:
            raise PersistenceIntegrityError("stored durable snapshot failed verification") from exc
        if snapshot.head.generation != row["generation"] or snapshot.digest != row["snapshot_digest"]:
            raise PersistenceIntegrityError("stored durable-head metadata does not match snapshot")
        return snapshot

    @staticmethod
    def _decode_reconciliation_row(row: sqlite3.Row) -> ReconciliationRecord:
        try:
            record = reconciliation_record_from_dict(json.loads(row["record_payload"]))
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

    @staticmethod
    def _decode_pending_row(row: sqlite3.Row, runner: RunnerCapabilities) -> PendingLogicalResult:
        try:
            pending = pending_logical_result_from_dict(json.loads(row["pending_payload"]))
        except (ValueError, TypeError) as exc:
            raise PersistenceIntegrityError("stored pending logical result is invalid") from exc
        if not verify_pending_logical_result(pending, runner):
            raise PersistenceIntegrityError("stored pending logical result failed runner verification")
        if (
            pending.runner_id != row["runner_id"]
            or pending.session_id != row["session_id"]
            or pending.logical_attempt != row["logical_attempt"]
            or pending.pending_id != row["pending_id"]
            or pending.digest != row["pending_digest"]
            or pending.reconciliation_id != row["reconciliation_id"]
            or pending.result.digest != row["result_digest"]
        ):
            raise PersistenceIntegrityError("stored pending-result metadata does not match payload")
        return pending

    @staticmethod
    def _decode_submission_row(
        row: sqlite3.Row,
        pending: PendingLogicalResult,
        runner: RunnerCapabilities,
    ) -> LogicalResultSubmission:
        try:
            submission = logical_result_submission_from_dict(json.loads(row["submission_payload"]), pending)
        except (ValueError, TypeError) as exc:
            raise PersistenceIntegrityError("stored logical result submission is invalid") from exc
        submitted = submission.submitted_session
        if (
            row["runner_id"] != runner.runner_id
            or row["session_id"] != pending.session_id
            or row["logical_attempt"] != pending.logical_attempt
            or row["pending_id"] != pending.pending_id
            or row["submission_id"] != submission.submission_id
            or row["submission_digest"] != submission.digest
            or row["result_digest"] != pending.result.digest
            or row["submitted_session_digest"] != sha256_digest(submitted)
            or submitted.session_id != pending.session_id
            or submitted.attempt != pending.logical_attempt
            or submitted.runner_id != runner.runner_id
            or submitted.runner_capability_digest != runner.digest
            or submitted.result_digest != pending.result.digest
            or submitted.state != "result_submitted"
        ):
            raise PersistenceIntegrityError("stored logical submission metadata does not match payload")
        return submission

    def _verify_pending_reconciliation(
        self,
        connection: sqlite3.Connection,
        pending: PendingLogicalResult,
    ) -> ReconciliationRecord:
        row = connection.execute(
            "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, previous_head_digest, "
            "committed_head_digest, record_payload FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
            (pending.runner_id, pending.authorization_id),
        ).fetchone()
        if row is None:
            raise PersistenceIntegrityError("pending logical result has no persisted reconciliation")
        record = self._decode_reconciliation_row(row)
        if (
            record.reconciliation_id != pending.reconciliation_id
            or record.digest != pending.reconciliation_digest
            or record.runner_capability_digest != pending.runner_capability_digest
            or record.session_id != pending.session_id
            or record.logical_attempt != pending.logical_attempt
            or record.spec_id != pending.spec_id
            or record.spec_digest != pending.spec_digest
            or record.authorization_id != pending.authorization_id
            or record.result_digest != pending.result.digest
        ):
            raise PersistenceIntegrityError("pending logical result is not bound to its exact reconciliation")
        return record

    def load_current(self, runner: RunnerCapabilities) -> DurableCapacitySnapshot | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload "
                "FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            return None if row is None else self._decode_row(row, runner)

    def load_reconciliation(self, runner: RunnerCapabilities, authorization_id: str) -> ReconciliationRecord | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, "
                "previous_head_digest, committed_head_digest, record_payload FROM ge_reconciliations "
                "WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, authorization_id),
            ).fetchone()
            return None if row is None else self._decode_reconciliation_row(row)

    def load_pending_result(
        self,
        runner: RunnerCapabilities,
        session_id: str,
        logical_attempt: int,
    ) -> PendingLogicalResult | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, "
                "result_digest, pending_payload FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, session_id, logical_attempt),
            ).fetchone()
            if row is None:
                return None
            pending = self._decode_pending_row(row, runner)
            self._verify_pending_reconciliation(connection, pending)
            return pending

    def load_result_submission(
        self,
        runner: RunnerCapabilities,
        session_id: str,
        logical_attempt: int,
    ) -> LogicalResultSubmission | None:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            pending_row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, "
                "result_digest, pending_payload FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, session_id, logical_attempt),
            ).fetchone()
            if pending_row is None:
                return None
            pending = self._decode_pending_row(pending_row, runner)
            self._verify_pending_reconciliation(connection, pending)
            row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, submission_id, submission_digest, result_digest, "
                "submitted_session_digest, submission_payload FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, session_id, logical_attempt),
            ).fetchone()
            return None if row is None else self._decode_submission_row(row, pending, runner)

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
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            if row is None:
                if expected_head_digest is not None:
                    raise PersistenceConflict("durable head is absent but a previous head was expected")
                if snapshot.head.previous_head_digest is not None:
                    raise PersistenceConflict("first stored snapshot cannot depend on an unstored predecessor")
                connection.execute(
                    "INSERT INTO ge_durable_heads (runner_id, head_digest, generation, snapshot_digest, snapshot_payload) VALUES (?, ?, ?, ?, ?)",
                    (runner.runner_id, snapshot.head.digest, snapshot.head.generation, snapshot.digest, payload),
                )
                previous_head_digest = None
                idempotent = False
            else:
                current = self._decode_row(row, runner)
                current_head_digest = current.head.digest
                if expected_head_digest != current_head_digest:
                    raise PersistenceConflict("expected durable head does not match canonical head")
                if snapshot.head.digest == current_head_digest:
                    if snapshot != current or snapshot.digest != row["snapshot_digest"] or payload != row["snapshot_payload"]:
                        raise PersistenceIntegrityError("same head digest maps to different stored snapshot")
                    previous_head_digest = current_head_digest
                    idempotent = True
                else:
                    if not verify_durable_successor(current, snapshot, runner):
                        raise PersistenceConflict("candidate snapshot is not a valid successor of canonical head")
                    cursor = connection.execute(
                        "UPDATE ge_durable_heads SET head_digest = ?, generation = ?, snapshot_digest = ?, snapshot_payload = ? WHERE runner_id = ? AND head_digest = ?",
                        (snapshot.head.digest, snapshot.head.generation, snapshot.digest, payload, runner.runner_id, current_head_digest),
                    )
                    if cursor.rowcount != 1:
                        raise PersistenceConflict("canonical durable head changed before commit")
                    previous_head_digest = current_head_digest
                    idempotent = False
            committed_row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            if committed_row is None or self._decode_row(committed_row, runner) != snapshot:
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
        pending = pending_logical_result_from_reconciliation(candidate, runner)
        pending_payload = canonical_json(pending_logical_result_to_dict(pending)) if pending is not None else None
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            existing_row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, previous_head_digest, committed_head_digest, record_payload FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, record.authorization_id),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode_reconciliation_row(existing_row)
                if existing != record or existing_row["record_payload"] != record_payload:
                    raise PersistenceConflict("authorization already has a different canonical reconciliation")
                pending_row = connection.execute(
                    "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, result_digest, pending_payload FROM ge_pending_results WHERE reconciliation_id = ?",
                    (record.reconciliation_id,),
                ).fetchone()
                if pending is None:
                    if pending_row is not None:
                        raise PersistenceIntegrityError("failure reconciliation unexpectedly has a pending logical result")
                else:
                    if pending_row is None:
                        raise PersistenceIntegrityError("completed reconciliation is missing its atomic pending logical result")
                    stored_pending = self._decode_pending_row(pending_row, runner)
                    self._verify_pending_reconciliation(connection, stored_pending)
                    if stored_pending != pending or pending_row["pending_payload"] != pending_payload:
                        raise PersistenceIntegrityError("stored pending result does not match reconciliation")
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
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload FROM ge_durable_heads WHERE runner_id = ?",
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
                "UPDATE ge_durable_heads SET head_digest = ?, generation = ?, snapshot_digest = ?, snapshot_payload = ? WHERE runner_id = ? AND head_digest = ?",
                (successor.head.digest, successor.head.generation, successor.digest, successor_payload, runner.runner_id, current.head.digest),
            )
            if cursor.rowcount != 1:
                raise PersistenceConflict("canonical durable head changed before reconciliation commit")
            connection.execute(
                "INSERT INTO ge_reconciliations (runner_id, authorization_id, reconciliation_id, reconciliation_digest, previous_head_digest, committed_head_digest, record_payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (runner.runner_id, record.authorization_id, record.reconciliation_id, record.digest, record.source_head_digest, record.successor_head_digest, record_payload),
            )
            if pending is not None:
                connection.execute(
                    "INSERT INTO ge_pending_results (runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, result_digest, pending_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (runner.runner_id, pending.session_id, pending.logical_attempt, pending.pending_id, pending.digest, pending.reconciliation_id, pending.result.digest, pending_payload),
                )
            committed_head_row = connection.execute(
                "SELECT runner_id, head_digest, generation, snapshot_digest, snapshot_payload FROM ge_durable_heads WHERE runner_id = ?",
                (runner.runner_id,),
            ).fetchone()
            committed_record_row = connection.execute(
                "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, previous_head_digest, committed_head_digest, record_payload FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
                (runner.runner_id, record.authorization_id),
            ).fetchone()
            if committed_head_row is None or committed_record_row is None:
                raise PersistenceIntegrityError("reconciliation transaction is incomplete")
            if self._decode_row(committed_head_row, runner) != successor:
                raise PersistenceIntegrityError("reconciliation transaction head does not match successor")
            if self._decode_reconciliation_row(committed_record_row) != record:
                raise PersistenceIntegrityError("reconciliation transaction record does not match candidate")
            if pending is not None:
                pending_row = connection.execute(
                    "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, result_digest, pending_payload FROM ge_pending_results WHERE reconciliation_id = ?",
                    (record.reconciliation_id,),
                ).fetchone()
                if pending_row is None:
                    raise PersistenceIntegrityError("reconciliation transaction is missing pending result")
                stored_pending = self._decode_pending_row(pending_row, runner)
                self._verify_pending_reconciliation(connection, stored_pending)
                if stored_pending != pending:
                    raise PersistenceIntegrityError("reconciliation transaction pending result does not match candidate")
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

    def commit_result_submission(
        self,
        submission: LogicalResultSubmission,
        source_session: ExecutionSession,
        runner: RunnerCapabilities,
    ) -> LogicalResultPersistenceReceipt:
        if not verify_logical_result_submission(submission, source_session, runner):
            raise PersistenceIntegrityError("logical result submission failed verification")
        pending = submission.pending
        payload = canonical_json(logical_result_submission_to_dict(submission))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            pending_row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, result_digest, pending_payload FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, pending.session_id, pending.logical_attempt),
            ).fetchone()
            if pending_row is None:
                raise PersistenceConflict("logical result submission requires a persisted pending result")
            stored_pending = self._decode_pending_row(pending_row, runner)
            if stored_pending != pending:
                raise PersistenceConflict("logical result submission does not match the canonical pending result")
            self._verify_pending_reconciliation(connection, stored_pending)
            existing_row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, submission_id, submission_digest, result_digest, submitted_session_digest, submission_payload FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, pending.session_id, pending.logical_attempt),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode_submission_row(existing_row, pending, runner)
                if existing != submission or existing_row["submission_payload"] != payload:
                    raise PersistenceConflict("logical Session already has a different canonical result submission")
                connection.commit()
                return LogicalResultPersistenceReceipt(
                    runner_id=runner.runner_id,
                    session_id=pending.session_id,
                    logical_attempt=pending.logical_attempt,
                    pending_id=pending.pending_id,
                    submission_id=submission.submission_id,
                    submission_digest=submission.digest,
                    result_digest=pending.result.digest,
                    submitted_session_digest=sha256_digest(submission.submitted_session),
                    idempotent=True,
                )
            connection.execute(
                "INSERT INTO ge_result_submissions (runner_id, session_id, logical_attempt, pending_id, submission_id, submission_digest, result_digest, submitted_session_digest, submission_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (runner.runner_id, pending.session_id, pending.logical_attempt, pending.pending_id, submission.submission_id, submission.digest, pending.result.digest, sha256_digest(submission.submitted_session), payload),
            )
            committed_row = connection.execute(
                "SELECT runner_id, session_id, logical_attempt, pending_id, submission_id, submission_digest, result_digest, submitted_session_digest, submission_payload FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, pending.session_id, pending.logical_attempt),
            ).fetchone()
            if committed_row is None or self._decode_submission_row(committed_row, pending, runner) != submission:
                raise PersistenceIntegrityError("logical result submission transaction is incomplete")
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise PersistenceConflict("logical result submission uniqueness constraint rejected the commit") from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return LogicalResultPersistenceReceipt(
            runner_id=runner.runner_id,
            session_id=pending.session_id,
            logical_attempt=pending.logical_attempt,
            pending_id=pending.pending_id,
            submission_id=submission.submission_id,
            submission_digest=submission.digest,
            result_digest=pending.result.digest,
            submitted_session_digest=sha256_digest(submission.submitted_session),
            idempotent=False,
        )
