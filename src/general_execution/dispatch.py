from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id
from .capacity import CapacityLease, RunnerCapacityState, verify_capacity_state
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import (
    VALID_TRANSPORT_STATUSES,
    PhysicalAttemptAuthorization,
    PhysicalOutcomeBundle,
    verify_physical_outcome,
)

DispatchStatus = Literal["prepared", "submission_unknown", "observed"]
RecoveryAction = Literal["begin_submission", "reconcile_provider", "none"]

INTENT_SCHEMA = "ge.dispatch-intent.v1"
STATE_SCHEMA = "ge.dispatch-intent-state.v1"
PERMIT_SCHEMA = "ge.dispatch-permit.v1"
RECOVERY_ITEM_SCHEMA = "ge.dispatch-recovery-item.v1"
RECOVERY_REPORT_SCHEMA = "ge.dispatch-recovery-report.v1"


class DispatchIntentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DispatchIntent:
    runner_id: str
    runner_capability_digest: str
    lease_id: str
    lease_digest: str
    slot: int
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    capacity_state_digest: str
    schema_version: str = INTENT_SCHEMA

    def __post_init__(self) -> None:
        if self.slot < 0:
            raise ValueError("slot must be >= 0")
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError("attempt ordinals must be >= 1")
        for name in (
            "runner_id",
            "runner_capability_digest",
            "lease_id",
            "lease_digest",
            "session_id",
            "authorization_id",
            "authorization_digest",
            "invocation_id",
            "request_digest",
            "capacity_state_digest",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")

    @property
    def intent_id(self) -> str:
        return stable_id("gedi", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class DispatchIntentState:
    intent: DispatchIntent
    status: DispatchStatus
    revision: int
    previous_state_digest: str | None = None
    provider_invocation_id: str | None = None
    observation_digest: str | None = None
    receipt_digest: str | None = None
    outcome_digest: str | None = None
    transport_status: str | None = None
    schema_version: str = STATE_SCHEMA

    def __post_init__(self) -> None:
        observed_fields = (
            self.observation_digest,
            self.receipt_digest,
            self.outcome_digest,
            self.transport_status,
        )
        if self.status == "prepared":
            if self.revision != 0 or self.previous_state_digest is not None:
                raise ValueError("prepared dispatch state must be revision 0 without predecessor")
            if self.provider_invocation_id is not None or any(value is not None for value in observed_fields):
                raise ValueError("prepared dispatch state cannot carry provider evidence")
        elif self.status == "submission_unknown":
            if self.revision != 1 or not self.previous_state_digest:
                raise ValueError("submission_unknown dispatch state must be revision 1 with predecessor")
            if self.provider_invocation_id is not None or any(value is not None for value in observed_fields):
                raise ValueError("submission_unknown state cannot claim provider evidence")
        elif self.status == "observed":
            if self.revision != 2 or not self.previous_state_digest:
                raise ValueError("observed dispatch state must be revision 2 with predecessor")
            if any(value is None for value in observed_fields):
                raise ValueError("observed dispatch state requires admitted outcome evidence")
            if self.transport_status not in VALID_TRANSPORT_STATUSES:
                raise ValueError("observed dispatch state has unsupported transport status")
        else:
            raise ValueError("unsupported dispatch status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class DispatchPermit:
    """Proof that the durable outbox entered SUBMISSION_UNKNOWN.

    This is deliberately not sufficient transport authority. A future transport
    must additionally require a LiveDispatchPermit bound to current capacity.
    """

    intent_id: str
    intent_digest: str
    state_digest: str
    invocation_id: str
    request_digest: str
    authorization_id: str
    authorization_digest: str
    transport_authority: bool = False
    schema_version: str = PERMIT_SCHEMA

    def __post_init__(self) -> None:
        if self.transport_authority:
            raise ValueError("durable dispatch permit cannot grant transport authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class DispatchRecoveryItem:
    intent_id: str
    state_digest: str
    status: DispatchStatus
    invocation_id: str
    request_digest: str
    runner_id: str
    lease_id: str
    recovery_action: RecoveryAction
    blind_resubmission_authorized: bool = False
    provider_outcome_inferred: bool = False
    schema_version: str = RECOVERY_ITEM_SCHEMA

    def __post_init__(self) -> None:
        if self.blind_resubmission_authorized:
            raise ValueError("dispatch recovery cannot authorize blind resubmission")
        if self.provider_outcome_inferred:
            raise ValueError("dispatch recovery cannot infer provider outcome")
        expected = {
            "prepared": "begin_submission",
            "submission_unknown": "reconcile_provider",
            "observed": "none",
        }[self.status]
        if self.recovery_action != expected:
            raise ValueError("dispatch recovery action does not match durable status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class DispatchRecoveryReport:
    runner_id: str
    items: tuple[DispatchRecoveryItem, ...]
    prepared_count: int
    submission_unknown_count: int
    observed_count: int
    blind_resubmissions_authorized: int = 0
    provider_outcomes_inferred: int = 0
    schema_version: str = RECOVERY_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.blind_resubmissions_authorized != 0:
            raise ValueError("dispatch recovery cannot authorize blind resubmission")
        if self.provider_outcomes_inferred != 0:
            raise ValueError("dispatch recovery cannot infer provider outcome")
        counts = {
            "prepared": sum(item.status == "prepared" for item in self.items),
            "submission_unknown": sum(item.status == "submission_unknown" for item in self.items),
            "observed": sum(item.status == "observed" for item in self.items),
        }
        if (
            self.prepared_count,
            self.submission_unknown_count,
            self.observed_count,
        ) != (counts["prepared"], counts["submission_unknown"], counts["observed"]):
            raise ValueError("dispatch recovery counts do not reconcile")
        if any(item.runner_id != self.runner_id for item in self.items):
            raise ValueError("dispatch recovery report mixes runners")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _find_active_lease(state: RunnerCapacityState, lease_id: str, lease_digest: str) -> CapacityLease:
    matches = [
        lease
        for lease in state.active_leases
        if lease.lease_id == lease_id and lease.digest == lease_digest
    ]
    if len(matches) != 1:
        raise DispatchIntentError("dispatch intent does not reference one active capacity lease")
    return matches[0]


def prepare_dispatch_intent(
    capacity_state: RunnerCapacityState,
    runner: RunnerCapabilities,
    lease: CapacityLease,
    authorization: PhysicalAttemptAuthorization,
) -> DispatchIntent:
    if not verify_capacity_state(capacity_state, runner):
        raise DispatchIntentError("capacity state does not replay for runner")
    active = _find_active_lease(capacity_state, lease.lease_id, lease.digest)
    if active != lease:
        raise DispatchIntentError("capacity lease is not the exact active lease")
    request = authorization.request
    if (
        lease.runner_id != runner.runner_id
        or lease.runner_capability_digest != runner.digest
        or lease.authorization_id != authorization.authorization_id
        or lease.authorization_digest != authorization.digest
        or lease.invocation_id != request.invocation_id
        or lease.physical_attempt != authorization.physical_attempt
        or lease.session_id != request.session_id
        or lease.logical_attempt != request.attempt
        or request.runner_id != runner.runner_id
        or request.runner_capability_digest != runner.digest
    ):
        raise DispatchIntentError("authorization does not reproduce the active capacity lease")
    return DispatchIntent(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        slot=lease.slot,
        session_id=lease.session_id,
        logical_attempt=lease.logical_attempt,
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.digest,
        invocation_id=request.invocation_id,
        request_digest=request.digest,
        physical_attempt=authorization.physical_attempt,
        capacity_state_digest=capacity_state.digest,
    )


def initial_dispatch_state(intent: DispatchIntent) -> DispatchIntentState:
    return DispatchIntentState(intent=intent, status="prepared", revision=0)


def _intent_from_dict(data: dict[str, Any]) -> DispatchIntent:
    if not isinstance(data, dict) or data.get("schema_version") != INTENT_SCHEMA:
        raise DispatchIntentError("unsupported dispatch intent schema")
    try:
        return DispatchIntent(**data)
    except (TypeError, ValueError) as exc:
        raise DispatchIntentError("invalid durable dispatch intent") from exc


def dispatch_state_to_dict(state: DispatchIntentState) -> dict[str, Any]:
    return asdict(state)


def dispatch_state_from_dict(data: dict[str, Any]) -> DispatchIntentState:
    if not isinstance(data, dict) or data.get("schema_version") != STATE_SCHEMA:
        raise DispatchIntentError("unsupported dispatch intent state schema")
    payload = dict(data)
    intent = payload.get("intent")
    if not isinstance(intent, dict):
        raise DispatchIntentError("dispatch intent state requires intent")
    payload["intent"] = _intent_from_dict(intent)
    try:
        return DispatchIntentState(**payload)
    except (TypeError, ValueError) as exc:
        raise DispatchIntentError("invalid durable dispatch intent state") from exc


def serialize_dispatch_state(state: DispatchIntentState) -> str:
    return canonical_json(dispatch_state_to_dict(state))


def deserialize_dispatch_state(state_json: str) -> DispatchIntentState:
    try:
        data = json.loads(state_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise DispatchIntentError("durable dispatch state is not valid JSON") from exc
    return dispatch_state_from_dict(data)


def _validate_intent_against_capacity(
    intent: DispatchIntent,
    capacity_state: RunnerCapacityState,
    runner: RunnerCapabilities,
) -> CapacityLease:
    if not verify_capacity_state(capacity_state, runner):
        raise DispatchIntentError("capacity state does not replay for runner")
    if intent.runner_id != runner.runner_id or intent.runner_capability_digest != runner.digest:
        raise DispatchIntentError("dispatch intent runner capabilities changed")
    lease = _find_active_lease(capacity_state, intent.lease_id, intent.lease_digest)
    if (
        lease.authorization_id != intent.authorization_id
        or lease.authorization_digest != intent.authorization_digest
        or lease.invocation_id != intent.invocation_id
        or lease.physical_attempt != intent.physical_attempt
        or lease.session_id != intent.session_id
        or lease.logical_attempt != intent.logical_attempt
    ):
        raise DispatchIntentError("active lease no longer matches dispatch intent")
    return lease


def _permit(state: DispatchIntentState) -> DispatchPermit:
    if state.status != "submission_unknown":
        raise DispatchIntentError("dispatch permit requires submission_unknown durable state")
    intent = state.intent
    return DispatchPermit(
        intent_id=intent.intent_id,
        intent_digest=intent.digest,
        state_digest=state.digest,
        invocation_id=intent.invocation_id,
        request_digest=intent.request_digest,
        authorization_id=intent.authorization_id,
        authorization_digest=intent.authorization_digest,
    )


def verify_dispatch_permit(state: DispatchIntentState, permit: DispatchPermit) -> bool:
    if state.status != "submission_unknown" or permit.transport_authority:
        return False
    return permit == _permit(state)


class SqliteDispatchIntentStore:
    """Durable dispatch outbox with CAS state transitions and no transport side effects."""

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
                CREATE TABLE IF NOT EXISTS dispatch_intents (
                    intent_id TEXT PRIMARY KEY,
                    runner_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    state_digest TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS dispatch_lease_unique ON dispatch_intents(lease_id)"
            )

    @staticmethod
    def _decode_row(row: tuple[Any, ...]) -> DispatchIntentState:
        intent_id, runner_id, lease_id, state_digest, revision, state_json = row
        state = deserialize_dispatch_state(state_json)
        intent = state.intent
        if (
            intent.intent_id != intent_id
            or intent.runner_id != runner_id
            or intent.lease_id != lease_id
            or state.digest != state_digest
            or state.revision != revision
        ):
            raise DispatchIntentError("durable dispatch row metadata mismatch")
        return state

    @staticmethod
    def _select_columns() -> str:
        return "intent_id, runner_id, lease_id, state_digest, revision, state_json"

    def initialize(self, intent: DispatchIntent) -> DispatchIntentState:
        state = initial_dispatch_state(intent)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (intent.intent_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode_row(row)
                if existing != state:
                    raise DispatchIntentError("durable dispatch intent already exists with different state")
                connection.commit()
                return existing
            lease_row = connection.execute(
                "SELECT intent_id FROM dispatch_intents WHERE lease_id = ?",
                (intent.lease_id,),
            ).fetchone()
            if lease_row is not None:
                raise DispatchIntentError("capacity lease already has a durable dispatch intent")
            connection.execute(
                """
                INSERT INTO dispatch_intents(intent_id, runner_id, lease_id, state_digest, revision, state_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.intent_id,
                    intent.runner_id,
                    intent.lease_id,
                    state.digest,
                    state.revision,
                    serialize_dispatch_state(state),
                ),
            )
            connection.commit()
            return state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, intent_id: str) -> DispatchIntentState:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
        if row is None:
            raise DispatchIntentError("durable dispatch intent does not exist")
        return self._decode_row(row)

    def load_for_runner(self, runner_id: str) -> tuple[DispatchIntentState, ...]:
        # Full-table decode is deliberate: metadata corruption must not be able to
        # hide a submission_unknown row merely by changing its runner_id column.
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents ORDER BY intent_id"
            ).fetchall()
        decoded = tuple(self._decode_row(row) for row in rows)
        return tuple(state for state in decoded if state.intent.runner_id == runner_id)

    def _commit(self, current: DispatchIntentState, new_state: DispatchIntentState) -> DispatchIntentState:
        if new_state.intent != current.intent:
            raise DispatchIntentError("dispatch state transition cannot change intent identity")
        if new_state.revision != current.revision + 1 or new_state.previous_state_digest != current.digest:
            raise DispatchIntentError("dispatch state transition predecessor mismatch")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (current.intent.intent_id,),
            ).fetchone()
            if row is None:
                raise DispatchIntentError("durable dispatch intent does not exist")
            durable = self._decode_row(row)
            if durable != current:
                raise DispatchIntentError("stale durable dispatch intent state")
            cursor = connection.execute(
                """
                UPDATE dispatch_intents
                SET state_digest = ?, revision = ?, state_json = ?
                WHERE intent_id = ? AND runner_id = ? AND lease_id = ?
                  AND state_digest = ? AND revision = ?
                """,
                (
                    new_state.digest,
                    new_state.revision,
                    serialize_dispatch_state(new_state),
                    current.intent.intent_id,
                    current.intent.runner_id,
                    current.intent.lease_id,
                    current.digest,
                    current.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise DispatchIntentError("durable dispatch compare-and-swap failed")
            connection.commit()
            return new_state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def begin_submission(
        self,
        intent_id: str,
        expected_state_digest: str,
        capacity_state: RunnerCapacityState,
        runner: RunnerCapabilities,
    ) -> tuple[DispatchIntentState, DispatchPermit]:
        current = self.load(intent_id)
        if current.digest != expected_state_digest:
            raise DispatchIntentError("stale durable dispatch intent state")
        if current.status != "prepared":
            raise DispatchIntentError("only prepared dispatch intent may begin submission")
        _validate_intent_against_capacity(current.intent, capacity_state, runner)
        new_state = DispatchIntentState(
            intent=current.intent,
            status="submission_unknown",
            revision=1,
            previous_state_digest=current.digest,
        )
        committed = self._commit(current, new_state)
        return committed, _permit(committed)

    def record_observed(
        self,
        intent_id: str,
        expected_state_digest: str,
        spec: ExecutionSpec,
        registry: RunnerRegistry,
        plan: DispatchPlan,
        session: ExecutionSession,
        runner: RunnerCapabilities,
        outcome: PhysicalOutcomeBundle,
    ) -> DispatchIntentState:
        current = self.load(intent_id)
        if current.digest != expected_state_digest:
            raise DispatchIntentError("stale durable dispatch intent state")
        if current.status != "submission_unknown":
            raise DispatchIntentError("provider observation requires submission_unknown state")
        intent = current.intent
        if not verify_physical_outcome(spec, registry, plan, session, runner, outcome):
            raise DispatchIntentError("physical outcome does not verify")
        auth = outcome.authorization
        receipt = outcome.receipt
        if (
            auth.authorization_id != intent.authorization_id
            or auth.digest != intent.authorization_digest
            or auth.request.invocation_id != intent.invocation_id
            or auth.request.digest != intent.request_digest
            or auth.request.runner_id != intent.runner_id
            or auth.request.runner_capability_digest != intent.runner_capability_digest
            or auth.physical_attempt != intent.physical_attempt
        ):
            raise DispatchIntentError("physical outcome does not belong to durable dispatch intent")
        new_state = DispatchIntentState(
            intent=intent,
            status="observed",
            revision=2,
            previous_state_digest=current.digest,
            provider_invocation_id=receipt.provider_invocation_id,
            observation_digest=outcome.observation.digest,
            receipt_digest=receipt.digest,
            outcome_digest=outcome.digest,
            transport_status=receipt.transport_status,
        )
        return self._commit(current, new_state)


def _recovery_item(state: DispatchIntentState) -> DispatchRecoveryItem:
    action: RecoveryAction = {
        "prepared": "begin_submission",
        "submission_unknown": "reconcile_provider",
        "observed": "none",
    }[state.status]
    intent = state.intent
    return DispatchRecoveryItem(
        intent_id=intent.intent_id,
        state_digest=state.digest,
        status=state.status,
        invocation_id=intent.invocation_id,
        request_digest=intent.request_digest,
        runner_id=intent.runner_id,
        lease_id=intent.lease_id,
        recovery_action=action,
    )


def recover_dispatch_after_restart(
    store: SqliteDispatchIntentStore,
    runner_id: str,
) -> DispatchRecoveryReport:
    states = store.load_for_runner(runner_id)
    items = tuple(_recovery_item(state) for state in states)
    return DispatchRecoveryReport(
        runner_id=runner_id,
        items=items,
        prepared_count=sum(item.status == "prepared" for item in items),
        submission_unknown_count=sum(item.status == "submission_unknown" for item in items),
        observed_count=sum(item.status == "observed" for item in items),
    )


def verify_dispatch_recovery(
    store: SqliteDispatchIntentStore,
    report: DispatchRecoveryReport,
) -> bool:
    try:
        expected = recover_dispatch_after_restart(store, report.runner_id)
    except DispatchIntentError:
        return False
    return report == expected
