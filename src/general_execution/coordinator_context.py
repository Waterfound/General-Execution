from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .adapter import verify_dispatch_request
from .canonical import canonical_json, sha256_digest, stable_id
from .capacity import CapacityLease, RunnerCapacityState, verify_capacity_state
from .context_codec import (
    ContextCodecError,
    authorization_from_dict,
    authorization_to_dict,
    plan_from_dict,
    plan_to_dict,
    registry_from_dict,
    registry_to_dict,
    session_from_dict,
    session_to_dict,
)
from .dispatch import DispatchIntent, DispatchIntentError, DispatchIntentState, prepare_dispatch_intent
from .durable import DurableCapacityHead, capacity_state_from_dict, capacity_state_to_dict
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import PhysicalAttemptAuthorization
from .planner import verify_plan
from .wire import spec_from_dict, spec_to_dict

CONTEXT_SCHEMA = "ge.coordinator-recovery-context.v1"
STORE_SCHEMA = "ge.coordinator-recovery-context-store.v1"
RecoveryAction = Literal["begin_submission", "reconcile_provider", "none"]


class CoordinatorContextError(ValueError):
    pass


class CoordinatorContextIntegrityError(CoordinatorContextError):
    pass


class CoordinatorContextConflict(CoordinatorContextError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _runner(context: "DurableCoordinatorContext") -> RunnerCapabilities:
    matches = [runner for runner in context.registry.runners if runner.runner_id == context.runner_id]
    if len(matches) != 1:
        raise CoordinatorContextIntegrityError("context must contain exactly one selected runner")
    return matches[0]


def _active_lease(state: RunnerCapacityState, lease_id: str, lease_digest: str) -> CapacityLease:
    matches = [
        lease
        for lease in state.active_leases
        if lease.lease_id == lease_id and lease.digest == lease_digest
    ]
    if len(matches) != 1:
        raise CoordinatorContextIntegrityError("context does not bind one active capacity lease")
    return matches[0]


def _state_extends(anchor: RunnerCapacityState, current: RunnerCapacityState) -> bool:
    return (
        current.runner_id == anchor.runner_id
        and current.runner_capability_digest == anchor.runner_capability_digest
        and current.generation >= anchor.generation
        and len(current.transitions) >= len(anchor.transitions)
        and current.transitions[: len(anchor.transitions)] == anchor.transitions
    )


def _intent_from_dict(data: dict[str, Any]) -> DispatchIntent:
    if data.get("schema_version") != "ge.dispatch-intent.v1":
        raise CoordinatorContextIntegrityError("unsupported dispatch intent schema")
    try:
        return DispatchIntent(**data)
    except (TypeError, ValueError) as exc:
        raise CoordinatorContextIntegrityError("invalid dispatch intent in context") from exc


@dataclass(frozen=True, slots=True)
class DurableCoordinatorContext:
    anchor_state: RunnerCapacityState
    runner_id: str
    lease_id: str
    lease_digest: str
    dispatch_intent: DispatchIntent
    spec: ExecutionSpec
    registry: RunnerRegistry
    plan: DispatchPlan
    session: ExecutionSession
    authorization: PhysicalAttemptAuthorization
    schema_version: str = CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CONTEXT_SCHEMA:
            raise ValueError("unsupported coordinator recovery context schema")
        for name in ("runner_id", "lease_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        _require_sha256("lease_digest", self.lease_digest)
        if self.session.state != "running":
            raise ValueError("coordinator recovery context requires a running Session")

    @property
    def digest(self) -> str:
        return sha256_digest(coordinator_context_to_dict(self))

    @property
    def context_id(self) -> str:
        return stable_id("gec", coordinator_context_to_dict(self))


def verify_coordinator_context(
    current_state: RunnerCapacityState,
    context: DurableCoordinatorContext,
) -> bool:
    try:
        runner = _runner(context)
        if not verify_capacity_state(context.anchor_state, runner):
            return False
        if not verify_capacity_state(current_state, runner):
            return False
        if not _state_extends(context.anchor_state, current_state):
            return False
        anchor_lease = _active_lease(context.anchor_state, context.lease_id, context.lease_digest)
        current_lease = _active_lease(current_state, context.lease_id, context.lease_digest)
        if anchor_lease != current_lease:
            return False
        if not verify_plan(context.spec, context.registry, context.plan):
            return False
        if context.plan.runner_id != runner.runner_id or context.plan.runner_capability_digest != runner.digest:
            return False
        expected_session = (
            context.spec.spec_id,
            context.spec.digest,
            context.plan.plan_id,
            context.plan.digest,
            runner.runner_id,
            runner.digest,
            context.plan.mode,
        )
        actual_session = (
            context.session.spec_id,
            context.session.spec_digest,
            context.session.plan_id,
            context.session.plan_digest,
            context.session.runner_id,
            context.session.runner_capability_digest,
            context.session.mode,
        )
        if actual_session != expected_session or context.session.state != "running":
            return False
        request = context.authorization.request
        if not verify_dispatch_request(
            context.spec,
            context.registry,
            context.plan,
            context.session,
            runner,
            request,
        ):
            return False
        expected_intent = prepare_dispatch_intent(
            context.anchor_state,
            runner,
            anchor_lease,
            context.authorization,
        )
        return (
            context.dispatch_intent == expected_intent
            and context.dispatch_intent.lease_id == current_lease.lease_id
            and context.dispatch_intent.lease_digest == current_lease.digest
        )
    except (ValueError, CoordinatorContextError, DispatchIntentError):
        return False


def build_coordinator_context(
    anchor_state: RunnerCapacityState,
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    lease: CapacityLease,
    authorization: PhysicalAttemptAuthorization,
) -> DurableCoordinatorContext:
    intent = prepare_dispatch_intent(anchor_state, runner, lease, authorization)
    context = DurableCoordinatorContext(
        anchor_state=anchor_state,
        runner_id=runner.runner_id,
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        dispatch_intent=intent,
        spec=spec,
        registry=registry,
        plan=plan,
        session=session,
        authorization=authorization,
    )
    if not verify_coordinator_context(anchor_state, context):
        raise CoordinatorContextIntegrityError("constructed coordinator context failed verification")
    return context


def coordinator_context_to_dict(context: DurableCoordinatorContext) -> dict[str, Any]:
    return {
        "schema_version": context.schema_version,
        "anchor_state": capacity_state_to_dict(context.anchor_state),
        "runner_id": context.runner_id,
        "lease_id": context.lease_id,
        "lease_digest": context.lease_digest,
        "dispatch_intent": asdict(context.dispatch_intent),
        "spec": spec_to_dict(context.spec),
        "registry": registry_to_dict(context.registry),
        "plan": plan_to_dict(context.plan),
        "session": session_to_dict(context.session),
        "authorization": authorization_to_dict(context.authorization),
    }


def coordinator_context_from_dict(data: dict[str, Any]) -> DurableCoordinatorContext:
    if data.get("schema_version") != CONTEXT_SCHEMA:
        raise CoordinatorContextIntegrityError("unsupported coordinator context schema")
    spec_data = data.get("spec")
    if not isinstance(spec_data, dict) or spec_data.get("schema_version") != "ge.execution-spec.v1":
        raise CoordinatorContextIntegrityError("context requires explicit execution spec schema")
    try:
        registry = registry_from_dict(data["registry"])
        context = DurableCoordinatorContext(
            anchor_state=capacity_state_from_dict(data["anchor_state"]),
            runner_id=str(data["runner_id"]),
            lease_id=str(data["lease_id"]),
            lease_digest=str(data["lease_digest"]),
            dispatch_intent=_intent_from_dict(data["dispatch_intent"]),
            spec=spec_from_dict(spec_data),
            registry=registry,
            plan=plan_from_dict(data["plan"]),
            session=session_from_dict(data["session"]),
            authorization=authorization_from_dict(data["authorization"]),
        )
    except (KeyError, TypeError, ValueError, ContextCodecError) as exc:
        if isinstance(exc, CoordinatorContextError):
            raise
        raise CoordinatorContextIntegrityError("coordinator context could not be decoded") from exc
    runner = _runner(context)
    if not verify_capacity_state(context.anchor_state, runner):
        raise CoordinatorContextIntegrityError("context anchor state does not replay for runner")
    return context


def serialize_coordinator_context(context: DurableCoordinatorContext) -> str:
    return canonical_json(coordinator_context_to_dict(context))


def deserialize_coordinator_context(payload: str) -> DurableCoordinatorContext:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CoordinatorContextIntegrityError("coordinator context is not valid JSON") from exc
    if not isinstance(data, dict):
        raise CoordinatorContextIntegrityError("coordinator context must be an object")
    context = coordinator_context_from_dict(data)
    if serialize_coordinator_context(context) != payload:
        raise CoordinatorContextIntegrityError("coordinator context payload is not canonical")
    return context


@dataclass(frozen=True, slots=True)
class CoordinatorContextCommitReceipt:
    context_id: str
    context_digest: str
    authorization_id: str
    dispatch_intent_id: str
    idempotent: bool
    schema_version: str = "ge.coordinator-context-commit-receipt.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SqliteCoordinatorContextStore:
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
                CREATE TABLE IF NOT EXISTS coordinator_context_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS coordinator_contexts (
                    context_id TEXT PRIMARY KEY,
                    context_digest TEXT NOT NULL,
                    authorization_id TEXT NOT NULL UNIQUE,
                    dispatch_intent_id TEXT NOT NULL UNIQUE,
                    runner_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO coordinator_context_metadata(key, value) VALUES('schema_version', ?)",
                (STORE_SCHEMA,),
            )
            self._verify_store_schema(connection)

    @staticmethod
    def _verify_store_schema(connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM coordinator_context_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row[0] != STORE_SCHEMA:
            raise CoordinatorContextIntegrityError("unsupported coordinator context store schema")

    def save(self, context: DurableCoordinatorContext) -> CoordinatorContextCommitReceipt:
        if not verify_coordinator_context(context.anchor_state, context):
            raise CoordinatorContextIntegrityError("candidate coordinator context failed verification")
        payload = serialize_coordinator_context(context)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_store_schema(connection)
            row = connection.execute(
                "SELECT context_id, context_digest, dispatch_intent_id, runner_id, payload "
                "FROM coordinator_contexts WHERE authorization_id = ?",
                (context.authorization.authorization_id,),
            ).fetchone()
            if row is None:
                try:
                    connection.execute(
                        "INSERT INTO coordinator_contexts "
                        "(context_id, context_digest, authorization_id, dispatch_intent_id, runner_id, payload) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            context.context_id,
                            context.digest,
                            context.authorization.authorization_id,
                            context.dispatch_intent.intent_id,
                            context.runner_id,
                            payload,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise CoordinatorContextConflict(
                        "coordinator context identity conflicts with durable state"
                    ) from exc
                idempotent = False
            else:
                if row != (
                    context.context_id,
                    context.digest,
                    context.dispatch_intent.intent_id,
                    context.runner_id,
                    payload,
                ):
                    raise CoordinatorContextConflict("authorization already has a different coordinator context")
                idempotent = True
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return CoordinatorContextCommitReceipt(
            context_id=context.context_id,
            context_digest=context.digest,
            authorization_id=context.authorization.authorization_id,
            dispatch_intent_id=context.dispatch_intent.intent_id,
            idempotent=idempotent,
        )

    def candidates(self) -> tuple[DurableCoordinatorContext, ...]:
        with self._connect() as connection:
            self._verify_store_schema(connection)
            rows = connection.execute(
                "SELECT context_id, context_digest, authorization_id, dispatch_intent_id, runner_id, payload "
                "FROM coordinator_contexts ORDER BY authorization_id"
            ).fetchall()
        contexts: list[DurableCoordinatorContext] = []
        for context_id, context_digest, authorization_id, intent_id, runner_id, payload in rows:
            context = deserialize_coordinator_context(payload)
            if (
                context.context_id != context_id
                or context.digest != context_digest
                or context.authorization.authorization_id != authorization_id
                or context.dispatch_intent.intent_id != intent_id
                or context.runner_id != runner_id
            ):
                raise CoordinatorContextIntegrityError("coordinator context row metadata mismatch")
            contexts.append(context)
        return tuple(contexts)


@dataclass(frozen=True, slots=True)
class ColdCoordinatorBinding:
    context: DurableCoordinatorContext
    runner: RunnerCapabilities
    capacity_state: RunnerCapacityState
    capacity_head: DurableCapacityHead
    dispatch_state: DispatchIntentState
    recovery_action: RecoveryAction
    schema_version: str = "ge.cold-coordinator-binding.v1"

    def __post_init__(self) -> None:
        if not verify_coordinator_context(self.capacity_state, self.context):
            raise ValueError("cold coordinator binding context does not verify")
        if self.dispatch_state.intent != self.context.dispatch_intent:
            raise ValueError("cold coordinator binding dispatch state does not match context")
        expected = {
            "prepared": "begin_submission",
            "submission_unknown": "reconcile_provider",
            "observed": "none",
        }[self.dispatch_state.status]
        if self.recovery_action != expected:
            raise ValueError("cold coordinator recovery action does not match dispatch status")
