from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapter import request_from_dict, request_to_dict, verify_dispatch_request
from .canonical import canonical_json, sha256_digest, stable_id
from .durable import (
    DurableCapacitySnapshot,
    RecoveredInFlightLease,
    load_durable_snapshot,
    recover_after_restart,
    serialize_durable_snapshot,
    verify_durable_snapshot,
)
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import PhysicalAttemptAuthorization
from .planner import verify_plan
from .wire import spec_from_dict, spec_to_dict

RECOVERY_CONTEXT_SCHEMA = "ge.durable-recovery-context.v1"
RECOVERY_CONTEXT_STORE_SCHEMA = "ge.recovery-context-store.v1"


class RecoveryContextError(ValueError):
    pass


class RecoveryContextIntegrityError(RecoveryContextError):
    pass


class RecoveryContextConflict(RecoveryContextError):
    pass


def _require_schema(data: dict[str, Any], expected: str) -> None:
    if data.get("schema_version") != expected:
        raise RecoveryContextIntegrityError(f"schema_version must be {expected}")


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def runner_to_dict(runner: RunnerCapabilities) -> dict[str, Any]:
    return {
        "runner_id": runner.runner_id,
        "provider": runner.provider,
        "adapter": runner.adapter,
        "adapter_version": runner.adapter_version,
        "capabilities": list(runner.capabilities),
        "modes": list(runner.modes),
        "max_parallelism": runner.max_parallelism,
    }


def runner_from_dict(data: dict[str, Any]) -> RunnerCapabilities:
    return RunnerCapabilities(
        runner_id=str(data["runner_id"]),
        provider=str(data["provider"]),
        adapter=str(data["adapter"]),
        adapter_version=str(data["adapter_version"]),
        capabilities=tuple(str(item) for item in data["capabilities"]),
        modes=tuple(str(item) for item in data["modes"]),
        max_parallelism=int(data["max_parallelism"]),
    )


def registry_to_dict(registry: RunnerRegistry) -> dict[str, Any]:
    return {
        "schema_version": registry.schema_version,
        "runners": [runner_to_dict(runner) for runner in registry.runners],
    }


def registry_from_dict(data: dict[str, Any]) -> RunnerRegistry:
    _require_schema(data, "ge.runner-registry.v1")
    return RunnerRegistry(tuple(runner_from_dict(item) for item in data["runners"]))


def plan_to_dict(plan: DispatchPlan) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "spec_id": plan.spec_id,
        "spec_digest": plan.spec_digest,
        "registry_digest": plan.registry_digest,
        "mode": plan.mode,
        "runner_id": plan.runner_id,
        "runner_capability_digest": plan.runner_capability_digest,
        "deferral_reason": plan.deferral_reason,
    }


def plan_from_dict(data: dict[str, Any]) -> DispatchPlan:
    _require_schema(data, "ge.dispatch-plan.v1")
    return DispatchPlan(
        spec_id=str(data["spec_id"]),
        spec_digest=str(data["spec_digest"]),
        registry_digest=str(data["registry_digest"]),
        mode=str(data["mode"]),
        runner_id=str(data["runner_id"]) if data["runner_id"] is not None else None,
        runner_capability_digest=(
            str(data["runner_capability_digest"])
            if data["runner_capability_digest"] is not None
            else None
        ),
        deferral_reason=(str(data["deferral_reason"]) if data["deferral_reason"] is not None else None),
    )


def session_to_dict(session: ExecutionSession) -> dict[str, Any]:
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


def session_from_dict(data: dict[str, Any]) -> ExecutionSession:
    _require_schema(data, "ge.execution-session.v1")
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
        result_digest=str(data["result_digest"]) if data["result_digest"] is not None else None,
    )


def authorization_to_dict(authorization: PhysicalAttemptAuthorization) -> dict[str, Any]:
    return {
        "schema_version": authorization.schema_version,
        "request": request_to_dict(authorization.request),
        "physical_attempt": authorization.physical_attempt,
        "previous_invocation_id": authorization.previous_invocation_id,
        "previous_receipt_digest": authorization.previous_receipt_digest,
    }


def authorization_from_dict(data: dict[str, Any]) -> PhysicalAttemptAuthorization:
    _require_schema(data, "ge.physical-authorization.v1")
    return PhysicalAttemptAuthorization(
        request=request_from_dict(data["request"]),
        physical_attempt=int(data["physical_attempt"]),
        previous_invocation_id=(
            str(data["previous_invocation_id"]) if data["previous_invocation_id"] is not None else None
        ),
        previous_receipt_digest=(
            str(data["previous_receipt_digest"]) if data["previous_receipt_digest"] is not None else None
        ),
    )


