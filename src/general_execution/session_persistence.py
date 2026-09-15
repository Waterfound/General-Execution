from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .canonical import canonical_json, sha256_digest
from .models import ExecutionSession, RunnerCapabilities
from .persistence import SQLiteDurableHeadStore
from .reconciliation import reconciliation_record_from_dict
from .result_handoff import (
    logical_result_submission_from_dict,
    pending_logical_result_from_dict,
    verify_logical_result_submission,
    verify_pending_logical_result,
)
from .session_registry import (
    SessionRegistryTransition,
    session_registry_transition_from_dict,
    session_registry_transition_to_dict,
    verify_session_registry_chain,
    verify_session_registry_transition,
)
from .wire import session_from_dict, session_to_dict

SESSION_REGISTRY_SCHEMA_VERSION = "ge.sqlite-session-registry.v1"


class SessionPersistenceError(ValueError):
    pass


class SessionPersistenceConflict(SessionPersistenceError):
    pass


class SessionPersistenceIntegrityError(SessionPersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class SessionRegistryCommitReceipt:
    runner_id: str
    session_id: str
    revision: int
    transition_id: str
    transition_digest: str
    session_digest: str
    idempotent: bool
    schema_version: str = "ge.session-registry-commit-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.session-registry-commit-receipt.v1":
            raise ValueError("unsupported session registry commit receipt schema")
        for name in ("runner_id", "session_id", "transition_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        for name in ("transition_digest", "session_digest"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteSessionRegistry:
    """Durable append-only registry for logical ExecutionSession lifecycle transitions."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.path == ":memory:":
            raise ValueError("durable Session registry requires a filesystem-backed database")
        SQLiteDurableHeadStore(self.path, timeout_seconds=timeout_seconds)
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
                "CREATE TABLE IF NOT EXISTS ge_session_registry_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_session_heads (
                    runner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    session_digest TEXT NOT NULL,
                    session_payload TEXT NOT NULL,
                    transition_digest TEXT NOT NULL,
                    PRIMARY KEY (runner_id, session_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_session_transitions (
                    runner_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    transition_id TEXT NOT NULL UNIQUE,
                    transition_digest TEXT NOT NULL,
                    transition_payload TEXT NOT NULL,
                    PRIMARY KEY (runner_id, session_id, revision)
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO ge_session_registry_metadata(key, value) VALUES('schema_version', ?)",
                (SESSION_REGISTRY_SCHEMA_VERSION,),
            )
            self._verify_schema(connection)
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _verify_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_session_registry_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != SESSION_REGISTRY_SCHEMA_VERSION:
            raise SessionPersistenceIntegrityError("SQLite Session registry schema mismatch")

    @staticmethod
    def _verify_runner_binding(session: ExecutionSession, runner: RunnerCapabilities) -> bool:
        return session.runner_id == runner.runner_id and session.runner_capability_digest == runner.digest

    @staticmethod
    def _decode_transition_row(row: sqlite3.Row, runner: RunnerCapabilities) -> SessionRegistryTransition:
        try:
            transition = session_registry_transition_from_dict(json.loads(row["transition_payload"]))
        except (ValueError, TypeError) as exc:
            raise SessionPersistenceIntegrityError("stored Session transition is invalid") from exc
        if not verify_session_registry_transition(transition):
            raise SessionPersistenceIntegrityError("stored Session transition failed structural verification")
        if (
            row["runner_id"] != runner.runner_id
            or transition.session_id != row["session_id"]
            or transition.revision != row["revision"]
            or transition.transition_id != row["transition_id"]
            or transition.digest != row["transition_digest"]
            or not SQLiteSessionRegistry._verify_runner_binding(transition.target_session, runner)
            or (
                transition.source_session is not None
                and not SQLiteSessionRegistry._verify_runner_binding(transition.source_session, runner)
            )
        ):
            raise SessionPersistenceIntegrityError("stored Session transition metadata does not match payload")
        return transition

    @staticmethod
    def _decode_head_row(row: sqlite3.Row, runner: RunnerCapabilities) -> ExecutionSession:
        try:
            session = session_from_dict(json.loads(row["session_payload"]))
        except (ValueError, TypeError) as exc:
            raise SessionPersistenceIntegrityError("stored Session head is invalid") from exc
        if (
            row["runner_id"] != runner.runner_id
            or session.session_id != row["session_id"]
            or sha256_digest(session) != row["session_digest"]
            or not SQLiteSessionRegistry._verify_runner_binding(session, runner)
        ):
            raise SessionPersistenceIntegrityError("stored Session head metadata does not match payload")
        return session

    def _verify_submit_binding(
        self,
        connection: sqlite3.Connection,
        transition: SessionRegistryTransition,
        runner: RunnerCapabilities,
    ) -> None:
        if transition.kind != "submit_result":
            return
        source = transition.source_session
        if source is None:
            raise SessionPersistenceIntegrityError("submit_result transition has no source Session")
        pending_row = connection.execute(
            "SELECT runner_id, session_id, logical_attempt, pending_id, pending_digest, reconciliation_id, "
            "result_digest, pending_payload FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
            (runner.runner_id, source.session_id, source.attempt),
        ).fetchone()
        submission_row = connection.execute(
            "SELECT runner_id, session_id, logical_attempt, pending_id, submission_id, submission_digest, result_digest, "
            "submitted_session_digest, submission_payload FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
            (runner.runner_id, source.session_id, source.attempt),
        ).fetchone()
        if pending_row is None or submission_row is None:
            raise SessionPersistenceConflict("submit_result registry transition requires persisted result handoff")
        try:
            pending = pending_logical_result_from_dict(json.loads(pending_row["pending_payload"]))
            submission = logical_result_submission_from_dict(json.loads(submission_row["submission_payload"]), pending)
        except (ValueError, TypeError) as exc:
            raise SessionPersistenceIntegrityError("persisted result handoff is undecodable") from exc
        if not verify_pending_logical_result(pending, runner):
            raise SessionPersistenceIntegrityError("persisted pending result failed verification")
        if (
            pending_row["runner_id"] != runner.runner_id
            or pending_row["session_id"] != source.session_id
            or pending_row["logical_attempt"] != source.attempt
            or pending_row["pending_id"] != pending.pending_id
            or pending_row["pending_digest"] != pending.digest
            or pending_row["reconciliation_id"] != pending.reconciliation_id
            or pending_row["result_digest"] != pending.result.digest
        ):
            raise SessionPersistenceIntegrityError("persisted pending-result metadata does not match payload")
        if not verify_logical_result_submission(submission, source, runner):
            raise SessionPersistenceIntegrityError("persisted logical result submission failed verification")
        if (
            submission_row["runner_id"] != runner.runner_id
            or submission_row["session_id"] != source.session_id
            or submission_row["logical_attempt"] != source.attempt
            or submission_row["pending_id"] != pending.pending_id
            or submission_row["submission_id"] != submission.submission_id
            or submission_row["submission_digest"] != submission.digest
            or submission_row["result_digest"] != pending.result.digest
            or submission_row["submitted_session_digest"] != sha256_digest(submission.submitted_session)
        ):
            raise SessionPersistenceIntegrityError("persisted result-submission metadata does not match payload")
        reconciliation_row = connection.execute(
            "SELECT runner_id, authorization_id, reconciliation_id, reconciliation_digest, previous_head_digest, "
            "committed_head_digest, record_payload FROM ge_reconciliations WHERE runner_id = ? AND authorization_id = ?",
            (runner.runner_id, pending.authorization_id),
        ).fetchone()
        if reconciliation_row is None:
            raise SessionPersistenceIntegrityError("persisted result handoff has no reconciliation")
        try:
            reconciliation = reconciliation_record_from_dict(json.loads(reconciliation_row["record_payload"]))
        except (ValueError, TypeError) as exc:
            raise SessionPersistenceIntegrityError("persisted reconciliation is undecodable") from exc
        if (
            reconciliation_row["runner_id"] != runner.runner_id
            or reconciliation_row["authorization_id"] != pending.authorization_id
            or reconciliation_row["reconciliation_id"] != reconciliation.reconciliation_id
            or reconciliation_row["reconciliation_digest"] != reconciliation.digest
            or reconciliation_row["previous_head_digest"] != reconciliation.source_head_digest
            or reconciliation_row["committed_head_digest"] != reconciliation.successor_head_digest
            or reconciliation.reconciliation_id != pending.reconciliation_id
            or reconciliation.digest != pending.reconciliation_digest
            or reconciliation.result_digest != pending.result.digest
            or submission.submission_id != transition.result_submission_id
            or submission.digest != transition.result_submission_digest
            or submission.submitted_session != transition.target_session
        ):
            raise SessionPersistenceIntegrityError("submit_result registry transition does not match persisted handoff")

    def _history_locked(
        self,
        connection: sqlite3.Connection,
        runner: RunnerCapabilities,
        session_id: str,
    ) -> tuple[SessionRegistryTransition, ...]:
        rows = connection.execute(
            "SELECT runner_id, session_id, revision, transition_id, transition_digest, transition_payload "
            "FROM ge_session_transitions WHERE runner_id = ? AND session_id = ? ORDER BY revision",
            (runner.runner_id, session_id),
        ).fetchall()
        transitions = tuple(self._decode_transition_row(row, runner) for row in rows)
        if transitions and not verify_session_registry_chain(transitions):
            raise SessionPersistenceIntegrityError("stored Session transition chain failed replay")
        for transition in transitions:
            self._verify_submit_binding(connection, transition, runner)
        return transitions

    def _current_locked(
        self,
        connection: sqlite3.Connection,
        runner: RunnerCapabilities,
        session_id: str,
    ) -> tuple[ExecutionSession | None, tuple[SessionRegistryTransition, ...]]:
        history = self._history_locked(connection, runner, session_id)
        head_row = connection.execute(
            "SELECT runner_id, session_id, revision, session_digest, session_payload, transition_digest "
            "FROM ge_session_heads WHERE runner_id = ? AND session_id = ?",
            (runner.runner_id, session_id),
        ).fetchone()
        if head_row is None:
            if history:
                raise SessionPersistenceIntegrityError("Session transition history exists without a head")
            return None, ()
        if not history:
            raise SessionPersistenceIntegrityError("Session head exists without transition history")
        session = self._decode_head_row(head_row, runner)
        last = history[-1]
        if (
            head_row["revision"] != last.revision
            or head_row["transition_digest"] != last.digest
            or session != last.target_session
        ):
            raise SessionPersistenceIntegrityError("Session head does not match transition history")
        return session, history

    def load_history(
        self,
        runner: RunnerCapabilities,
        session_id: str,
    ) -> tuple[SessionRegistryTransition, ...]:
        with self._connect() as connection:
            self._verify_schema(connection)
            _, history = self._current_locked(connection, runner, session_id)
            return history

    def load_current(
        self,
        runner: RunnerCapabilities,
        session_id: str,
    ) -> ExecutionSession | None:
        with self._connect() as connection:
            self._verify_schema(connection)
            current, _ = self._current_locked(connection, runner, session_id)
            return current

    def commit_transition(
        self,
        transition: SessionRegistryTransition,
        runner: RunnerCapabilities,
    ) -> SessionRegistryCommitReceipt:
        if not verify_session_registry_transition(transition):
            raise SessionPersistenceIntegrityError("Session transition failed structural verification")
        if not self._verify_runner_binding(transition.target_session, runner):
            raise SessionPersistenceIntegrityError("Session transition target is not bound to runner")
        if transition.source_session is not None and not self._verify_runner_binding(transition.source_session, runner):
            raise SessionPersistenceIntegrityError("Session transition source is not bound to runner")
        payload = canonical_json(session_registry_transition_to_dict(transition))
        target_payload = canonical_json(session_to_dict(transition.target_session))
        target_digest = sha256_digest(transition.target_session)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_schema(connection)
            current, history = self._current_locked(connection, runner, transition.session_id)
            existing = connection.execute(
                "SELECT runner_id, session_id, revision, transition_id, transition_digest, transition_payload "
                "FROM ge_session_transitions WHERE transition_id = ?",
                (transition.transition_id,),
            ).fetchone()
            if existing is not None:
                decoded = self._decode_transition_row(existing, runner)
                if decoded != transition or existing["transition_payload"] != payload:
                    raise SessionPersistenceConflict("transition ID already maps to different Session transition")
                if transition not in history:
                    raise SessionPersistenceIntegrityError("replayed transition is not in the canonical Session history")
                self._verify_submit_binding(connection, transition, runner)
                connection.commit()
                return SessionRegistryCommitReceipt(
                    runner_id=runner.runner_id,
                    session_id=transition.session_id,
                    revision=transition.revision,
                    transition_id=transition.transition_id,
                    transition_digest=transition.digest,
                    session_digest=target_digest,
                    idempotent=True,
                )

            if transition.kind == "register":
                if current is not None or history:
                    raise SessionPersistenceConflict("logical Session is already registered")
            else:
                if current is None or not history:
                    raise SessionPersistenceConflict("logical Session is not registered")
                if (
                    history[-1].revision != transition.revision - 1
                    or current != transition.source_session
                    or sha256_digest(current) != transition.expected_session_digest
                ):
                    raise SessionPersistenceConflict("Session transition predecessor is stale")
            self._verify_submit_binding(connection, transition, runner)
            connection.execute(
                "INSERT INTO ge_session_transitions (runner_id, session_id, revision, transition_id, transition_digest, transition_payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (runner.runner_id, transition.session_id, transition.revision, transition.transition_id, transition.digest, payload),
            )
            if current is None:
                connection.execute(
                    "INSERT INTO ge_session_heads (runner_id, session_id, revision, session_digest, session_payload, transition_digest) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (runner.runner_id, transition.session_id, transition.revision, target_digest, target_payload, transition.digest),
                )
            else:
                cursor = connection.execute(
                    "UPDATE ge_session_heads SET revision = ?, session_digest = ?, session_payload = ?, transition_digest = ? "
                    "WHERE runner_id = ? AND session_id = ? AND revision = ? AND session_digest = ?",
                    (
                        transition.revision,
                        target_digest,
                        target_payload,
                        transition.digest,
                        runner.runner_id,
                        transition.session_id,
                        transition.revision - 1,
                        transition.expected_session_digest,
                    ),
                )
                if cursor.rowcount != 1:
                    raise SessionPersistenceConflict("Session head changed before transition commit")
            committed, committed_history = self._current_locked(connection, runner, transition.session_id)
            if committed != transition.target_session or not committed_history or committed_history[-1] != transition:
                raise SessionPersistenceIntegrityError("Session transition transaction is incomplete")
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise SessionPersistenceConflict("Session registry uniqueness constraint rejected transition") from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return SessionRegistryCommitReceipt(
            runner_id=runner.runner_id,
            session_id=transition.session_id,
            revision=transition.revision,
            transition_id=transition.transition_id,
            transition_digest=transition.digest,
            session_digest=target_digest,
            idempotent=False,
        )
