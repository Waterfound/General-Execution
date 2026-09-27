from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id

CHECKPOINT_SCHEMA = "ge.execution-checkpoint.v1"
CHECKPOINT_EVIDENCE_SCHEMA = "ge.checkpoint-evidence.v1"

CheckpointRole = Literal["active", "secondary", "passive"]
CheckpointState = Literal[
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
TERMINAL_WITHOUT_NEXT = {"complete", "failed"}


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
        raise ExecutionCheckpointError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


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
            f"{label} fields mismatch: missing={sorted(expected - actual)} "
            f"unknown={sorted(actual - expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class CheckpointEvidence:
    kind: str
    locator: str
    digest: str
    schema_version: str = CHECKPOINT_EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CHECKPOINT_EVIDENCE_SCHEMA:
            raise ExecutionCheckpointError("unsupported checkpoint evidence schema")
        _nonempty("evidence.kind", self.kind)
        _nonempty("evidence.locator", self.locator)
        _digest("evidence.digest", self.digest)

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.kind, self.locator, self.digest)

    @property
    def evidence_digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionCheckpoint:
    portfolio_id: str
    portfolio_generation: int
    portfolio_state_digest: str
    work_id: str
    role: CheckpointRole
    state_before: CheckpointState
    state_after: CheckpointState
    action_ref: str
    source_revision: str
    observed_at: str
    summary: str
    evidence: tuple[CheckpointEvidence, ...]
    canonical_refs: tuple[str, ...]
    uncertainties: tuple[str, ...] = ()
    next_transition_refs: tuple[str, ...] = ()
    authority_stop: bool = False
    authority_boundary: str | None = None
    schema_version: str = CHECKPOINT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CHECKPOINT_SCHEMA:
            raise ExecutionCheckpointError("unsupported execution checkpoint schema")
        for name in (
            "portfolio_id",
            "work_id",
            "action_ref",
            "source_revision",
            "observed_at",
            "summary",
        ):
            _nonempty(name, getattr(self, name))

        if not isinstance(self.portfolio_generation, int) or isinstance(
            self.portfolio_generation, bool
        ):
            raise ExecutionCheckpointError("portfolio_generation must be an integer")
        if self.portfolio_generation < 0:
            raise ExecutionCheckpointError("portfolio_generation cannot be negative")

        _digest("portfolio_state_digest", self.portfolio_state_digest)

        if self.role not in VALID_ROLES:
            raise ExecutionCheckpointError("unsupported checkpoint role")
        if self.state_before not in VALID_STATES or self.state_after not in VALID_STATES:
            raise ExecutionCheckpointError("unsupported checkpoint state")

        if not self.evidence:
            raise ExecutionCheckpointError("checkpoint requires admitted evidence")
        evidence_ids = tuple(item.identity for item in self.evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ExecutionCheckpointError("checkpoint evidence must not contain duplicates")

        _unique_nonempty("canonical_refs", self.canonical_refs)
        if not self.canonical_refs:
            raise ExecutionCheckpointError("checkpoint requires at least one canonical_ref")
        _unique_nonempty("uncertainties", self.uncertainties)
        _unique_nonempty("next_transition_refs", self.next_transition_refs)

        if self.authority_stop:
            if not self.authority_boundary:
                raise ExecutionCheckpointError(
                    "authority_stop requires authority_boundary"
                )
            if self.state_after != "human_gate":
                raise ExecutionCheckpointError(
                    "authority_stop requires state_after=human_gate"
                )
            if self.next_transition_refs:
                raise ExecutionCheckpointError(
                    "authority_stop cannot declare automatic next transitions"
                )
        else:
            if self.authority_boundary is not None:
                raise ExecutionCheckpointError(
                    "authority_boundary is valid only for authority_stop"
                )
            if (
                not self.next_transition_refs
                and self.state_after not in TERMINAL_WITHOUT_NEXT
            ):
                raise ExecutionCheckpointError(
                    "nonterminal checkpoint requires next_transition_refs"
                )

        if self.role == "passive" and self.state_after != "passive":
            raise ExecutionCheckpointError(
                "passive checkpoint cannot claim non-passive state"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def checkpoint_id(self) -> str:
        return stable_id("gec", self)


def checkpoint_to_dict(checkpoint: ExecutionCheckpoint) -> dict[str, Any]:
    return json.loads(canonical_json(checkpoint))


def serialize_checkpoint(checkpoint: ExecutionCheckpoint) -> str:
    return canonical_json(checkpoint)


def _evidence_from_dict(data: Any) -> CheckpointEvidence:
    obj = _require_exact_fields(
        data,
        {"kind", "locator", "digest", "schema_version"},
        "checkpoint evidence",
    )
    try:
        return CheckpointEvidence(**obj)
    except (TypeError, KeyError) as exc:
        raise ExecutionCheckpointError("invalid checkpoint evidence") from exc


def checkpoint_from_dict(data: Any) -> ExecutionCheckpoint:
    obj = _require_exact_fields(
        data,
        {
            "portfolio_id",
            "portfolio_generation",
            "portfolio_state_digest",
            "work_id",
            "role",
            "state_before",
            "state_after",
            "action_ref",
            "source_revision",
            "observed_at",
            "summary",
            "evidence",
            "canonical_refs",
            "uncertainties",
            "next_transition_refs",
            "authority_stop",
            "authority_boundary",
            "schema_version",
        },
        "execution checkpoint",
    )
    for field in ("evidence", "canonical_refs", "uncertainties", "next_transition_refs"):
        if not isinstance(obj[field], list):
            raise ExecutionCheckpointError(f"{field} must be a list")
    try:
        return ExecutionCheckpoint(
            portfolio_id=obj["portfolio_id"],
            portfolio_generation=obj["portfolio_generation"],
            portfolio_state_digest=obj["portfolio_state_digest"],
            work_id=obj["work_id"],
            role=obj["role"],
            state_before=obj["state_before"],
            state_after=obj["state_after"],
            action_ref=obj["action_ref"],
            source_revision=obj["source_revision"],
            observed_at=obj["observed_at"],
            summary=obj["summary"],
            evidence=tuple(_evidence_from_dict(item) for item in obj["evidence"]),
            canonical_refs=tuple(obj["canonical_refs"]),
            uncertainties=tuple(obj["uncertainties"]),
            next_transition_refs=tuple(obj["next_transition_refs"]),
            authority_stop=obj["authority_stop"],
            authority_boundary=obj["authority_boundary"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise ExecutionCheckpointError("invalid execution checkpoint") from exc


def deserialize_checkpoint(payload: str) -> ExecutionCheckpoint:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExecutionCheckpointError("execution checkpoint is not valid JSON") from exc
    return checkpoint_from_dict(data)