@dataclass(frozen=True, slots=True)
class DurableRecoveryContext:
    anchor_snapshot: DurableCapacitySnapshot
    recovered_lease_id: str
    recovered_lease_digest: str
    runner_id: str
    spec: ExecutionSpec
    registry: RunnerRegistry
    plan: DispatchPlan
    session: ExecutionSession
    authorization: PhysicalAttemptAuthorization
    schema_version: str = RECOVERY_CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_CONTEXT_SCHEMA:
            raise ValueError("unsupported durable recovery context schema")
        _require_sha256("recovered_lease_digest", self.recovered_lease_digest)
        for name in ("recovered_lease_id", "runner_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.session.state != "running":
            raise ValueError("durable recovery context requires a running Session")

    @property
    def anchor_head_digest(self) -> str:
        return self.anchor_snapshot.head.digest

    @property
    def anchor_snapshot_digest(self) -> str:
        return self.anchor_snapshot.digest

    @property
    def digest(self) -> str:
        return sha256_digest(recovery_context_to_dict(self))

    @property
    def context_id(self) -> str:
        return stable_id("gec", recovery_context_to_dict(self))


def _runner_from_context(context: DurableRecoveryContext) -> RunnerCapabilities:
    matches = [runner for runner in context.registry.runners if runner.runner_id == context.runner_id]
    if len(matches) != 1:
        raise RecoveryContextIntegrityError("recovery context must contain exactly one selected runner")
    return matches[0]


def _state_extends(anchor: DurableCapacitySnapshot, current: DurableCapacitySnapshot) -> bool:
    anchor_transitions = anchor.state.transitions
    current_transitions = current.state.transitions
    return (
        current.state.generation >= anchor.state.generation
        and len(current_transitions) >= len(anchor_transitions)
        and current_transitions[: len(anchor_transitions)] == anchor_transitions
    )


def _find_recovered_lease(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    context: DurableRecoveryContext,
) -> RecoveredInFlightLease:
    _, report = recover_after_restart(snapshot, runner)
    matches = [
        lease
        for lease in report.active_leases
        if lease.lease_id == context.recovered_lease_id and lease.lease_digest == context.recovered_lease_digest
    ]
    if len(matches) != 1:
        raise RecoveryContextIntegrityError("recovery context does not bind one active recovered lease")
    return matches[0]


def verify_recovery_context(current: DurableCapacitySnapshot, context: DurableRecoveryContext) -> bool:
    try:
        runner = _runner_from_context(context)
        anchor = context.anchor_snapshot
        if not verify_durable_snapshot(anchor, runner) or not verify_durable_snapshot(current, runner):
            return False
        if not _state_extends(anchor, current):
            return False
        anchor_recovered = _find_recovered_lease(anchor, runner, context)
        current_recovered = _find_recovered_lease(current, runner, context)
        if anchor_recovered != current_recovered:
            return False
        if not verify_plan(context.spec, context.registry, context.plan):
            return False
        if context.plan.runner_id != runner.runner_id or context.plan.runner_capability_digest != runner.digest:
            return False
        session = context.session
        expected_session_binding = (
            context.spec.spec_id,
            context.spec.digest,
            context.plan.plan_id,
            context.plan.digest,
            runner.runner_id,
            runner.digest,
            context.plan.mode,
        )
        actual_session_binding = (
            session.spec_id,
            session.spec_digest,
            session.plan_id,
            session.plan_digest,
            session.runner_id,
            session.runner_capability_digest,
            session.mode,
        )
        if actual_session_binding != expected_session_binding or session.state != "running":
            return False
        if not verify_dispatch_request(
            context.spec,
            context.registry,
            context.plan,
            session,
            runner,
            context.authorization.request,
        ):
            return False
        authorization = context.authorization
        return (
            authorization.authorization_id == current_recovered.authorization_id
            and authorization.digest == current_recovered.authorization_digest
            and authorization.request.invocation_id == current_recovered.invocation_id
            and authorization.physical_attempt == current_recovered.physical_attempt
            and authorization.previous_invocation_id == current_recovered.previous_invocation_id
            and authorization.previous_receipt_digest == current_recovered.previous_receipt_digest
            and authorization.request.session_id == current_recovered.session_id
            and authorization.request.attempt == current_recovered.logical_attempt
        )
    except (ValueError, KeyError, TypeError, RecoveryContextError):
        return False


def build_recovery_context(
    anchor: DurableCapacitySnapshot,
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    authorization: PhysicalAttemptAuthorization,
    recovered: RecoveredInFlightLease,
) -> DurableRecoveryContext:
    context = DurableRecoveryContext(
        anchor_snapshot=anchor,
        recovered_lease_id=recovered.lease_id,
        recovered_lease_digest=recovered.lease_digest,
        runner_id=runner.runner_id,
        spec=spec,
        registry=registry,
        plan=plan,
        session=session,
        authorization=authorization,
    )
    if not verify_recovery_context(anchor, context):
        raise RecoveryContextIntegrityError("constructed recovery context failed verification")
    return context


def recovery_context_to_dict(context: DurableRecoveryContext) -> dict[str, Any]:
    return {
        "schema_version": context.schema_version,
        "anchor_snapshot": json.loads(serialize_durable_snapshot(context.anchor_snapshot)),
        "recovered_lease_id": context.recovered_lease_id,
        "recovered_lease_digest": context.recovered_lease_digest,
        "runner_id": context.runner_id,
        "spec": spec_to_dict(context.spec),
        "registry": registry_to_dict(context.registry),
        "plan": plan_to_dict(context.plan),
        "session": session_to_dict(context.session),
        "authorization": authorization_to_dict(context.authorization),
    }


def recovery_context_from_dict(data: dict[str, Any]) -> DurableRecoveryContext:
    _require_schema(data, RECOVERY_CONTEXT_SCHEMA)
    spec_data = data["spec"]
    if spec_data.get("schema_version") != "ge.execution-spec.v1":
        raise RecoveryContextIntegrityError("execution spec schema is required and must be v1")
    registry = registry_from_dict(data["registry"])
    runner_id = str(data["runner_id"])
    matches = [runner for runner in registry.runners if runner.runner_id == runner_id]
    if len(matches) != 1:
        raise RecoveryContextIntegrityError("serialized context must contain one selected runner")
    runner = matches[0]
    anchor_payload = canonical_json(data["anchor_snapshot"])
    try:
        anchor = load_durable_snapshot(anchor_payload, runner)
    except ValueError as exc:
        raise RecoveryContextIntegrityError("anchor durable snapshot is invalid") from exc
    return DurableRecoveryContext(
        anchor_snapshot=anchor,
        recovered_lease_id=str(data["recovered_lease_id"]),
        recovered_lease_digest=str(data["recovered_lease_digest"]),
        runner_id=runner_id,
        spec=spec_from_dict(spec_data),
        registry=registry,
        plan=plan_from_dict(data["plan"]),
        session=session_from_dict(data["session"]),
        authorization=authorization_from_dict(data["authorization"]),
    )


def serialize_recovery_context(context: DurableRecoveryContext) -> str:
    return canonical_json(recovery_context_to_dict(context))


def load_recovery_context(
    payload: str,
    current: DurableCapacitySnapshot,
    *,
    expected_context_digest: str | None = None,
) -> DurableRecoveryContext:
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise RecoveryContextIntegrityError("recovery context payload must decode to an object")
        context = recovery_context_from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, RecoveryContextError):
            raise
        raise RecoveryContextIntegrityError("recovery context payload could not be decoded") from exc
    if serialize_recovery_context(context) != payload:
        raise RecoveryContextIntegrityError("recovery context payload is not canonical")
    if expected_context_digest is not None and context.digest != expected_context_digest:
        raise RecoveryContextIntegrityError("recovery context digest does not match expected digest")
    if not verify_recovery_context(current, context):
        raise RecoveryContextIntegrityError("recovery context failed protocol verification")
    return context


