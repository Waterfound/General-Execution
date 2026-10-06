from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id
from .execution_launch_admission import (
    ExecutionLaunchOrder,
    ExecutionLaunchReceipt,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
)
from .executor_activation import (
    ExecutorActivationCapability,
    ExecutorActivationIntent,
    NativeActivationObservation,
)
from .work_sparse_unattended import (
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    WorkSparseControllerDecision,
)

AUTHORITY_SCHEMA = "ge.work-invocation-authority.v1"
REQUEST_SCHEMA = "ge.work-escalation-request.v1"
STATE_SCHEMA = "ge.work-escalation-state.v1"
PLATFORM_REQUEST_SCHEMA = "ge.work-platform-activation-request.v1"
PLATFORM_OBSERVATION_SCHEMA = "ge.work-platform-observation.v1"
PROTOCOL_VERSION = "0.1.0"

WorkEscalationStatus = Literal[
    "reserved",
    "platform_wait",
    "human_reauth_required",
    "platform_accepted",
    "failed_activation",
]
WorkPlatformOutcome = Literal[
    "PLATFORM_ACCEPTED",
    "PLATFORM_WAIT",
    "HUMAN_REAUTH_REQUIRED",
    "FAILED_ACTIVATION",
]


class WorkEscalationError(ValueError):
    """Raised when a Work escalation artifact violates a durable boundary."""


class WorkEscalationBudgetExhausted(WorkEscalationError):
    """Raised when a durable Work invocation budget has no remaining slot."""


def _nonempty(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkEscalationError(f"{field} must be a non-empty string")
    return value.strip()


def _nonnegative_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorkEscalationError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: int, field: str) -> int:
    _nonnegative_int(value, field)
    if value == 0:
        raise WorkEscalationError(f"{field} must be greater than zero")
    return value


