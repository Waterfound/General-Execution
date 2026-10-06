from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Literal

from .canonical import canonical_json, sha256_digest

AUTH_LEASE_SCHEMA = "ge.provider-auth-lease.v1"
AUTH_OBSERVATION_SCHEMA = "ge.provider-auth-observation.v1"
AUTH_PATH_SCHEMA = "ge.provider-auth-path-decision.v1"
QUEUE_ITEM_SCHEMA = "ge.provider-auth-queue-item.v1"
QUEUE_RECORD_SCHEMA = "ge.provider-auth-queue-record.v1"
DRAIN_PLAN_SCHEMA = "ge.provider-auth-drain-plan.v1"
PROTOCOL_VERSION = "0.1.0"

AuthSurface = Literal["connector_api", "cloud_browser"]
AuthLeaseState = Literal[
    "AUTH_AVAILABLE",
    "AUTH_SUSPECT",
    "HUMAN_REAUTH_REQUIRED",
]
AuthObservationOutcome = Literal[
    "AUTH_SUCCESS",
    "AUTH_UNCERTAIN",
    "AUTH_REJECTED",
    "AUTH_CHALLENGE",
]
QueueStatus = Literal["queued", "drained"]


class PersistentAuthLeaseError(ValueError):
    """Raised when persistent authentication capability evidence is invalid."""


class AuthPathDisposition(str, Enum):
    USE_AUTH = "USE_AUTH"
    PROBE_AUTH = "PROBE_AUTH"
    HUMAN_REAUTH_REQUIRED = "HUMAN_REAUTH_REQUIRED"
    CONDITION_WAIT = "CONDITION_WAIT"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistentAuthLeaseError(f"{field} must be a non-empty string")
    return value.strip()


def _nonnegative_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PersistentAuthLeaseError(f"{field} must be a non-negative integer")
    return value


