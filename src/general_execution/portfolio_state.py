from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest

PORTFOLIO_SCHEMA = "ge.portfolio-state.v1"
ENTRY_SCHEMA = "ge.portfolio-entry.v1"
BLOCKER_SCHEMA = "ge.portfolio-blocker.v1"
WAKE_SCHEMA = "ge.wake-condition.v1"

PortfolioRole = Literal["active", "secondary", "passive"]
PortfolioLifecycleState = Literal[
    "ready",
    "running",
    "verifying",
    "complete",
    "waiting_external",
    "rework",
    "di_required",
    "human_gate",
    "failed",
    "passive",
]
BlockerKind = Literal[
    "external_dependency",
    "time",
    "infrastructure",
    "evidence",
    "authorization",
    "authority",
    "unknown",
]
WakeKind = Literal["at_or_after", "event_received", "evidence_predicate_satisfied"]

VALID_ROLES = {"active", "secondary", "passive"}
VALID_STATES = {
    "ready",
    "running",
    "verifying",
    "complete",
    "waiting_external",
    "rework",
    "di_required",
    "human_gate",
    "failed",
    "passive",
}
VALID_BLOCKER_KINDS = {
    "external_dependency",
    "time",
    "infrastructure",
    "evidence",
    "authorization",
    "authority",
    "unknown",
}
VALID_WAKE_KINDS = {"at_or_after", "event_received", "evidence_predicate_satisfied"}
ACTIVE_STATES = VALID_STATES - {"passive"}