def _digest(value: str, field: str) -> str:
    value = _nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise WorkEscalationError(f"{field} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise WorkEscalationError(f"{field} must contain hexadecimal digest") from exc
    return value


def _canonical_scopes(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise WorkEscalationError(f"{field} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise WorkEscalationError(f"{field} must not contain duplicates")
    if values != tuple(sorted(values)):
        raise WorkEscalationError(f"{field} must be canonical-sorted")
    return values


def _time(value: str, field: str) -> str:
    raw = _nonempty(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkEscalationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise WorkEscalationError(f"{field} must include timezone")
    return raw


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise WorkEscalationError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise WorkEscalationError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class WorkInvocationAuthority:
    actor: str
    authority_ref: str
    authority_boundary: str
    granted_scopes: tuple[str, ...]
    max_invocations: int
    authority_created: bool = False
    schema_version: str = AUTHORITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != AUTHORITY_SCHEMA:
            raise WorkEscalationError("unsupported Work invocation authority schema")
        _nonempty(self.actor, "actor")
        _nonempty(self.authority_ref, "authority_ref")
        _nonempty(self.authority_boundary, "authority_boundary")
        scopes = _canonical_scopes(self.granted_scopes, "granted_scopes")
        required = {"executor_activation", "work_invocation"}
        if not required <= set(scopes):
            raise WorkEscalationError(
                "Work invocation authority requires executor_activation and work_invocation scopes"
            )
        _positive_int(self.max_invocations, "max_invocations")
        if self.authority_created:
            raise WorkEscalationError("Work invocation authority artifact cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class WorkEscalationRequest:
    work_id: str
    objective: str
    repository: str
    source_revision: str
    authority_ref: str
    envelope_digest: str
    work_item_digest: str
    routing_decision_digest: str
    selected_executor_digest: str
    required_capabilities: tuple[str, ...]
    requested_actions: tuple[str, ...]
    max_work_invocations: int
    authority_digest: str
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA:
            raise WorkEscalationError("unsupported Work escalation request schema")
        for field in (
            "work_id",
            "objective",
            "repository",
            "source_revision",
            "authority_ref",
        ):
            _nonempty(getattr(self, field), field)
        for field in (
            "envelope_digest",
            "work_item_digest",
            "routing_decision_digest",
            "selected_executor_digest",
            "authority_digest",
        ):
            _digest(getattr(self, field), field)
        if not self.required_capabilities:
            raise WorkEscalationError("required_capabilities cannot be empty")
        if not self.requested_actions:
            raise WorkEscalationError("requested_actions cannot be empty")
        if len(self.required_capabilities) != len(set(self.required_capabilities)):
            raise WorkEscalationError("required_capabilities must not contain duplicates")
        if len(self.requested_actions) != len(set(self.requested_actions)):
            raise WorkEscalationError("requested_actions must not contain duplicates")
        _positive_int(self.max_work_invocations, "max_work_invocations")
        if self.authority_created:
            raise WorkEscalationError("Work escalation request cannot create authority")
        if self.execution_triggered:
            raise WorkEscalationError("Work escalation request cannot claim execution")

    @property
    def request_id(self) -> str:
        return stable_id("gewr", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def prepare_work_escalation_request(
    envelope: UnattendedAuthorityEnvelope,
    work: UnattendedWorkItem,
    decision: WorkSparseControllerDecision,
    authority: WorkInvocationAuthority,
) -> WorkEscalationRequest:
    if decision.disposition != "DISPATCH":
        raise WorkEscalationError("Work escalation requires a DISPATCH routing decision")
    if decision.selected_executor_id != "work" or not decision.work_required:
        raise WorkEscalationError("routing decision did not select Work")
    if decision.execution_triggered or decision.authority_created:
        raise WorkEscalationError("routing decision cannot claim execution or create authority")
    if decision.work_item_digest != work.digest:
        raise WorkEscalationError("routing decision work item digest mismatch")
    if decision.envelope_digest != envelope.digest:
        raise WorkEscalationError("routing decision envelope digest mismatch")
    if decision.authority_ref != envelope.authority_ref:
        raise WorkEscalationError("routing decision authority mismatch")
    if work.authority_ref != envelope.authority_ref:
        raise WorkEscalationError("work item authority mismatch")
    if authority.authority_ref != envelope.authority_ref:
        raise WorkEscalationError("Work invocation authority reference mismatch")
    if envelope.max_work_invocations <= 0:
        raise WorkEscalationError("Work invocation budget is not authorized")
    limit = min(envelope.max_work_invocations, authority.max_invocations)
    if limit <= 0:
        raise WorkEscalationError("Work invocation authority has no usable budget")
    return WorkEscalationRequest(
        work_id=work.work_id,
        objective=work.objective,
        repository=work.repository,
        source_revision=work.source_revision,
        authority_ref=work.authority_ref,
        envelope_digest=envelope.digest,
        work_item_digest=work.digest,
        routing_decision_digest=decision.decision_digest,
        selected_executor_digest=_digest(
            decision.selected_executor_digest or "",
            "selected_executor_digest",
        ),
        required_capabilities=work.required_capabilities,
        requested_actions=work.requested_actions,
        max_work_invocations=limit,
        authority_digest=authority.digest,
    )


@dataclass(frozen=True, slots=True)
class WorkEscalationState:
    request: WorkEscalationRequest
    slot_index: int
    status: WorkEscalationStatus
    revision: int
    previous_state_digest: str | None = None
    platform_observation_digest: str | None = None
    native_execution_ref: str | None = None
    condition_ref: str | None = None
    failure_reason: str | None = None
    authority_created: bool = False
    schema_version: str = STATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != STATE_SCHEMA:
            raise WorkEscalationError("unsupported Work escalation state schema")
        _positive_int(self.slot_index, "slot_index")
        _nonnegative_int(self.revision, "revision")
        if self.slot_index > self.request.max_work_invocations:
            raise WorkEscalationError("Work escalation slot exceeds request budget")
        if self.authority_created:
            raise WorkEscalationError("Work escalation state cannot create authority")
        if self.revision == 0:
            if self.status != "reserved" or self.previous_state_digest is not None:
                raise WorkEscalationError(
                    "revision-zero Work escalation state must be reserved without predecessor"
                )
            if any(
                value is not None
                for value in (
                    self.platform_observation_digest,
                    self.native_execution_ref,
                    self.condition_ref,
                    self.failure_reason,
                )
            ):
                raise WorkEscalationError("reserved state cannot claim provider outcome")
        else:
            _digest(self.previous_state_digest or "", "previous_state_digest")
            _digest(self.platform_observation_digest or "", "platform_observation_digest")
            if self.status == "platform_accepted":
                _nonempty(self.native_execution_ref, "native_execution_ref")
                if self.condition_ref is not None or self.failure_reason is not None:
                    raise WorkEscalationError("accepted state cannot carry wait/failure fields")
            elif self.status in {"platform_wait", "human_reauth_required"}:
                _nonempty(self.condition_ref, "condition_ref")
                if self.native_execution_ref is not None or self.failure_reason is not None:
                    raise WorkEscalationError("wait state cannot carry native execution/failure")
                if self.status == "human_reauth_required" and not str(
                    self.condition_ref
                ).startswith("auth://"):
                    raise WorkEscalationError(
                        "human reauthentication condition must use auth:// action ref"
                    )
            elif self.status == "failed_activation":
                _nonempty(self.failure_reason, "failure_reason")
                if self.native_execution_ref is not None or self.condition_ref is not None:
                    raise WorkEscalationError("failed state cannot carry native execution/wait")
            else:
                raise WorkEscalationError("unsupported Work escalation state")

    @property
    def reservation_digest(self) -> str:
        return sha256_digest(
            {
                "request_id": self.request.request_id,
                "request_digest": self.request.digest,
                "authority_ref": self.request.authority_ref,
                "envelope_digest": self.request.envelope_digest,
                "slot_index": self.slot_index,
            }
        )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _state_to_dict(state: WorkEscalationState) -> dict[str, Any]:
    return asdict(state)


def _state_from_dict(data: dict[str, Any]) -> WorkEscalationState:
    payload = dict(data)
    request_data = payload.get("request")
    if not isinstance(request_data, dict):
        raise WorkEscalationError("stored Work escalation state requires request")
    request_payload = dict(request_data)
    for field in ("required_capabilities", "requested_actions"):
        if isinstance(request_payload.get(field), list):
            request_payload[field] = tuple(request_payload[field])
    try:
        payload["request"] = WorkEscalationRequest(**request_payload)
        return WorkEscalationState(**payload)
    except (TypeError, ValueError) as exc:
        raise WorkEscalationError("invalid Work escalation state") from exc


class SqliteWorkEscalationStore:
    """Crash-safe Work budget reservation and provider-state ledger."""

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
                CREATE TABLE IF NOT EXISTS work_escalation (
                    request_id TEXT PRIMARY KEY,
                    request_digest TEXT NOT NULL,
                    authority_ref TEXT NOT NULL,
                    envelope_digest TEXT NOT NULL,
                    slot_index INTEGER NOT NULL,
                    state_digest TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    UNIQUE(authority_ref, envelope_digest, slot_index)
                )
                """
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> WorkEscalationState:
        (
            request_id,
            request_digest,
            authority_ref,
            envelope_digest,
            slot_index,
            state_digest,
            revision,
            state_json,
        ) = row
        try:
            state = _state_from_dict(json.loads(str(state_json)))
        except json.JSONDecodeError as exc:
            raise WorkEscalationError("stored Work escalation state is invalid JSON") from exc
        if (
            state.request.request_id != request_id
            or state.request.digest != request_digest
            or state.request.authority_ref != authority_ref
            or state.request.envelope_digest != envelope_digest
            or state.slot_index != slot_index
            or state.digest != state_digest
            or state.revision != revision
        ):
            raise WorkEscalationError("stored Work escalation metadata mismatch")
        return state

    def reserve(self, request: WorkEscalationRequest) -> WorkEscalationState:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT request_id, request_digest, authority_ref, envelope_digest,
                       slot_index, state_digest, revision, state_json
                FROM work_escalation
                WHERE request_id = ?
                """,
                (request.request_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if existing.request != request:
                    raise WorkEscalationError(
                        "request_id already bound to different Work escalation"
                    )
                connection.commit()
                return existing

            used = connection.execute(
                """
                SELECT COUNT(*), COALESCE(MAX(slot_index), 0)
                FROM work_escalation
                WHERE authority_ref = ? AND envelope_digest = ?
                """,
                (request.authority_ref, request.envelope_digest),
            ).fetchone()
            count = int(used[0])
            max_slot = int(used[1])
            if count >= request.max_work_invocations:
                raise WorkEscalationBudgetExhausted(
                    "durable Work invocation budget exhausted"
                )
            slot_index = max_slot + 1
            if slot_index > request.max_work_invocations:
                raise WorkEscalationBudgetExhausted(
                    "durable Work invocation slot exceeds budget"
                )
            state = WorkEscalationState(
                request=request,
                slot_index=slot_index,
                status="reserved",
                revision=0,
            )
            connection.execute(
                """
                INSERT INTO work_escalation(
                    request_id, request_digest, authority_ref, envelope_digest,
                    slot_index, state_digest, revision, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id,
                    request.digest,
                    request.authority_ref,
                    request.envelope_digest,
                    slot_index,
                    state.digest,
                    state.revision,
                    canonical_json(_state_to_dict(state)),
                ),
            )
            connection.commit()
            return state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, request_id: str) -> WorkEscalationState:
        request_id = _nonempty(request_id, "request_id")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT request_id, request_digest, authority_ref, envelope_digest,
                       slot_index, state_digest, revision, state_json
                FROM work_escalation WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            raise WorkEscalationError("Work escalation state does not exist")
        return self._decode(row)

    def compare_and_swap(
        self,
        previous: WorkEscalationState,
        next_state: WorkEscalationState,
    ) -> WorkEscalationState:
        if previous.request != next_state.request:
            raise WorkEscalationError("Work escalation transition changed request")
        if previous.slot_index != next_state.slot_index:
            raise WorkEscalationError("Work escalation transition changed budget slot")
        if next_state.previous_state_digest != previous.digest:
            raise WorkEscalationError("Work escalation predecessor mismatch")
        if next_state.revision != previous.revision + 1:
            raise WorkEscalationError("Work escalation revision must increment by one")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE work_escalation
                SET state_digest = ?, revision = ?, state_json = ?
                WHERE request_id = ? AND state_digest = ? AND revision = ?
                """,
                (
                    next_state.digest,
                    next_state.revision,
                    canonical_json(_state_to_dict(next_state)),
                    previous.request.request_id,
                    previous.digest,
                    previous.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise WorkEscalationError("Work escalation compare-and-swap conflict")
            connection.commit()
            return next_state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


@dataclass(frozen=True, slots=True)
class WorkPlatformActivationRequest:
    work_request_id: str
    work_request_digest: str
    reservation_digest: str
    slot_index: int
    launch_receipt_id: str
    launch_receipt_digest: str
    dispatch_identity: str
    repository: str
    source_revision: str
    authority_ref: str
    objective: str
    execution_triggered: bool = False
    authority_created: bool = False
    schema_version: str = PLATFORM_REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PLATFORM_REQUEST_SCHEMA:
            raise WorkEscalationError("unsupported Work platform request schema")
        for field in (
            "work_request_id",
            "launch_receipt_id",
            "dispatch_identity",
            "repository",
            "source_revision",
            "authority_ref",
            "objective",
        ):
            _nonempty(getattr(self, field), field)
        for field in (
            "work_request_digest",
            "reservation_digest",
            "launch_receipt_digest",
        ):
            _digest(getattr(self, field), field)
        _positive_int(self.slot_index, "slot_index")
        if self.execution_triggered:
            raise WorkEscalationError("platform activation request cannot claim execution")
        if self.authority_created:
            raise WorkEscalationError("platform activation request cannot create authority")

    @property
    def platform_request_id(self) -> str:
        return stable_id("gewp", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def work_platform_activation_request_to_dict(
    request: WorkPlatformActivationRequest,
) -> dict[str, Any]:
    return json.loads(canonical_json(request))


def work_platform_activation_request_from_dict(
    data: Any,
) -> WorkPlatformActivationRequest:
    obj = _exact(
        data,
        {
            "work_request_id",
            "work_request_digest",
            "reservation_digest",
            "slot_index",
            "launch_receipt_id",
            "launch_receipt_digest",
            "dispatch_identity",
            "repository",
            "source_revision",
            "authority_ref",
            "objective",
            "execution_triggered",
            "authority_created",
            "schema_version",
        },
        "Work platform activation request",
    )
    try:
        return WorkPlatformActivationRequest(**obj)
    except (TypeError, ValueError) as exc:
        raise WorkEscalationError("invalid Work platform activation request") from exc


def build_work_launch_order(
    request: WorkEscalationRequest,
    authority: WorkInvocationAuthority,
    capability: ExecutorActivationCapability,
) -> ExecutionLaunchOrder:
    if authority.digest != request.authority_digest:
        raise WorkEscalationError("Work invocation authority digest mismatch")
    if authority.authority_ref != request.authority_ref:
        raise WorkEscalationError("Work invocation authority reference mismatch")
    if capability.executor != "work":
        raise WorkEscalationError("Work launch requires executor capability 'work'")
    launch_authority = LaunchAuthorityBinding(
        actor=authority.actor,
        authority_ref=authority.authority_ref,
        authority_boundary=authority.authority_boundary,
        granted_scopes=authority.granted_scopes,
    )
    launch_executor = LaunchExecutorBinding(
        executor="work",
        availability="AVAILABLE" if capability.available else "UNAVAILABLE",
        evidence_ref=capability.evidence_ref,
        evidence_digest=capability.evidence_digest,
    )
    return ExecutionLaunchOrder(
        workstream_id=request.request_id,
        owner="general_execution",
        repository=request.repository,
        executor="work",
        objective=request.objective,
        order_ref=f"work-escalation://{request.request_id}",
        source_revision=request.source_revision,
        required_authority_scopes=("executor_activation", "work_invocation"),
        authority=launch_authority,
        executor_binding=launch_executor,
        known_first_artifact_ref=f"work-escalation://{request.request_id}",
    )


def prepare_work_platform_activation_request(
    state: WorkEscalationState,
    receipt: ExecutionLaunchReceipt,
) -> WorkPlatformActivationRequest:
    if receipt.disposition != "ADMITTED":
        raise WorkEscalationError("Work platform request requires ADMITTED launch receipt")
    if receipt.executor != "work":
        raise WorkEscalationError("Work platform request requires Work launch receipt")
    if receipt.workstream_id != state.request.request_id:
        raise WorkEscalationError("launch receipt workstream does not match Work request")
    if receipt.authority_ref != state.request.authority_ref:
        raise WorkEscalationError("launch receipt authority does not match Work request")
    if not receipt.dispatch_identity:
        raise WorkEscalationError("ADMITTED Work receipt lacks dispatch identity")
    return WorkPlatformActivationRequest(
        work_request_id=state.request.request_id,
        work_request_digest=state.request.digest,
        reservation_digest=state.reservation_digest,
        slot_index=state.slot_index,
        launch_receipt_id=receipt.receipt_id,
        launch_receipt_digest=receipt.digest,
        dispatch_identity=receipt.dispatch_identity,
        repository=state.request.repository,
        source_revision=state.request.source_revision,
        authority_ref=state.request.authority_ref,
        objective=state.request.objective,
    )


@dataclass(frozen=True, slots=True)
class WorkPlatformObservation:
    platform_request_id: str
    platform_request_digest: str
    dispatch_identity: str
    outcome: WorkPlatformOutcome
    observed_at: str
    evidence_ref: str
    evidence_digest: str
    native_execution_ref: str | None = None
    condition_ref: str | None = None
    failure_reason: str | None = None
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    schema_version: str = PLATFORM_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PLATFORM_OBSERVATION_SCHEMA:
            raise WorkEscalationError("unsupported Work platform observation schema")
        _nonempty(self.platform_request_id, "platform_request_id")
        _digest(self.platform_request_digest, "platform_request_digest")
        _nonempty(self.dispatch_identity, "dispatch_identity")
        _time(self.observed_at, "observed_at")
        _nonempty(self.evidence_ref, "evidence_ref")
        _digest(self.evidence_digest, "evidence_digest")
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise WorkEscalationError("Work platform observation cannot persist auth secrets")
        if self.authority_created:
            raise WorkEscalationError("Work platform observation cannot create authority")
        if self.outcome == "PLATFORM_ACCEPTED":
            _nonempty(self.native_execution_ref, "native_execution_ref")
            if self.condition_ref is not None or self.failure_reason is not None:
                raise WorkEscalationError("accepted Work observation cannot carry wait/failure")
        elif self.outcome == "PLATFORM_WAIT":
            _nonempty(self.condition_ref, "condition_ref")
            if self.native_execution_ref is not None or self.failure_reason is not None:
                raise WorkEscalationError("waiting Work observation cannot carry execution/failure")
        elif self.outcome == "HUMAN_REAUTH_REQUIRED":
            condition = _nonempty(self.condition_ref, "condition_ref")
            if not condition.startswith("auth://"):
                raise WorkEscalationError(
                    "human reauthentication Work observation requires auth:// condition"
                )
            if self.native_execution_ref is not None or self.failure_reason is not None:
                raise WorkEscalationError("reauth Work observation cannot carry execution/failure")
        elif self.outcome == "FAILED_ACTIVATION":
            _nonempty(self.failure_reason, "failure_reason")
            if self.native_execution_ref is not None or self.condition_ref is not None:
                raise WorkEscalationError("failed Work observation cannot carry execution/wait")
        else:
            raise WorkEscalationError("unsupported Work platform outcome")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def work_platform_observation_to_dict(
    observation: WorkPlatformObservation,
) -> dict[str, Any]:
    return json.loads(canonical_json(observation))


def work_platform_observation_from_dict(data: Any) -> WorkPlatformObservation:
    obj = _exact(
        data,
        {
            "platform_request_id",
            "platform_request_digest",
            "dispatch_identity",
            "outcome",
            "observed_at",
            "evidence_ref",
            "evidence_digest",
            "native_execution_ref",
            "condition_ref",
            "failure_reason",
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
            "schema_version",
        },
        "Work platform observation",
    )
    try:
        return WorkPlatformObservation(**obj)
    except (TypeError, ValueError) as exc:
        raise WorkEscalationError("invalid Work platform observation") from exc


def record_work_platform_observation(
    state: WorkEscalationState,
    platform_request: WorkPlatformActivationRequest,
    observation: WorkPlatformObservation,
) -> WorkEscalationState:
    if state.status in {"platform_accepted", "failed_activation"}:
        raise WorkEscalationError("terminal Work escalation state cannot transition")
    if platform_request.work_request_id != state.request.request_id:
        raise WorkEscalationError("platform request Work identity mismatch")
    if platform_request.work_request_digest != state.request.digest:
        raise WorkEscalationError("platform request Work digest mismatch")
    if platform_request.reservation_digest != state.reservation_digest:
        raise WorkEscalationError("platform request reservation mismatch")
    if observation.platform_request_id != platform_request.platform_request_id:
        raise WorkEscalationError("Work platform observation request identity mismatch")
    if observation.platform_request_digest != platform_request.digest:
        raise WorkEscalationError("Work platform observation request digest mismatch")
    if observation.dispatch_identity != platform_request.dispatch_identity:
        raise WorkEscalationError("Work platform observation dispatch mismatch")

    common = dict(
        request=state.request,
        slot_index=state.slot_index,
        revision=state.revision + 1,
        previous_state_digest=state.digest,
        platform_observation_digest=observation.digest,
    )
    if observation.outcome == "PLATFORM_ACCEPTED":
        return WorkEscalationState(
            **common,
            status="platform_accepted",
            native_execution_ref=observation.native_execution_ref,
        )
    if observation.outcome == "PLATFORM_WAIT":
        return WorkEscalationState(
            **common,
            status="platform_wait",
            condition_ref=observation.condition_ref,
        )
    if observation.outcome == "HUMAN_REAUTH_REQUIRED":
        return WorkEscalationState(
            **common,
            status="human_reauth_required",
            condition_ref=observation.condition_ref,
        )
    return WorkEscalationState(
        **common,
        status="failed_activation",
        failure_reason=observation.failure_reason,
    )


class ExternalWorkExecutorActivationAdapter:
    """EAC-01 adapter for an externally observed Work platform result.

    This adapter never launches Work. It only binds an already-observed native
    Work execution/failure to the exact EAC dispatch identity.
    """

    def __init__(
        self,
        capability: ExecutorActivationCapability,
        platform_request: WorkPlatformActivationRequest,
        observation: WorkPlatformObservation,
    ) -> None:
        if capability.executor != "work":
            raise WorkEscalationError("external Work adapter requires executor 'work'")
        self.capability = capability
        self.platform_request = platform_request
        self.observation = observation
        self.calls = 0

    def activate(self, intent: ExecutorActivationIntent) -> NativeActivationObservation:
        self.calls += 1
        if intent.dispatch_identity != self.platform_request.dispatch_identity:
            raise WorkEscalationError("EAC intent dispatch does not match Work platform request")
        if self.observation.platform_request_id != self.platform_request.platform_request_id:
            raise WorkEscalationError("Work provider observation request mismatch")
        if self.observation.platform_request_digest != self.platform_request.digest:
            raise WorkEscalationError("Work provider observation digest mismatch")
        if self.observation.dispatch_identity != intent.dispatch_identity:
            raise WorkEscalationError("Work provider observation dispatch mismatch")

        if self.observation.outcome == "PLATFORM_ACCEPTED":
            evidence = sha256_digest(
                {
                    "platform_observation_digest": self.observation.digest,
                    "native_execution_ref": self.observation.native_execution_ref,
                    "dispatch_identity": intent.dispatch_identity,
                    "authority_created": False,
                }
            )
            return NativeActivationObservation(
                activation_id=intent.activation_id,
                dispatch_identity=intent.dispatch_identity,
                executor="work",
                outcome="EXECUTOR_ACCEPTED",
                native_execution_ref=self.observation.native_execution_ref,
                evidence_ref=self.observation.evidence_ref,
                evidence_digest=evidence,
            )

        if self.observation.outcome == "FAILED_ACTIVATION":
            evidence = sha256_digest(
                {
                    "platform_observation_digest": self.observation.digest,
                    "failure_reason": self.observation.failure_reason,
                    "dispatch_identity": intent.dispatch_identity,
                    "authority_created": False,
                }
            )
            return NativeActivationObservation(
                activation_id=intent.activation_id,
                dispatch_identity=intent.dispatch_identity,
                executor="work",
                outcome="FAILED_ACTIVATION",
                failure_reason=self.observation.failure_reason,
                evidence_ref=self.observation.evidence_ref,
                evidence_digest=evidence,
            )

        raise WorkEscalationError(
            "Work platform wait/reauth observations remain in the bridge and are not terminal EAC activation evidence"
        )


def work_executor_capability(
    *,
    adapter_id: str = "general-execution/external-work-platform",
    adapter_version: str = "1",
    available: bool = True,
    evidence_ref: str = "chatgpt-work://activation-adapter",
) -> ExecutorActivationCapability:
    evidence = {
        "adapter_id": adapter_id,
        "adapter_version": adapter_version,
        "executor": "work",
        "idempotency_key": "dispatch_identity",
        "external_platform_observation_required": True,
        "authority_created": False,
        "available": available,
    }
    return ExecutorActivationCapability(
        executor="work",
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        evidence_ref=evidence_ref,
        evidence_digest=sha256_digest(evidence),
        available=available,
    )
