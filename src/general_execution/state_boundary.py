from __future__ import annotations

import hashlib
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .canonical import sha256_digest

STATE_BOUNDARY_SCHEMA = "ge.state-boundary.v1"
STATE_RECEIPT_SCHEMA = "ge.state-boundary-receipt.v1"
SEMANTIC_RECEIPT_SCHEMA = "ge.execution-semantic-receipt.v1"
PRESERVATION_SCHEMA = "ge.state-boundary-preservation.v1"

Visibility = Literal["public", "private"]

_OPAQUE_STATE_REF = re.compile(r"^s_[0-9a-f]{16}$")


class StateBoundaryError(ValueError):
    pass


def _digest(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise StateBoundaryError(f"{field} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise StateBoundaryError(f"{field} must contain hexadecimal digest") from exc
    return value


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateBoundaryError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class StateTransportBinding:
    state_ref: str
    storage_visibility: Visibility
    execution_resource_ref: str
    execution_requires_storage_provider: bool = False
    authority_created: bool = False
    schema_version: str = STATE_BOUNDARY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != STATE_BOUNDARY_SCHEMA:
            raise StateBoundaryError("unsupported state-boundary schema")
        if not _OPAQUE_STATE_REF.fullmatch(self.state_ref):
            raise StateBoundaryError("state_ref must be opaque s_<16-hex>")
        if self.storage_visibility not in {"public", "private"}:
            raise StateBoundaryError("unsupported storage visibility")
        _nonempty(self.execution_resource_ref, "execution_resource_ref")
        if self.authority_created:
            raise StateBoundaryError("state transport cannot create authority")


@dataclass(frozen=True, slots=True)
class StateTransportReceipt:
    state_ref: str
    blob_digest: str
    byte_count: int
    storage_visibility: Visibility
    authority_created: bool = False
    schema_version: str = STATE_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != STATE_RECEIPT_SCHEMA:
            raise StateBoundaryError("unsupported state-receipt schema")
        if not _OPAQUE_STATE_REF.fullmatch(self.state_ref):
            raise StateBoundaryError("state_ref must be opaque s_<16-hex>")
        _digest(self.blob_digest, "blob_digest")
        if not isinstance(self.byte_count, int) or isinstance(self.byte_count, bool) or self.byte_count < 0:
            raise StateBoundaryError("byte_count must be a non-negative integer")
        if self.storage_visibility not in {"public", "private"}:
            raise StateBoundaryError("unsupported storage visibility")
        if self.authority_created:
            raise StateBoundaryError("state receipt cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionSemanticReceipt:
    operation: str
    status: str
    pre_generation: int
    post_generation: int
    pre_state_digest: str
    post_state_digest: str
    checkpoint_digest: str | None
    human_required: bool
    requested_action_ref: str | None
    authority_created: bool = False
    schema_version: str = SEMANTIC_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SEMANTIC_RECEIPT_SCHEMA:
            raise StateBoundaryError("unsupported semantic receipt schema")
        _nonempty(self.operation, "operation")
        _nonempty(self.status, "status")
        for field in ("pre_generation", "post_generation"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateBoundaryError(f"{field} must be a non-negative integer")
        _digest(self.pre_state_digest, "pre_state_digest")
        _digest(self.post_state_digest, "post_state_digest")
        if self.checkpoint_digest is not None:
            _digest(self.checkpoint_digest, "checkpoint_digest")
        if self.authority_created:
            raise StateBoundaryError("semantic receipt cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PreservationDecision:
    equivalent: bool
    semantic_fields_equal: bool
    authority_semantics_equal: bool
    evidence_semantics_equal: bool
    storage_execution_decoupled: bool
    baseline_digest: str
    candidate_digest: str
    reasons: tuple[str, ...]
    authority_created: bool = False
    schema_version: str = PRESERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PRESERVATION_SCHEMA:
            raise StateBoundaryError("unsupported preservation schema")
        _digest(self.baseline_digest, "baseline_digest")
        _digest(self.candidate_digest, "candidate_digest")
        if self.authority_created:
            raise StateBoundaryError("preservation decision cannot create authority")


class FilePrivateStateBoundary:
    """Candidate local/private persistence boundary.

    The storage root is intentionally outside the public receipt. This class is a
    pre-cutover proof primitive, not a provider implementation.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    def _path(self, state_ref: str) -> Path:
        if not _OPAQUE_STATE_REF.fullmatch(state_ref):
            raise StateBoundaryError("state_ref must be opaque s_<16-hex>")
        return self.root / f"{state_ref}.bin"

    def persist(self, state_ref: str, blob: bytes) -> StateTransportReceipt:
        if not isinstance(blob, (bytes, bytearray)):
            raise StateBoundaryError("blob must be bytes")
        path = self._path(state_ref)
        path.write_bytes(bytes(blob))
        try:
            path.chmod(0o600)
        except OSError:
            pass
        digest = "sha256:" + hashlib.sha256(bytes(blob)).hexdigest()
        return StateTransportReceipt(
            state_ref=state_ref,
            blob_digest=digest,
            byte_count=len(blob),
            storage_visibility="private",
        )

    def restore(self, receipt: StateTransportReceipt) -> bytes:
        path = self._path(receipt.state_ref)
        blob = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(blob).hexdigest()
        if digest != receipt.blob_digest:
            raise StateBoundaryError("private state blob digest mismatch")
        if len(blob) != receipt.byte_count:
            raise StateBoundaryError("private state blob byte_count mismatch")
        return blob


def semantic_receipt_from_runtime(report: Any) -> ExecutionSemanticReceipt:
    return ExecutionSemanticReceipt(
        operation=report.operation,
        status=report.status,
        pre_generation=report.pre_generation,
        post_generation=report.post_generation,
        pre_state_digest=report.pre_state_digest,
        post_state_digest=report.post_state_digest,
        checkpoint_digest=report.checkpoint_digest,
        human_required=report.human_required,
        requested_action_ref=report.requested_action_ref,
    )


def public_state_receipt(receipt: StateTransportReceipt) -> dict[str, Any]:
    """Minimal public projection. No path, provider, project or state content."""
    return {
        "schema_version": receipt.schema_version,
        "state_ref": receipt.state_ref,
        "blob_digest": receipt.blob_digest,
        "byte_count": receipt.byte_count,
        "storage_visibility": receipt.storage_visibility,
        "authority_created": False,
        "receipt_digest": receipt.digest,
    }


def compare_semantic_preservation(
    baseline: ExecutionSemanticReceipt,
    candidate: ExecutionSemanticReceipt,
    *,
    baseline_binding: StateTransportBinding,
    candidate_binding: StateTransportBinding,
    evidence_predicate_preserved: bool,
) -> PreservationDecision:
    semantic_fields_equal = asdict(baseline) == asdict(candidate)
    authority_semantics_equal = (
        baseline.authority_created == candidate.authority_created == False
        and baseline.human_required == candidate.human_required
        and baseline.requested_action_ref == candidate.requested_action_ref
    )
    evidence_semantics_equal = bool(evidence_predicate_preserved)
    storage_execution_decoupled = (
        not candidate_binding.execution_requires_storage_provider
        and bool(candidate_binding.execution_resource_ref)
    )
    reasons: list[str] = []
    if not semantic_fields_equal:
        reasons.append("semantic_receipt_mismatch")
    if not authority_semantics_equal:
        reasons.append("authority_semantics_mismatch")
    if not evidence_semantics_equal:
        reasons.append("evidence_predicate_weakened")
    if not storage_execution_decoupled:
        reasons.append("storage_compute_coupled")

    equivalent = not reasons
    return PreservationDecision(
        equivalent=equivalent,
        semantic_fields_equal=semantic_fields_equal,
        authority_semantics_equal=authority_semantics_equal,
        evidence_semantics_equal=evidence_semantics_equal,
        storage_execution_decoupled=storage_execution_decoupled,
        baseline_digest=baseline.digest,
        candidate_digest=candidate.digest,
        reasons=tuple(reasons),
    )