class PortfolioStateError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioStateError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _unique_nonempty(name: str, values: tuple[str, ...]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise PortfolioStateError(f"{name} must contain only non-empty strings")
    if len(values) != len(set(values)):
        raise PortfolioStateError(f"{name} must not contain duplicates")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise PortfolioStateError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PortfolioStateError(f"{name} must contain 64 hexadecimal characters") from exc


def _require_exact_fields(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PortfolioStateError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise PortfolioStateError(
            f"{label} fields mismatch: missing={missing} unknown={unknown}"
        )
    return data


@dataclass(frozen=True, slots=True)
class PortfolioBlocker:
    kind: BlockerKind
    detail: str
    evidence_refs: tuple[str, ...] = ()
    schema_version: str = BLOCKER_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BLOCKER_SCHEMA:
            raise PortfolioStateError("unsupported portfolio blocker schema")
        if self.kind not in VALID_BLOCKER_KINDS:
            raise PortfolioStateError("unsupported blocker kind")
        _nonempty("blocker.detail", self.detail)
        _unique_nonempty("blocker.evidence_refs", self.evidence_refs)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class WakeCondition:
    kind: WakeKind
    value: str
    schema_version: str = WAKE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WAKE_SCHEMA:
            raise PortfolioStateError("unsupported wake condition schema")
        if self.kind not in VALID_WAKE_KINDS:
            raise PortfolioStateError("unsupported wake condition kind")
        _nonempty("wake_condition.value", self.value)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PortfolioEntry:
    work_id: str
    role: PortfolioRole
    state: PortfolioLifecycleState
    objective: str
    active_gate: str
    next_action_ref: str
    source_revision: str
    evidence_required: tuple[str, ...] = ()
    authority_boundary: str | None = None
    authority_ref: str | None = None
    blockers: tuple[PortfolioBlocker, ...] = ()
    wake_condition: WakeCondition | None = None
    checkpoint_ref: str | None = None
    schema_version: str = ENTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ENTRY_SCHEMA:
            raise PortfolioStateError("unsupported portfolio entry schema")
        if self.role not in VALID_ROLES:
            raise PortfolioStateError("unsupported portfolio role")
        if self.state not in VALID_STATES:
            raise PortfolioStateError("unsupported portfolio lifecycle state")

        for name in (
            "work_id",
            "objective",
            "active_gate",
            "next_action_ref",
            "source_revision",
        ):
            _nonempty(name, getattr(self, name))

        _unique_nonempty("evidence_required", self.evidence_required)
        _optional_nonempty("authority_boundary", self.authority_boundary)
        _optional_nonempty("authority_ref", self.authority_ref)
        _optional_nonempty("checkpoint_ref", self.checkpoint_ref)

        blocker_keys = [(blocker.kind, blocker.detail, blocker.evidence_refs) for blocker in self.blockers]
        if len(blocker_keys) != len(set(blocker_keys)):
            raise PortfolioStateError("blockers must not contain duplicates")

        if self.role == "active":
            if self.state not in ACTIVE_STATES:
                raise PortfolioStateError("active entry cannot use passive state")
            if self.wake_condition is not None and self.state != "waiting_external":
                raise PortfolioStateError(
                    "active wake condition is valid only while waiting_external"
                )
            if self.state == "waiting_external" and not self.blockers:
                raise PortfolioStateError("waiting_external active entry requires a blocker")
            if self.state == "human_gate":
                if not self.authority_boundary:
                    raise PortfolioStateError(
                        "human_gate active entry requires authority_boundary"
                    )
                if not any(
                    blocker.kind in {"authorization", "authority"}
                    for blocker in self.blockers
                ):
                    raise PortfolioStateError(
                        "human_gate active entry requires authorization/authority blocker"
                    )

        elif self.role == "secondary":
            if self.state != "ready":
                raise PortfolioStateError("secondary entry must remain ready")
            if self.blockers:
                raise PortfolioStateError("secondary entry cannot carry blockers")
            if self.wake_condition is not None:
                raise PortfolioStateError("secondary entry cannot carry wake condition")

        elif self.role == "passive":
            if self.state != "passive":
                raise PortfolioStateError("passive entry must use passive state")
            if not self.blockers:
                raise PortfolioStateError("passive entry requires at least one blocker")
            if self.wake_condition is None:
                raise PortfolioStateError(
                    "passive entry requires an explicit wake condition"
                )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PortfolioState:
    portfolio_id: str
    generation: int
    active: PortfolioEntry
    secondary: PortfolioEntry
    passive: tuple[PortfolioEntry, ...] = ()
    previous_state_digest: str | None = None
    schema_version: str = PORTFOLIO_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PORTFOLIO_SCHEMA:
            raise PortfolioStateError("unsupported portfolio state schema")
        _nonempty("portfolio_id", self.portfolio_id)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool):
            raise PortfolioStateError("generation must be an integer")
        if self.generation < 0:
            raise PortfolioStateError("generation cannot be negative")

        if self.active.role != "active":
            raise PortfolioStateError("active slot requires role=active")
        if self.secondary.role != "secondary":
            raise PortfolioStateError("secondary slot requires role=secondary")
        if any(entry.role != "passive" for entry in self.passive):
            raise PortfolioStateError("passive slots require role=passive")

        passive_ids = tuple(entry.work_id for entry in self.passive)
        if passive_ids != tuple(sorted(passive_ids)):
            raise PortfolioStateError(
                "passive entries must be sorted by work_id for canonical state"
            )

        work_ids = (self.active.work_id, self.secondary.work_id, *passive_ids)
        if len(work_ids) != len(set(work_ids)):
            raise PortfolioStateError("portfolio work_id values must be unique")

        if self.generation == 0:
            if self.previous_state_digest is not None:
                raise PortfolioStateError(
                    "generation zero cannot have previous_state_digest"
                )
        else:
            if self.previous_state_digest is None:
                raise PortfolioStateError(
                    "generation > 0 requires previous_state_digest"
                )
            _digest("previous_state_digest", self.previous_state_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def portfolio_state_to_dict(state: PortfolioState) -> dict[str, Any]:
    return asdict(state)


def serialize_portfolio_state(state: PortfolioState) -> str:
    return canonical_json(state)


def _blocker_from_dict(data: Any) -> PortfolioBlocker:
    obj = _require_exact_fields(
        data,
        {"kind", "detail", "evidence_refs", "schema_version"},
        "portfolio blocker",
    )
    evidence_refs = obj["evidence_refs"]
    if not isinstance(evidence_refs, list):
        raise PortfolioStateError("blocker.evidence_refs must be a list")
    try:
        return PortfolioBlocker(
            kind=obj["kind"],
            detail=obj["detail"],
            evidence_refs=tuple(evidence_refs),
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise PortfolioStateError("invalid portfolio blocker") from exc


def _wake_from_dict(data: Any) -> WakeCondition:
    obj = _require_exact_fields(
        data,
        {"kind", "value", "schema_version"},
        "wake condition",
    )
    try:
        return WakeCondition(
            kind=obj["kind"],
            value=obj["value"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise PortfolioStateError("invalid wake condition") from exc


def _entry_from_dict(data: Any) -> PortfolioEntry:
    obj = _require_exact_fields(
        data,
        {
            "work_id",
            "role",
            "state",
            "objective",
            "active_gate",
            "next_action_ref",
            "source_revision",
            "evidence_required",
            "authority_boundary",
            "authority_ref",
            "blockers",
            "wake_condition",
            "checkpoint_ref",
            "schema_version",
        },
        "portfolio entry",
    )

    evidence_required = obj["evidence_required"]
    blockers = obj["blockers"]
    if not isinstance(evidence_required, list):
        raise PortfolioStateError("evidence_required must be a list")
    if not isinstance(blockers, list):
        raise PortfolioStateError("blockers must be a list")

    wake_data = obj["wake_condition"]
    if wake_data is not None and not isinstance(wake_data, dict):
        raise PortfolioStateError("wake_condition must be an object or null")

    try:
        return PortfolioEntry(
            work_id=obj["work_id"],
            role=obj["role"],
            state=obj["state"],
            objective=obj["objective"],
            active_gate=obj["active_gate"],
            next_action_ref=obj["next_action_ref"],
            source_revision=obj["source_revision"],
            evidence_required=tuple(evidence_required),
            authority_boundary=obj["authority_boundary"],
            authority_ref=obj["authority_ref"],
            blockers=tuple(_blocker_from_dict(item) for item in blockers),
            wake_condition=_wake_from_dict(wake_data) if wake_data is not None else None,
            checkpoint_ref=obj["checkpoint_ref"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise PortfolioStateError("invalid portfolio entry") from exc


def portfolio_state_from_dict(data: Any) -> PortfolioState:
    obj = _require_exact_fields(
        data,
        {
            "portfolio_id",
            "generation",
            "active",
            "secondary",
            "passive",
            "previous_state_digest",
            "schema_version",
        },
        "portfolio state",
    )
    passive = obj["passive"]
    if not isinstance(passive, list):
        raise PortfolioStateError("passive must be a list")

    try:
        return PortfolioState(
            portfolio_id=obj["portfolio_id"],
            generation=obj["generation"],
            active=_entry_from_dict(obj["active"]),
            secondary=_entry_from_dict(obj["secondary"]),
            passive=tuple(_entry_from_dict(item) for item in passive),
            previous_state_digest=obj["previous_state_digest"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise PortfolioStateError("invalid portfolio state") from exc


def deserialize_portfolio_state(payload: str) -> PortfolioState:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PortfolioStateError("portfolio state is not valid JSON") from exc
    return portfolio_state_from_dict(data)
