from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .canonical import sha256_digest, stable_id
from .reattachment import ProviderReattachmentKey

REFERENCE_JOB_REGISTRY_SCHEMA = "ge.reference-job-registry.v1"


class ReferenceRegistryError(ValueError):
    pass


class ReferenceRegistryConflict(ReferenceRegistryError):
    pass


class ReferenceRegistryIntegrityError(ReferenceRegistryError):
    pass


@dataclass(frozen=True, slots=True)
class ReferenceJobRecord:
    provider_key: str
    binding_digest: str
    job_id: str
    state: str
    terminal_payload: str | None = None
    terminal_payload_digest: str | None = None
    schema_version: str = "ge.reference-job-record.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reference-job-record.v1":
            raise ValueError("unsupported reference job record schema")
        if not self.provider_key or not self.provider_key.strip():
            raise ValueError("provider_key must be non-empty")
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id must be non-empty")
        if self.state not in {"running", "terminal"}:
            raise ValueError("unsupported reference job state")
        if self.state == "running" and (
            self.terminal_payload is not None or self.terminal_payload_digest is not None
        ):
            raise ValueError("running reference job cannot carry terminal payload")
        if self.state == "terminal" and (
            self.terminal_payload is None or self.terminal_payload_digest is None
        ):
            raise ValueError("terminal reference job requires terminal payload")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteReferenceJobRegistry:
    """Filesystem-backed reference registry for deterministic job identity and status."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        self.timeout_seconds = timeout_seconds
        if not self.path or not self.path.strip():
            raise ValueError("path must be non-empty")
        if self.path == ":memory:":
            raise ValueError("reference registry requires filesystem-backed SQLite")
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
                "CREATE TABLE IF NOT EXISTS ge_reference_registry_metadata ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ge_reference_jobs ("
                "provider_key TEXT PRIMARY KEY, binding_digest TEXT NOT NULL, "
                "job_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL, "
                "terminal_payload TEXT, terminal_payload_digest TEXT)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO ge_reference_registry_metadata(key, value) "
                "VALUES('schema_version', ?)",
                (REFERENCE_JOB_REGISTRY_SCHEMA,),
            )
            self._verify_schema(connection)

    def _verify_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_reference_registry_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != REFERENCE_JOB_REGISTRY_SCHEMA:
            raise ReferenceRegistryIntegrityError("reference registry schema mismatch")

    @staticmethod
    def job_id_for_key(key: ProviderReattachmentKey) -> str:
        return stable_id("gerj", {"provider_key": key.provider_key})

    @staticmethod
    def _decode(row: sqlite3.Row) -> ReferenceJobRecord:
        return ReferenceJobRecord(
            provider_key=row["provider_key"],
            binding_digest=row["binding_digest"],
            job_id=row["job_id"],
            state=row["state"],
            terminal_payload=row["terminal_payload"],
            terminal_payload_digest=row["terminal_payload_digest"],
        )

    def register(self, key: ProviderReattachmentKey) -> tuple[ReferenceJobRecord, bool]:
        job_id = self.job_id_for_key(key)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_reference_jobs WHERE provider_key = ?",
                (key.provider_key,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO ge_reference_jobs(provider_key, binding_digest, job_id, state) "
                    "VALUES (?, ?, ?, 'running')",
                    (key.provider_key, key.digest, job_id),
                )
                record = ReferenceJobRecord(key.provider_key, key.digest, job_id, "running")
                idempotent = False
            else:
                record = self._decode(row)
                if record.binding_digest != key.digest or record.job_id != job_id:
                    raise ReferenceRegistryIntegrityError("provider key maps to different reference binding")
                idempotent = True
            connection.commit()
            return record, idempotent
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def lookup(self, key: ProviderReattachmentKey) -> ReferenceJobRecord | None:
        with self._connect() as connection:
            self._verify_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_reference_jobs WHERE provider_key = ?",
                (key.provider_key,),
            ).fetchone()
            if row is None:
                return None
            record = self._decode(row)
            if record.binding_digest != key.digest or record.job_id != self.job_id_for_key(key):
                raise ReferenceRegistryIntegrityError("stored reference job binding is inconsistent")
            return record

    def mark_terminal(
        self,
        key: ProviderReattachmentKey,
        *,
        payload: str,
        payload_digest: str,
    ) -> bool:
        if sha256_digest(payload) != payload_digest:
            raise ReferenceRegistryIntegrityError("terminal payload digest mismatch")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_schema(connection)
            row = connection.execute(
                "SELECT * FROM ge_reference_jobs WHERE provider_key = ?",
                (key.provider_key,),
            ).fetchone()
            if row is None:
                raise ReferenceRegistryConflict("reference job does not exist")
            record = self._decode(row)
            if record.binding_digest != key.digest or record.job_id != self.job_id_for_key(key):
                raise ReferenceRegistryIntegrityError("stored reference job binding is inconsistent")
            if record.state == "terminal":
                if record.terminal_payload != payload or record.terminal_payload_digest != payload_digest:
                    raise ReferenceRegistryConflict("reference job already has a different terminal payload")
                idempotent = True
            elif record.state == "running":
                cursor = connection.execute(
                    "UPDATE ge_reference_jobs SET state = 'terminal', terminal_payload = ?, "
                    "terminal_payload_digest = ? WHERE provider_key = ? AND state = 'running'",
                    (payload, payload_digest, key.provider_key),
                )
                if cursor.rowcount != 1:
                    raise ReferenceRegistryConflict("reference job changed before terminal update")
                idempotent = False
            else:
                raise ReferenceRegistryIntegrityError("unsupported stored reference job state")
            connection.commit()
            return idempotent
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