@dataclass(frozen=True, slots=True)
class RecoveryContextCommitReceipt:
    context_id: str
    context_digest: str
    authorization_id: str
    anchor_head_digest: str
    idempotent: bool
    schema_version: str = "ge.recovery-context-commit-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.recovery-context-commit-receipt.v1":
            raise ValueError("unsupported recovery context commit receipt schema")
        for name in ("context_id", "authorization_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        _require_sha256("context_digest", self.context_digest)
        _require_sha256("anchor_head_digest", self.anchor_head_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SQLiteRecoveryContextStore:
    """Immutable filesystem-backed recovery-context registry."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("recovery context store must be filesystem-backed")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self.timeout_seconds = timeout_seconds
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
                "CREATE TABLE IF NOT EXISTS ge_recovery_context_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ge_recovery_contexts (
                    context_id TEXT PRIMARY KEY,
                    context_digest TEXT NOT NULL,
                    authorization_id TEXT NOT NULL UNIQUE,
                    anchor_head_digest TEXT NOT NULL,
                    anchor_snapshot_digest TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO ge_recovery_context_metadata(key, value) VALUES('schema_version', ?)",
                (RECOVERY_CONTEXT_STORE_SCHEMA,),
            )
            self._verify_store_schema(connection)

    def _verify_store_schema(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM ge_recovery_context_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != RECOVERY_CONTEXT_STORE_SCHEMA:
            raise RecoveryContextIntegrityError("recovery context store schema mismatch")

    def save(
        self,
        context: DurableRecoveryContext,
        current: DurableCapacitySnapshot,
    ) -> RecoveryContextCommitReceipt:
        if not verify_recovery_context(current, context):
            raise RecoveryContextIntegrityError("candidate recovery context failed verification")
        payload = serialize_recovery_context(context)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT context_id, context_digest, authorization_id, anchor_head_digest, "
                "anchor_snapshot_digest, payload FROM ge_recovery_contexts WHERE authorization_id = ?",
                (context.authorization.authorization_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO ge_recovery_contexts "
                    "(context_id, context_digest, authorization_id, anchor_head_digest, anchor_snapshot_digest, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        context.context_id,
                        context.digest,
                        context.authorization.authorization_id,
                        context.anchor_head_digest,
                        context.anchor_snapshot_digest,
                        payload,
                    ),
                )
                idempotent = False
            else:
                if (
                    row["context_id"] != context.context_id
                    or row["context_digest"] != context.digest
                    or row["anchor_head_digest"] != context.anchor_head_digest
                    or row["anchor_snapshot_digest"] != context.anchor_snapshot_digest
                    or row["payload"] != payload
                ):
                    raise RecoveryContextConflict("authorization already has a different durable recovery context")
                idempotent = True
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return RecoveryContextCommitReceipt(
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=context.authorization.authorization_id,
            anchor_head_digest=context.anchor_head_digest,
            idempotent=idempotent,
        )

    def _read_row_for_authorization(self, authorization_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT context_digest, anchor_head_digest, anchor_snapshot_digest, payload "
                "FROM ge_recovery_contexts WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
        if row is None:
            raise RecoveryContextIntegrityError("no durable recovery context exists for authorization")
        return row

    def load_for_recovered(
        self,
        current: DurableCapacitySnapshot,
        recovered: RecoveredInFlightLease,
    ) -> tuple[DurableRecoveryContext, RunnerCapabilities]:
        row = self._read_row_for_authorization(recovered.authorization_id)
        try:
            data = json.loads(row["payload"])
            if not isinstance(data, dict):
                raise RecoveryContextIntegrityError("stored recovery context is not an object")
            candidate = recovery_context_from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, RecoveryContextError):
                raise
            raise RecoveryContextIntegrityError("stored recovery context could not be decoded") from exc
        runner = _runner_from_context(candidate)
        loaded = load_recovery_context(
            row["payload"], current, expected_context_digest=row["context_digest"]
        )
        if (
            row["anchor_head_digest"] != loaded.anchor_head_digest
            or row["anchor_snapshot_digest"] != loaded.anchor_snapshot_digest
        ):
            raise RecoveryContextIntegrityError("stored recovery context metadata does not match payload")
        if loaded.recovered_lease_id != recovered.lease_id or loaded.recovered_lease_digest != recovered.lease_digest:
            raise RecoveryContextIntegrityError("durable recovery context does not match recovered lease")
        return loaded, runner

    def bootstrap_candidates(self) -> tuple[tuple[DurableRecoveryContext, RunnerCapabilities], ...]:
        """Decode self-contained anchor contexts so a cold coordinator can rediscover runner definitions."""
        with self._connect() as connection:
            self._verify_store_schema(connection)
            rows = connection.execute(
                "SELECT context_digest, anchor_head_digest, anchor_snapshot_digest, payload "
                "FROM ge_recovery_contexts ORDER BY authorization_id"
            ).fetchall()
        candidates: list[tuple[DurableRecoveryContext, RunnerCapabilities]] = []
        for row in rows:
            try:
                data = json.loads(row["payload"])
                if not isinstance(data, dict):
                    raise RecoveryContextIntegrityError("stored recovery context is not an object")
                context = recovery_context_from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                if isinstance(exc, RecoveryContextError):
                    raise
                raise RecoveryContextIntegrityError("stored recovery context could not be decoded") from exc
            if serialize_recovery_context(context) != row["payload"]:
                raise RecoveryContextIntegrityError("stored recovery context payload is not canonical")
            if (
                context.digest != row["context_digest"]
                or context.anchor_head_digest != row["anchor_head_digest"]
                or context.anchor_snapshot_digest != row["anchor_snapshot_digest"]
            ):
                raise RecoveryContextIntegrityError("stored recovery context metadata does not match payload")
            runner = _runner_from_context(context)
            if not verify_recovery_context(context.anchor_snapshot, context):
                raise RecoveryContextIntegrityError("stored recovery context fails anchor verification")
            candidates.append((context, runner))
        return tuple(candidates)

    def list_contexts(self) -> tuple[tuple[str, str, str], ...]:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            rows = connection.execute(
                "SELECT authorization_id, context_id, context_digest FROM ge_recovery_contexts ORDER BY authorization_id"
            ).fetchall()
        return tuple((row["authorization_id"], row["context_id"], row["context_digest"]) for row in rows)
