from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest
from .models import ExecutionSession, ResultEnvelope
from .session import revoke_session, submit_result
from .wire import result_from_dict, result_to_dict

SESSION_SETTLEMENT_STORE_SCHEMA = "ge.session-settlement-store.v1"
SESSION_RECORD_SCHEMA = "ge.durable-session-record.v1"
SettlementState = Literal["running", "result_submitted", "revoked"]


class SessionSettlementError(ValueError):
    pass


class SessionSettlementConflict(SessionSettlementError):
    pass


class SessionSettlementIntegrityError(SessionSettlementError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _session_to_dict(session: ExecutionSession) -> dict[str, Any]:
    return {
        "schema_version": session.schema_version,
        "spec_id": session.spec_id,
        "spec_digest": session.spec_digest,
        "plan_id": session.plan_id,
        "plan_digest": session.plan_digest,
        "runner_id": session.runner_id,
        "runner_capability_digest": session.runner_capability_digest,
        "mode": session.mode,
        "attempt": session.attempt,
        "state": session.state,
        "result_digest": session.result_digest,
    }


def _session_from_dict(data: dict[str, Any]) -> ExecutionSession:
    if data.get("schema_version") != "ge.execution-session.v1":
        raise SessionSettlementIntegrityError("execution Session schema must be v1")
    try:
        return ExecutionSession(
            spec_id=str(data["spec_id"]),
            spec_digest=str(data["spec_digest"]),
            plan_id=str(data["plan_id"]),
            plan_digest=str(data["plan_digest"]),
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            mode=str(data["mode"]),
            attempt=int(data["attempt"]),
            state=str(data["state"]),
            result_digest=(str(data["result_digest"]) if data["result_digest"] is not None else None),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionSettlementIntegrityError("invalid execution Session payload") from exc


@dataclass(frozen=True, slots=True)
class DurableSessionRecord:
    source_session: ExecutionSession
    current_session: ExecutionSession
    result: ResultEnvelope | None = None
    schema_version: str = SESSION_RECORD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SESSION_RECORD_SCHEMA:
            raise ValueError("unsupported durable Session record schema")
        if self.source_session.state != "running":
            raise ValueError("durable Session source must be running")
        if self.current_session.session_id != self.source_session.session_id:
            raise ValueError("durable Session record cannot change logical Session identity")
        if self.current_session.state not in {"running", "result_submitted", "revoked"}:
            raise ValueError("unsupported durable Session state")
        if self.current_session.state == "running":
            if self.current_session != self.source_session or self.result is not None:
                raise ValueError("running durable Session must equal source and carry no result")
        elif self.current_session.state == "result_submitted":
            if self.result is None:
                raise ValueError("result_submitted durable Session requires result")
            expected = submit_result(self.source_session, self.result)
            if self.current_session != expected:
                raise ValueError("result_submitted durable Session does not reproduce from source/result")
        else:
            if self.result is not None or self.current_session != revoke_session(self.source_session):
                raise ValueError("revoked durable Session must reproduce exact source revocation")

    @property
    def session_id(self) -> str:
        return self.source_session.session_id

    @property
    def source_session_digest(self) -> str:
        return sha256_digest(self.source_session)

    @property
    def current_session_digest(self) -> str:
        return sha256_digest(self.current_session)

    @property
    def digest(self) -> str:
        return sha256_digest(session_record_to_dict(self))


def session_record_to_dict(record: DurableSessionRecord) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "source_session": _session_to_dict(record.source_session),
        "current_session": _session_to_dict(record.current_session),
        "result": result_to_dict(record.result) if record.result is not None else None,
    }


def session_record_from_dict(data: dict[str, Any]) -> DurableSessionRecord:
    if data.get("schema_version") != SESSION_RECORD_SCHEMA:
        raise SessionSettlementIntegrityError("durable Session record schema mismatch")
    try:
        result_data = data["result"]
        if result_data is not None and result_data.get("schema_version") != "ge.result-envelope.v1":
            raise SessionSettlementIntegrityError("result envelope schema must be v1")
        return DurableSessionRecord(
            source_session=_session_from_dict(data["source_session"]),
            current_session=_session_from_dict(data["current_session"]),
            result=result_from_dict(result_data) if result_data is not None else None,
        )
    except SessionSettlementError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionSettlementIntegrityError("invalid durable Session record payload") from exc


def serialize_session_record(record: DurableSessionRecord) -> str:
    return canonical_json(session_record_to_dict(record))


def load_session_record(
    payload: str,
    *,
    expected_record_digest: str | None = None,
) -> DurableSessionRecord:
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise SessionSettlementIntegrityError("durable Session payload must decode to an object")
        record = session_record_from_dict(data)
    except json.JSONDecodeError as exc:
        raise SessionSettlementIntegrityError("durable Session payload is not valid JSON") from exc
    if serialize_session_record(record) != payload:
        raise SessionSettlementIntegrityError("durable Session payload is not canonical")
    if expected_record_digest is not None:
        _require_sha256("expected_record_digest", expected_record_digest)
        if record.digest != expected_record_digest:
            raise SessionSettlementIntegrityError("durable Session digest does not match expected digest")
    return record


@dataclass(frozen=True, slots=True)
class SessionSettlementReceipt:
    session_id: str
    source_session_digest: str
    committed_session_digest: str
    committed_record_digest: str
    state: SettlementState
    result_digest: str | None
    idempotent: bool
    schema_version: str = "ge.session-settlement-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.session-settlement-receipt.v1":
            raise ValueError("unsupported Session settlement receipt schema")
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must be non-empty")
        if self.state not in {"running", "result_submitted", "revoked"}:
            raise ValueError("unsupported Session settlement receipt state")
        for name in ("source_session_digest", "committed_session_digest", "committed_record_digest"):
            _require_sha256(name, getattr(self, name))
        if self.state == "result_submitted":
            if self.result_digest is None:
                raise ValueError("result_submitted receipt requires result_digest")
            _require_sha256("result_digest", self.result_digest)
        elif self.result_digest is not None:
            raise ValueError("only result_submitted receipt may carry result_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteSessionSettlementStore:
    """Filesystem-backed, one-way durable logical Session state store."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        self.timeout_seconds = timeout_seconds
        if not self.path or not self.path.strip():
            raise ValueError("path must be non-empty")
        if self.path == ":memory:":
            raise ValueError("Session settlement store requires filesystem-backed SQLite")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=self.timeout_seconds)
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ge_session_settlement_metadata ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ge_session_settlements ("
                "session_id TEXT PRIMARY KEY, source_session_digest TEXT NOT NULL, "
                "current_session_digest TEXT NOT NULL, state TEXT NOT NULL, "
                "record_digest TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO ge_session_settlement_metadata(key, value) "
                "VALUES('schema_version', ?)",
                (SESSION_SETTLEMENT_STORE_SCHEMA,),
            )
            self._verify_store_schema(connection)

    def _verify_store_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_session_settlement_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != SESSION_SETTLEMENT_STORE_SCHEMA:
            raise SessionSettlementIntegrityError("Session settlement store schema mismatch")

    @staticmethod
    def _decode_row(row: sqlite3.Row) -> DurableSessionRecord:
        record = load_session_record(row["payload"], expected_record_digest=row["record_digest"])
        if (
            record.session_id != row["session_id"]
            or record.source_session_digest != row["source_session_digest"]
            or record.current_session_digest != row["current_session_digest"]
            or record.current_session.state != row["state"]
        ):
            raise SessionSettlementIntegrityError("stored Session settlement metadata does not match payload")
        return record

    @staticmethod
    def _receipt(record: DurableSessionRecord, *, idempotent: bool) -> SessionSettlementReceipt:
        return SessionSettlementReceipt(
            session_id=record.session_id,
            source_session_digest=record.source_session_digest,
            committed_session_digest=record.current_session_digest,
            committed_record_digest=record.digest,
            state=record.current_session.state,
            result_digest=record.result.digest if record.result is not None else None,
            idempotent=idempotent,
        )

    def load(self, session_id: str) -> DurableSessionRecord | None:
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be non-empty")
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_session_settlements WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return self._decode_row(row)

    def register_running(self, session: ExecutionSession) -> SessionSettlementReceipt:
        if session.state != "running":
            raise SessionSettlementError("only a running Session can be registered")
        candidate = DurableSessionRecord(source_session=session, current_session=session)
        payload = serialize_session_record(candidate)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_session_settlements WHERE session_id = ?",
                (session.session_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO ge_session_settlements "
                    "(session_id, source_session_digest, current_session_digest, state, record_digest, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        candidate.session_id,
                        candidate.source_session_digest,
                        candidate.current_session_digest,
                        candidate.current_session.state,
                        candidate.digest,
                        payload,
                    ),
                )
                committed = candidate
                idempotent = False
            else:
                committed = self._decode_row(row)
                if committed != candidate:
                    raise SessionSettlementConflict("logical Session already has a different durable state")
                idempotent = True
            connection.commit()
            return self._receipt(committed, idempotent=idempotent)
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _settle(
        self,
        source_session: ExecutionSession,
        candidate: DurableSessionRecord,
    ) -> SessionSettlementReceipt:
        if source_session.state != "running":
            raise SessionSettlementError("settlement source Session must be running")
        if candidate.source_session != source_session:
            raise SessionSettlementError("candidate settlement does not use exact source Session")
        payload = serialize_session_record(candidate)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_session_settlements WHERE session_id = ?",
                (source_session.session_id,),
            ).fetchone()
            if row is None:
                raise SessionSettlementConflict("logical Session has no durable running registration")
            current = self._decode_row(row)
            if current.source_session != source_session:
                raise SessionSettlementConflict("durable Session source binding differs from settlement source")

            if current.current_session.state == "running":
                cursor = connection.execute(
                    "UPDATE ge_session_settlements SET current_session_digest = ?, state = ?, "
                    "record_digest = ?, payload = ? WHERE session_id = ? AND record_digest = ?",
                    (
                        candidate.current_session_digest,
                        candidate.current_session.state,
                        candidate.digest,
                        payload,
                        candidate.session_id,
                        current.digest,
                    ),
                )
                if cursor.rowcount != 1:
                    raise SessionSettlementConflict("durable Session changed before settlement commit")
                verify_row = connection.execute(
                    "SELECT * FROM ge_session_settlements WHERE session_id = ?",
                    (candidate.session_id,),
                ).fetchone()
                if verify_row is None:
                    raise SessionSettlementIntegrityError("committed Session settlement row disappeared")
                committed = self._decode_row(verify_row)
                if committed != candidate:
                    raise SessionSettlementIntegrityError("committed Session settlement does not match candidate")
                idempotent = False
            elif current == candidate:
                committed = current
                idempotent = True
            else:
                raise SessionSettlementConflict("logical Session is already terminal with a different settlement")

            connection.commit()
            return self._receipt(committed, idempotent=idempotent)
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def submit_result(
        self,
        source_session: ExecutionSession,
        result: ResultEnvelope,
    ) -> SessionSettlementReceipt:
        try:
            target = submit_result(source_session, result)
        except ValueError as exc:
            raise SessionSettlementError("result cannot settle the exact logical Session") from exc
        candidate = DurableSessionRecord(
            source_session=source_session,
            current_session=target,
            result=result,
        )
        return self._settle(source_session, candidate)

    def revoke(self, source_session: ExecutionSession) -> SessionSettlementReceipt:
        try:
            target = revoke_session(source_session)
        except ValueError as exc:
            raise SessionSettlementError("logical Session cannot be revoked from this source state") from exc
        candidate = DurableSessionRecord(
            source_session=source_session,
            current_session=target,
            result=None,
        )
        return self._settle(source_session, candidate)
