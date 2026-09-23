from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json, sha256_digest
from .portfolio_state import VALID_ROLES, VALID_STATES
from .transition_policy import (
    AdmittedEvidence,
    TransitionDecision,
    TransitionPolicyError,
    transition_decision_from_dict,
)

CANONICAL_REF_SCHEMA = "ge.checkpoint-canonical-ref.v1"
CHECKPOINT_SCHEMA = "ge.execution-checkpoint.v1"


class ExecutionCheckpointError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionCheckpointError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ExecutionCheckpointError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ExecutionCheckpointError(f"{name} must contain 64 hexadecimal characters") from exc


def _unique_nonempty(name: str, values: tuple[str, ...]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ExecutionCheckpointError(f"{name} must contain only non-empty strings")
    if len(values) != len(set(values)):
        raise ExecutionCheckpointError(f"{name} must not contain duplicates")


def _require_exact_fields(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ExecutionCheckpointError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise ExecutionCheckpointError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class CheckpointCanonicalRef:
    name: str
    locator: str
    content_digest: str
    schema_version: str = CANONICAL_REF_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CANONICAL_REF_SCHEMA:
            raise ExecutionCheckpointError("unsupported checkpoint canonical ref schema")
        _nonempty("canonical_ref.name", self.name)
        _nonempty("canonical_ref.locator", self.locator)
        _digest("canonical_ref.content_digest", self.content_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionCheckpoint:
    portfolio_id: str
    portfolio_generation: int
    portfolio_state_digest: str
    work_id: str
    entry_digest: str
    entry_role: str
    entry_state: str
    source_revision: str
    observed_signal: str
    summary: str
    evidence: tuple[AdmittedEvidence, ...]
    canonical_refs: tuple[CheckpointCanonicalRef, ...]
    uncertainties: tuple[str, ...] = ()
    next_transition: TransitionDecision | None = None
    stop_reason: str | None = None
    schema_version: str = CHECKPOINT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CHECKPOINT_SCHEMA:
            raise ExecutionCheckpointError("unsupported execution checkpoint schema")
        for name in ("portfolio_id", "work_id", "source_revision", "observed_signal", "summary"):
            _nonempty(name, getattr(self, name))
        if not isinstance(self.portfolio_generation, int) or isinstance(
            self.portfolio_generation, bool
        ):
            raise ExecutionCheckpointError("portfolio_generation must be an integer")
        if self.portfolio_generation < 0:
            raise ExecutionCheckpointError("portfolio_generation cannot be negative")
        _digest("portfolio_state_digest", self.portfolio_state_digest)
        _digest("entry_digest", self.entry_digest)

        if self.entry_role not in VALID_ROLES:
            raise ExecutionCheckpointError("unsupported checkpoint entry role")
        if self.entry_state not in VALID_STATES:
            raise ExecutionCheckpointError("unsupported checkpoint entry state")

        if not self.evidence:
            raise ExecutionCheckpointError("checkpoint requires admitted evidence")
        evidence_kinds = tuple(item.kind for item in self.evidence)
        if len(evidence_kinds) != len(set(evidence_kinds)):
            raise ExecutionCheckpointError(
                "checkpoint evidence kinds must be unique"
            )

        if not self.canonical_refs:
            raise ExecutionCheckpointError(
                "checkpoint requires at least one canonical reference"
            )
        canonical_names = tuple(item.name for item in self.canonical_refs)
        if len(canonical_names) != len(set(canonical_names)):
            raise ExecutionCheckpointError(
                "checkpoint canonical reference names must be unique"
            )

        _unique_nonempty("uncertainties", self.uncertainties)
        _optional_nonempty("stop_reason", self.stop_reason)

        if (self.next_transition is None) == (self.stop_reason is None):
            raise ExecutionCheckpointError(
                "checkpoint requires exactly one of next_transition or stop_reason"
            )

        if self.next_transition is not None:
            decision = self.next_transition
            if decision.work_id != self.work_id:
                raise ExecutionCheckpointError(
                    "checkpoint transition work_id mismatch"
                )
            if decision.entry_digest != self.entry_digest:
                raise ExecutionCheckpointError(
                    "checkpoint transition entry_digest mismatch"
                )
            if decision.from_role != self.entry_role:
                raise ExecutionCheckpointError(
                    "checkpoint transition role mismatch"
                )
            if decision.from_state != self.entry_state:
                raise ExecutionCheckpointError(
                    "checkpoint transition state mismatch"
                )
            if decision.signal != self.observed_signal:
                raise ExecutionCheckpointError(
                    "checkpoint transition signal mismatch"
                )

            available_evidence = {item.digest for item in self.evidence}
            missing = tuple(
                digest
                for digest in decision.evidence_digests
                if digest not in available_evidence
            )
            if missing:
                raise ExecutionCheckpointError(
                    "checkpoint transition references evidence not preserved in checkpoint"
                )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def execution_checkpoint_to_dict(checkpoint: ExecutionCheckpoint) -> dict[str, Any]:
    return json.loads(canonical_json(checkpoint))


def serialize_execution_checkpoint(checkpoint: ExecutionCheckpoint) -> str:
    return canonical_json(checkpoint)


def _evidence_from_dict(data: Any) -> AdmittedEvidence:
    obj = _require_exact_fields(
        data,
        {"kind", "locator", "content_digest", "schema_version"},
        "checkpoint admitted evidence",
    )
    try:
        return AdmittedEvidence(
            kind=obj["kind"],
            locator=obj["locator"],
            content_digest=obj["content_digest"],
            schema_version=obj["schema_version"],
        )
    except TransitionPolicyError as exc:
        raise ExecutionCheckpointError("invalid checkpoint admitted evidence") from exc


def _canonical_ref_from_dict(data: Any) -> CheckpointCanonicalRef:
    obj = _require_exact_fields(
        data,
        {"name", "locator", "content_digest", "schema_version"},
        "checkpoint canonical ref",
    )
    return CheckpointCanonicalRef(
        name=obj["name"],
        locator=obj["locator"],
        content_digest=obj["content_digest"],
        schema_version=obj["schema_version"],
    )


def execution_checkpoint_from_dict(data: Any) -> ExecutionCheckpoint:
    obj = _require_exact_fields(
        data,
        {
            "portfolio_id",
            "portfolio_generation",
            "portfolio_state_digest",
            "work_id",
            "entry_digest",
            "entry_role",
            "entry_state",
            "source_revision",
            "observed_signal",
            "summary",
            "evidence",
            "canonical_refs",
            "uncertainties",
            "next_transition",
            "stop_reason",
            "schema_version",
        },
        "execution checkpoint",
    )

    evidence = obj["evidence"]
    canonical_refs = obj["canonical_refs"]
    uncertainties = obj["uncertainties"]
    if not isinstance(evidence, list):
        raise ExecutionCheckpointError("checkpoint evidence must be a list")
    if not isinstance(canonical_refs, list):
        raise ExecutionCheckpointError("checkpoint canonical_refs must be a list")
    if not isinstance(uncertainties, list):
        raise ExecutionCheckpointError("checkpoint uncertainties must be a list")

    transition = obj["next_transition"]
    if transition is not None and not isinstance(transition, dict):
        raise ExecutionCheckpointError(
            "checkpoint next_transition must be an object or null"
        )

    try:
        parsed_transition = (
            transition_decision_from_dict(transition)
            if transition is not None
            else None
        )
    except TransitionPolicyError as exc:
        raise ExecutionCheckpointError("invalid checkpoint transition decision") from exc

    return ExecutionCheckpoint(
        portfolio_id=obj["portfolio_id"],
        portfolio_generation=obj["portfolio_generation"],
        portfolio_state_digest=obj["portfolio_state_digest"],
        work_id=obj["work_id"],
        entry_digest=obj["entry_digest"],
        entry_role=obj["entry_role"],
        entry_state=obj["entry_state"],
        source_revision=obj["source_revision"],
        observed_signal=obj["observed_signal"],
        summary=obj["summary"],
        evidence=tuple(_evidence_from_dict(item) for item in evidence),
        canonical_refs=tuple(_canonical_ref_from_dict(item) for item in canonical_refs),
        uncertainties=tuple(uncertainties),
        next_transition=parsed_transition,
        stop_reason=obj["stop_reason"],
        schema_version=obj["schema_version"],
    )


def deserialize_execution_checkpoint(payload: str) -> ExecutionCheckpoint:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExecutionCheckpointError(
            "execution checkpoint is not valid JSON"
        ) from exc
    return execution_checkpoint_from_dict(data)