def _digest(value: str, field: str) -> str:
    value = _nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise PersistentAuthLeaseError(f"{field} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PersistentAuthLeaseError(f"{field} must contain 64 hexadecimal characters") from exc
    return value


def _bool(value: bool, field: str) -> bool:
    if not isinstance(value, bool):
        raise PersistentAuthLeaseError(f"{field} must be boolean")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise PersistentAuthLeaseError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise PersistentAuthLeaseError(f"{field} must not contain duplicates")
    return items


def _parse_time(value: str, field: str) -> datetime:
    raw = _nonempty(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PersistentAuthLeaseError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PersistentAuthLeaseError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ProviderAuthObservation:
    provider_id: str
    surface: AuthSurface
    outcome: AuthObservationOutcome
    observed_at: str
    evidence_ref: str
    evidence_digest: str
    human_interaction: bool = False
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    schema_version: str = AUTH_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != AUTH_OBSERVATION_SCHEMA:
            raise PersistentAuthLeaseError("unsupported auth observation schema")
        _nonempty(self.provider_id, "provider_id")
        if self.surface not in {"connector_api", "cloud_browser"}:
            raise PersistentAuthLeaseError("unsupported auth surface")
        if self.outcome not in {
            "AUTH_SUCCESS",
            "AUTH_UNCERTAIN",
            "AUTH_REJECTED",
            "AUTH_CHALLENGE",
        }:
            raise PersistentAuthLeaseError("unsupported auth observation outcome")
        _parse_time(self.observed_at, "observed_at")
        _nonempty(self.evidence_ref, "evidence_ref")
        _digest(self.evidence_digest, "evidence_digest")
        for field in (
            "human_interaction",
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
        ):
            _bool(getattr(self, field), field)
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise PersistentAuthLeaseError(
                "auth observation cannot persist credentials, cookies, or tokens"
            )
        if self.authority_created:
            raise PersistentAuthLeaseError("auth observation cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderAuthLease:
    provider_id: str
    surface: AuthSurface
    state: AuthLeaseState
    generation: int
    last_observed_at: str
    last_evidence_ref: str
    last_evidence_digest: str
    previous_lease_digest: str | None = None
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    schema_version: str = AUTH_LEASE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != AUTH_LEASE_SCHEMA:
            raise PersistentAuthLeaseError("unsupported auth lease schema")
        _nonempty(self.provider_id, "provider_id")
        if self.surface not in {"connector_api", "cloud_browser"}:
            raise PersistentAuthLeaseError("unsupported auth surface")
        if self.state not in {
            "AUTH_AVAILABLE",
            "AUTH_SUSPECT",
            "HUMAN_REAUTH_REQUIRED",
        }:
            raise PersistentAuthLeaseError("unsupported auth lease state")
        _nonnegative_int(self.generation, "generation")
        _parse_time(self.last_observed_at, "last_observed_at")
        _nonempty(self.last_evidence_ref, "last_evidence_ref")
        _digest(self.last_evidence_digest, "last_evidence_digest")
        if self.generation == 0:
            if self.previous_lease_digest is not None:
                raise PersistentAuthLeaseError(
                    "generation-zero auth lease cannot have predecessor"
                )
        else:
            if self.previous_lease_digest is None:
                raise PersistentAuthLeaseError(
                    "nonzero auth lease generation requires predecessor"
                )
            _digest(self.previous_lease_digest, "previous_lease_digest")
        for field in (
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
        ):
            _bool(getattr(self, field), field)
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise PersistentAuthLeaseError(
                "auth lease cannot persist credentials, cookies, or tokens"
            )
        if self.authority_created:
            raise PersistentAuthLeaseError("auth lease cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _state_for_outcome(outcome: AuthObservationOutcome) -> AuthLeaseState:
    if outcome == "AUTH_SUCCESS":
        return "AUTH_AVAILABLE"
    if outcome == "AUTH_UNCERTAIN":
        return "AUTH_SUSPECT"
    return "HUMAN_REAUTH_REQUIRED"


def initialize_auth_lease(observation: ProviderAuthObservation) -> ProviderAuthLease:
    return ProviderAuthLease(
        provider_id=observation.provider_id,
        surface=observation.surface,
        state=_state_for_outcome(observation.outcome),
        generation=0,
        last_observed_at=observation.observed_at,
        last_evidence_ref=observation.evidence_ref,
        last_evidence_digest=observation.evidence_digest,
    )


def apply_auth_observation(
    current: ProviderAuthLease,
    observation: ProviderAuthObservation,
) -> ProviderAuthLease:
    if observation.provider_id != current.provider_id:
        raise PersistentAuthLeaseError("auth observation provider mismatch")
    if observation.surface != current.surface:
        raise PersistentAuthLeaseError("auth observation surface mismatch")
    if _parse_time(observation.observed_at, "observed_at") < _parse_time(
        current.last_observed_at, "last_observed_at"
    ):
        raise PersistentAuthLeaseError("auth observation cannot move backwards in time")
    return ProviderAuthLease(
        provider_id=current.provider_id,
        surface=current.surface,
        state=_state_for_outcome(observation.outcome),
        generation=current.generation + 1,
        last_observed_at=observation.observed_at,
        last_evidence_ref=observation.evidence_ref,
        last_evidence_digest=observation.evidence_digest,
        previous_lease_digest=current.digest,
    )


def effective_auth_state(
    lease: ProviderAuthLease,
    *,
    now: str | None = None,
    evidence_stale_after_seconds: int | None = None,
) -> AuthLeaseState:
    """Return evidence freshness state without claiming the provider session expired.

    A freshness threshold can only downgrade AUTH_AVAILABLE to AUTH_SUSPECT.
    It never changes provider authentication state to HUMAN_REAUTH_REQUIRED.
    That terminal gate requires an explicit rejection/challenge observation.
    """

    if evidence_stale_after_seconds is None or lease.state != "AUTH_AVAILABLE":
        return lease.state
    _nonnegative_int(evidence_stale_after_seconds, "evidence_stale_after_seconds")
    if now is None:
        raise PersistentAuthLeaseError("now is required when freshness threshold is used")
    current = _parse_time(now, "now")
    observed = _parse_time(lease.last_observed_at, "last_observed_at")
    age = (current - observed).total_seconds()
    if age < 0:
        raise PersistentAuthLeaseError("now cannot precede auth observation")
    if age >= evidence_stale_after_seconds:
        return "AUTH_SUSPECT"
    return "AUTH_AVAILABLE"


@dataclass(frozen=True, slots=True)
class ProviderAuthPathDecision:
    provider_id: str
    disposition: str
    selected_surface: AuthSurface | None
    selected_lease_digest: str | None
    reasons: tuple[str, ...]
    human_interaction_required: bool
    human_action_ref: str | None = None
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    execution_triggered: bool = False
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = AUTH_PATH_SCHEMA
    decision_digest: str = ""

    def __post_init__(self) -> None:
        if self.disposition not in {item.value for item in AuthPathDisposition}:
            raise PersistentAuthLeaseError("unsupported auth path disposition")
        _nonempty(self.provider_id, "provider_id")
        if self.selected_surface is None:
            if self.selected_lease_digest is not None:
                raise PersistentAuthLeaseError(
                    "decision without selected surface cannot bind a lease"
                )
        else:
            if self.selected_surface not in {"connector_api", "cloud_browser"}:
                raise PersistentAuthLeaseError("unsupported selected auth surface")
            if self.selected_lease_digest is None:
                raise PersistentAuthLeaseError("selected auth surface requires lease digest")
            _digest(self.selected_lease_digest, "selected_lease_digest")
        for field in (
            "human_interaction_required",
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
            "execution_triggered",
        ):
            _bool(getattr(self, field), field)
        if self.human_interaction_required:
            _nonempty(self.human_action_ref or "", "human_action_ref")
        elif self.human_action_ref is not None:
            raise PersistentAuthLeaseError(
                "non-human auth path cannot carry human_action_ref"
            )
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise PersistentAuthLeaseError("auth path cannot persist authentication secrets")
        if self.authority_created:
            raise PersistentAuthLeaseError("auth path cannot create authority")
        if self.execution_triggered:
            raise PersistentAuthLeaseError("auth path decision cannot claim execution")

    @property
    def digest(self) -> str:
        return self.decision_digest


def _auth_decision_payload(decision: ProviderAuthPathDecision) -> dict[str, Any]:
    payload = _jsonable(decision)
    payload.pop("decision_digest", None)
    return payload


def auth_path_to_dict(decision: ProviderAuthPathDecision) -> dict[str, Any]:
    return {
        **_auth_decision_payload(decision),
        "decision_digest": decision.decision_digest,
    }


def verify_auth_path_decision(
    provider_id: str,
    leases: tuple[ProviderAuthLease, ...],
    decision: dict[str, Any],
    *,
    now: str | None = None,
    evidence_stale_after_seconds: int | None = None,
) -> bool:
    try:
        expected = auth_path_to_dict(
            select_provider_auth_path(
                provider_id,
                leases,
                now=now,
                evidence_stale_after_seconds=evidence_stale_after_seconds,
            )
        )
    except (PersistentAuthLeaseError, TypeError, ValueError):
        return False
    return expected == decision


def _finalize_auth_path(
    *,
    provider_id: str,
    disposition: AuthPathDisposition,
    reasons: tuple[str, ...],
    lease: ProviderAuthLease | None = None,
) -> ProviderAuthPathDecision:
    provisional = ProviderAuthPathDecision(
        provider_id=provider_id,
        disposition=disposition.value,
        selected_surface=lease.surface if lease else None,
        selected_lease_digest=lease.digest if lease else None,
        reasons=reasons,
        human_interaction_required=(
            disposition == AuthPathDisposition.HUMAN_REAUTH_REQUIRED
        ),
        human_action_ref=(
            f"auth://{provider_id}/reauthenticate"
            if disposition == AuthPathDisposition.HUMAN_REAUTH_REQUIRED
            else None
        ),
    )
    digest = sha256_digest(_auth_decision_payload(provisional))
    return ProviderAuthPathDecision(
        provider_id=provisional.provider_id,
        disposition=provisional.disposition,
        selected_surface=provisional.selected_surface,
        selected_lease_digest=provisional.selected_lease_digest,
        reasons=provisional.reasons,
        human_interaction_required=provisional.human_interaction_required,
        human_action_ref=provisional.human_action_ref,
        decision_digest=digest,
    )


def select_provider_auth_path(
    provider_id: str,
    leases: tuple[ProviderAuthLease, ...],
    *,
    now: str | None = None,
    evidence_stale_after_seconds: int | None = None,
) -> ProviderAuthPathDecision:
    provider_id = _nonempty(provider_id, "provider_id")
    relevant = [lease for lease in leases if lease.provider_id == provider_id]
    if not relevant:
        return _finalize_auth_path(
            provider_id=provider_id,
            disposition=AuthPathDisposition.HUMAN_REAUTH_REQUIRED,
            reasons=("no_authenticated_provider_capability_evidence",),
        )

    ranked_surface = {"connector_api": 0, "cloud_browser": 1}
    available = sorted(
        (
            lease
            for lease in relevant
            if effective_auth_state(
                lease,
                now=now,
                evidence_stale_after_seconds=evidence_stale_after_seconds,
            )
            == "AUTH_AVAILABLE"
        ),
        key=lambda lease: (ranked_surface[lease.surface], lease.provider_id),
    )
    if available:
        selected = available[0]
        return _finalize_auth_path(
            provider_id=provider_id,
            disposition=AuthPathDisposition.USE_AUTH,
            reasons=(
                "provider_auth_evidence_available",
                "connector_first" if selected.surface == "connector_api" else "reuse_existing_browser_session",
            ),
            lease=selected,
        )

    suspect = sorted(
        (
            lease
            for lease in relevant
            if effective_auth_state(
                lease,
                now=now,
                evidence_stale_after_seconds=evidence_stale_after_seconds,
            )
            == "AUTH_SUSPECT"
        ),
        key=lambda lease: (ranked_surface[lease.surface], lease.provider_id),
    )
    if suspect:
        selected = suspect[0]
        return _finalize_auth_path(
            provider_id=provider_id,
            disposition=AuthPathDisposition.PROBE_AUTH,
            reasons=(
                "authentication_evidence_stale_or_uncertain",
                "probe_before_human_reauthentication",
            ),
            lease=selected,
        )

    if any(lease.state == "HUMAN_REAUTH_REQUIRED" for lease in relevant):
        return _finalize_auth_path(
            provider_id=provider_id,
            disposition=AuthPathDisposition.HUMAN_REAUTH_REQUIRED,
            reasons=("provider_rejected_or_challenged_authentication",),
        )

    return _finalize_auth_path(
        provider_id=provider_id,
        disposition=AuthPathDisposition.CONDITION_WAIT,
        reasons=("provider_auth_state_unresolved",),
    )


@dataclass(frozen=True, slots=True)
class ProviderAuthQueueItem:
    queue_id: str
    provider_id: str
    work_id: str
    repository: str
    authority_ref: str
    source_revision: str
    requested_actions: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    priority: int = 100
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    schema_version: str = QUEUE_ITEM_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != QUEUE_ITEM_SCHEMA:
            raise PersistentAuthLeaseError("unsupported provider queue item schema")
        for field in (
            "queue_id",
            "provider_id",
            "work_id",
            "repository",
            "authority_ref",
            "source_revision",
        ):
            _nonempty(getattr(self, field), field)
        _unique(self.requested_actions, "requested_actions", allow_empty=False)
        _unique(self.required_capabilities, "required_capabilities", allow_empty=False)
        _nonnegative_int(self.priority, "priority")
        for field in (
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
        ):
            _bool(getattr(self, field), field)
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise PersistentAuthLeaseError("provider queue cannot contain auth secrets")
        if self.authority_created:
            raise PersistentAuthLeaseError("provider queue item cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderAuthQueueRecord:
    item: ProviderAuthQueueItem
    status: QueueStatus = "queued"
    drain_evidence_ref: str | None = None
    drain_evidence_digest: str | None = None
    schema_version: str = QUEUE_RECORD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != QUEUE_RECORD_SCHEMA:
            raise PersistentAuthLeaseError("unsupported provider queue record schema")
        if self.status not in {"queued", "drained"}:
            raise PersistentAuthLeaseError("unsupported provider queue status")
        if self.status == "queued":
            if self.drain_evidence_ref is not None or self.drain_evidence_digest is not None:
                raise PersistentAuthLeaseError("queued record cannot claim drain evidence")
        else:
            _nonempty(self.drain_evidence_ref or "", "drain_evidence_ref")
            _digest(self.drain_evidence_digest or "", "drain_evidence_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderDrainPlan:
    provider_id: str
    auth_decision_digest: str
    disposition: str
    queue_depth: int
    selected_queue_ids: tuple[str, ...]
    human_interaction_required: bool
    human_action_ref: str | None = None
    credentials_persisted: bool = False
    cookies_persisted: bool = False
    tokens_persisted: bool = False
    authority_created: bool = False
    execution_triggered: bool = False
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = DRAIN_PLAN_SCHEMA
    plan_digest: str = ""

    def __post_init__(self) -> None:
        if self.disposition not in {item.value for item in AuthPathDisposition}:
            raise PersistentAuthLeaseError("unsupported drain-plan disposition")
        _nonempty(self.provider_id, "provider_id")
        _digest(self.auth_decision_digest, "auth_decision_digest")
        _nonnegative_int(self.queue_depth, "queue_depth")
        _unique(self.selected_queue_ids, "selected_queue_ids")
        if len(self.selected_queue_ids) > self.queue_depth:
            raise PersistentAuthLeaseError("drain plan cannot select more than queue depth")
        if self.disposition != "USE_AUTH" and self.selected_queue_ids:
            raise PersistentAuthLeaseError(
                "only USE_AUTH drain plans may select queued work"
            )
        for field in (
            "human_interaction_required",
            "credentials_persisted",
            "cookies_persisted",
            "tokens_persisted",
            "authority_created",
            "execution_triggered",
        ):
            _bool(getattr(self, field), field)
        if self.human_interaction_required:
            _nonempty(self.human_action_ref or "", "human_action_ref")
        elif self.human_action_ref is not None:
            raise PersistentAuthLeaseError(
                "non-human drain plan cannot carry human_action_ref"
            )
        if self.credentials_persisted or self.cookies_persisted or self.tokens_persisted:
            raise PersistentAuthLeaseError("drain plan cannot persist auth secrets")
        if self.authority_created:
            raise PersistentAuthLeaseError("drain plan cannot create authority")
        if self.execution_triggered:
            raise PersistentAuthLeaseError("drain plan cannot claim execution")

    @property
    def digest(self) -> str:
        return self.plan_digest


def _drain_payload(plan: ProviderDrainPlan) -> dict[str, Any]:
    payload = _jsonable(plan)
    payload.pop("plan_digest", None)
    return payload


def drain_plan_to_dict(plan: ProviderDrainPlan) -> dict[str, Any]:
    return {**_drain_payload(plan), "plan_digest": plan.plan_digest}


def verify_provider_drain_plan(
    provider_id: str,
    leases: tuple[ProviderAuthLease, ...],
    queued_items: tuple[ProviderAuthQueueItem, ...],
    plan: dict[str, Any],
    *,
    max_items: int = 1,
    now: str | None = None,
    evidence_stale_after_seconds: int | None = None,
) -> bool:
    try:
        expected = drain_plan_to_dict(
            plan_provider_drain(
                provider_id,
                leases,
                queued_items,
                max_items=max_items,
                now=now,
                evidence_stale_after_seconds=evidence_stale_after_seconds,
            )
        )
    except (PersistentAuthLeaseError, TypeError, ValueError):
        return False
    return expected == plan


def plan_provider_drain(
    provider_id: str,
    leases: tuple[ProviderAuthLease, ...],
    queued_items: tuple[ProviderAuthQueueItem, ...],
    *,
    max_items: int = 1,
    now: str | None = None,
    evidence_stale_after_seconds: int | None = None,
) -> ProviderDrainPlan:
    _nonnegative_int(max_items, "max_items")
    auth = select_provider_auth_path(
        provider_id,
        leases,
        now=now,
        evidence_stale_after_seconds=evidence_stale_after_seconds,
    )
    relevant = sorted(
        (item for item in queued_items if item.provider_id == provider_id),
        key=lambda item: (item.priority, item.queue_id),
    )
    selected = (
        tuple(item.queue_id for item in relevant[:max_items])
        if auth.disposition == "USE_AUTH"
        else ()
    )
    provisional = ProviderDrainPlan(
        provider_id=provider_id,
        auth_decision_digest=auth.decision_digest,
        disposition=auth.disposition,
        queue_depth=len(relevant),
        selected_queue_ids=selected,
        human_interaction_required=auth.human_interaction_required,
        human_action_ref=auth.human_action_ref,
    )
    digest = sha256_digest(_drain_payload(provisional))
    return ProviderDrainPlan(
        provider_id=provisional.provider_id,
        auth_decision_digest=provisional.auth_decision_digest,
        disposition=provisional.disposition,
        queue_depth=provisional.queue_depth,
        selected_queue_ids=provisional.selected_queue_ids,
        human_interaction_required=provisional.human_interaction_required,
        human_action_ref=provisional.human_action_ref,
        plan_digest=digest,
    )


def auth_lease_to_dict(lease: ProviderAuthLease) -> dict[str, Any]:
    return _jsonable(lease)


def auth_lease_from_dict(data: dict[str, Any]) -> ProviderAuthLease:
    try:
        return ProviderAuthLease(**data)
    except (TypeError, ValueError) as exc:
        raise PersistentAuthLeaseError("invalid provider auth lease document") from exc


def queue_item_to_dict(item: ProviderAuthQueueItem) -> dict[str, Any]:
    return _jsonable(item)


def queue_item_from_dict(data: dict[str, Any]) -> ProviderAuthQueueItem:
    payload = dict(data)
    for field in ("requested_actions", "required_capabilities"):
        value = payload.get(field)
        if isinstance(value, list):
            payload[field] = tuple(value)
    try:
        return ProviderAuthQueueItem(**payload)
    except (TypeError, ValueError) as exc:
        raise PersistentAuthLeaseError("invalid provider auth queue item") from exc


def queue_record_to_dict(record: ProviderAuthQueueRecord) -> dict[str, Any]:
    return _jsonable(record)


def queue_record_from_dict(data: dict[str, Any]) -> ProviderAuthQueueRecord:
    payload = dict(data)
    item = payload.get("item")
    if not isinstance(item, dict):
        raise PersistentAuthLeaseError("provider queue record requires item")
    payload["item"] = queue_item_from_dict(item)
    try:
        return ProviderAuthQueueRecord(**payload)
    except (TypeError, ValueError) as exc:
        raise PersistentAuthLeaseError("invalid provider auth queue record") from exc


class SqliteProviderAuthStateStore:
    """Durable non-secret provider-auth evidence and queue state.

    The schema intentionally has no credential/token/cookie columns.
    """

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
                CREATE TABLE IF NOT EXISTS provider_auth_leases (
                    provider_id TEXT NOT NULL,
                    surface TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    lease_digest TEXT NOT NULL,
                    lease_json TEXT NOT NULL,
                    PRIMARY KEY(provider_id, surface)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_auth_queue (
                    queue_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    record_digest TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _decode_lease(row: tuple[Any, ...]) -> ProviderAuthLease:
        provider_id, surface, generation, lease_digest, lease_json = row
        try:
            data = json.loads(str(lease_json))
        except json.JSONDecodeError as exc:
            raise PersistentAuthLeaseError("stored auth lease is not valid JSON") from exc
        lease = auth_lease_from_dict(data)
        if (
            lease.provider_id != provider_id
            or lease.surface != surface
            or lease.generation != generation
            or lease.digest != lease_digest
        ):
            raise PersistentAuthLeaseError("stored auth lease metadata mismatch")
        return lease

    @staticmethod
    def _decode_queue(row: tuple[Any, ...]) -> ProviderAuthQueueRecord:
        queue_id, provider_id, status, record_digest, record_json = row
        try:
            data = json.loads(str(record_json))
        except json.JSONDecodeError as exc:
            raise PersistentAuthLeaseError("stored provider queue record is invalid JSON") from exc
        record = queue_record_from_dict(data)
        if (
            record.item.queue_id != queue_id
            or record.item.provider_id != provider_id
            or record.status != status
            or record.digest != record_digest
        ):
            raise PersistentAuthLeaseError("stored provider queue metadata mismatch")
        return record

    def observe(self, observation: ProviderAuthObservation) -> ProviderAuthLease:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT provider_id, surface, generation, lease_digest, lease_json
                FROM provider_auth_leases
                WHERE provider_id = ? AND surface = ?
                """,
                (observation.provider_id, observation.surface),
            ).fetchone()
            if row is None:
                next_lease = initialize_auth_lease(observation)
                connection.execute(
                    """
                    INSERT INTO provider_auth_leases(
                        provider_id, surface, generation, lease_digest, lease_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        next_lease.provider_id,
                        next_lease.surface,
                        next_lease.generation,
                        next_lease.digest,
                        canonical_json(auth_lease_to_dict(next_lease)),
                    ),
                )
            else:
                current = self._decode_lease(row)
                next_lease = apply_auth_observation(current, observation)
                cursor = connection.execute(
                    """
                    UPDATE provider_auth_leases
                    SET generation = ?, lease_digest = ?, lease_json = ?
                    WHERE provider_id = ? AND surface = ?
                      AND generation = ? AND lease_digest = ?
                    """,
                    (
                        next_lease.generation,
                        next_lease.digest,
                        canonical_json(auth_lease_to_dict(next_lease)),
                        current.provider_id,
                        current.surface,
                        current.generation,
                        current.digest,
                    ),
                )
                if cursor.rowcount != 1:
                    raise PersistentAuthLeaseError("provider auth lease compare-and-swap conflict")
            connection.commit()
            return next_lease
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load_leases(self, provider_id: str | None = None) -> tuple[ProviderAuthLease, ...]:
        with self._connect() as connection:
            if provider_id is None:
                rows = connection.execute(
                    """
                    SELECT provider_id, surface, generation, lease_digest, lease_json
                    FROM provider_auth_leases
                    ORDER BY provider_id, surface
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT provider_id, surface, generation, lease_digest, lease_json
                    FROM provider_auth_leases
                    WHERE provider_id = ?
                    ORDER BY surface
                    """,
                    (_nonempty(provider_id, "provider_id"),),
                ).fetchall()
        return tuple(self._decode_lease(row) for row in rows)

    def enqueue(self, item: ProviderAuthQueueItem) -> ProviderAuthQueueRecord:
        record = ProviderAuthQueueRecord(item=item)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT queue_id, provider_id, status, record_digest, record_json
                FROM provider_auth_queue WHERE queue_id = ?
                """,
                (item.queue_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode_queue(row)
                if existing.item != item:
                    raise PersistentAuthLeaseError(
                        "queue_id already bound to a different provider work item"
                    )
                connection.commit()
                return existing
            connection.execute(
                """
                INSERT INTO provider_auth_queue(
                    queue_id, provider_id, status, record_digest, record_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item.queue_id,
                    item.provider_id,
                    record.status,
                    record.digest,
                    canonical_json(queue_record_to_dict(record)),
                ),
            )
            connection.commit()
            return record
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def queued(self, provider_id: str) -> tuple[ProviderAuthQueueItem, ...]:
        provider_id = _nonempty(provider_id, "provider_id")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT queue_id, provider_id, status, record_digest, record_json
                FROM provider_auth_queue
                WHERE provider_id = ? AND status = 'queued'
                """,
                (provider_id,),
            ).fetchall()
        records = [self._decode_queue(row) for row in rows]
        return tuple(
            record.item
            for record in sorted(
                records,
                key=lambda record: (record.item.priority, record.item.queue_id),
            )
        )

    def mark_drained(
        self,
        queue_id: str,
        *,
        expected_item_digest: str,
        evidence_ref: str,
        evidence_digest: str,
    ) -> ProviderAuthQueueRecord:
        queue_id = _nonempty(queue_id, "queue_id")
        _digest(expected_item_digest, "expected_item_digest")
        _nonempty(evidence_ref, "evidence_ref")
        _digest(evidence_digest, "evidence_digest")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT queue_id, provider_id, status, record_digest, record_json
                FROM provider_auth_queue WHERE queue_id = ?
                """,
                (queue_id,),
            ).fetchone()
            if row is None:
                raise PersistentAuthLeaseError("provider queue item does not exist")
            current = self._decode_queue(row)
            if current.item.digest != expected_item_digest:
                raise PersistentAuthLeaseError("provider queue item digest mismatch")
            if current.status == "drained":
                connection.commit()
                return current
            next_record = ProviderAuthQueueRecord(
                item=current.item,
                status="drained",
                drain_evidence_ref=evidence_ref,
                drain_evidence_digest=evidence_digest,
            )
            cursor = connection.execute(
                """
                UPDATE provider_auth_queue
                SET status = ?, record_digest = ?, record_json = ?
                WHERE queue_id = ? AND status = 'queued' AND record_digest = ?
                """,
                (
                    next_record.status,
                    next_record.digest,
                    canonical_json(queue_record_to_dict(next_record)),
                    queue_id,
                    current.digest,
                ),
            )
            if cursor.rowcount != 1:
                raise PersistentAuthLeaseError("provider queue compare-and-swap conflict")
            connection.commit()
            return next_record
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def plan_drain(
        self,
        provider_id: str,
        *,
        max_items: int = 1,
        now: str | None = None,
        evidence_stale_after_seconds: int | None = None,
    ) -> ProviderDrainPlan:
        return plan_provider_drain(
            provider_id,
            self.load_leases(provider_id),
            self.queued(provider_id),
            max_items=max_items,
            now=now,
            evidence_stale_after_seconds=evidence_stale_after_seconds,
        )
