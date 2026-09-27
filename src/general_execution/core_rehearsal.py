from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_digest

CORE_REHEARSAL_ASSERTION_SCHEMA = "ge.core-rehearsal-assertion.v1"
CORE_REHEARSAL_REPORT_SCHEMA = "ge.core-rehearsal-report.v1"

REQUIRED_CORE1_ASSERTIONS = (
    "bounded_retry",
    "checkpoint_reconstruction",
    "cold_resume",
    "cost_security_authority_stop",
    "duplicate_tick_idempotent",
    "external_blocker_parking",
    "human_gate_stop",
    "no_chat_dependency",
    "no_hidden_authority",
    "passive_wake_admission",
    "stale_write_rejected",
    "unknown_failure_single_reproduction",
    "verified_secondary_promotion",
)


class CoreRehearsalError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CoreRehearsalError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise CoreRehearsalError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise CoreRehearsalError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _commit_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise CoreRehearsalError(f"{name} must be a 40-character commit SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CoreRehearsalError(f"{name} must be hexadecimal") from exc


@dataclass(frozen=True, slots=True)
class CoreRehearsalAssertion:
    assertion_id: str
    passed: bool
    evidence_refs: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    schema_version: str = CORE_REHEARSAL_ASSERTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CORE_REHEARSAL_ASSERTION_SCHEMA:
            raise CoreRehearsalError(
                "unsupported core rehearsal assertion schema"
            )
        if self.assertion_id not in REQUIRED_CORE1_ASSERTIONS:
            raise CoreRehearsalError("unsupported CORE-1 assertion id")
        if not isinstance(self.passed, bool):
            raise CoreRehearsalError("assertion passed must be boolean")
        if not self.evidence_refs:
            raise CoreRehearsalError("CORE-1 assertion requires evidence refs")
        if not self.evidence_digests:
            raise CoreRehearsalError(
                "CORE-1 assertion requires evidence digests"
            )
        if tuple(sorted(self.evidence_refs)) != self.evidence_refs:
            raise CoreRehearsalError(
                "CORE-1 assertion evidence refs must be canonical-sorted"
            )
        if tuple(sorted(self.evidence_digests)) != self.evidence_digests:
            raise CoreRehearsalError(
                "CORE-1 assertion evidence digests must be canonical-sorted"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise CoreRehearsalError(
                "CORE-1 assertion evidence refs must be unique"
            )
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise CoreRehearsalError(
                "CORE-1 assertion evidence digests must be unique"
            )
        for value in self.evidence_refs:
            _nonempty("evidence_ref", value)
        for value in self.evidence_digests:
            _digest("evidence_digest", value)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CoreRehearsalReport:
    candidate_revision: str
    core_verification_receipt_digest: str
    assertions: tuple[CoreRehearsalAssertion, ...]
    all_passed: bool
    chat_context_required: bool = False
    unattended_runtime_enabled: bool = False
    schema_version: str = CORE_REHEARSAL_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CORE_REHEARSAL_REPORT_SCHEMA:
            raise CoreRehearsalError(
                "unsupported core rehearsal report schema"
            )
        _commit_sha("candidate_revision", self.candidate_revision)
        _digest(
            "core_verification_receipt_digest",
            self.core_verification_receipt_digest,
        )
        if not isinstance(self.all_passed, bool):
            raise CoreRehearsalError("all_passed must be boolean")
        if not isinstance(self.chat_context_required, bool):
            raise CoreRehearsalError("chat_context_required must be boolean")
        if not isinstance(self.unattended_runtime_enabled, bool):
            raise CoreRehearsalError(
                "unattended_runtime_enabled must be boolean"
            )
        if self.chat_context_required:
            raise CoreRehearsalError(
                "CORE-1 cannot depend on chat context"
            )
        if self.unattended_runtime_enabled:
            raise CoreRehearsalError(
                "CORE-1 evidence cannot enable unattended runtime"
            )

        ids = tuple(item.assertion_id for item in self.assertions)
        if ids != tuple(sorted(ids)):
            raise CoreRehearsalError(
                "CORE-1 assertions must be canonical-sorted"
            )
        if len(ids) != len(set(ids)):
            raise CoreRehearsalError(
                "CORE-1 assertion ids must be unique"
            )
        if set(ids) != set(REQUIRED_CORE1_ASSERTIONS):
            missing = sorted(set(REQUIRED_CORE1_ASSERTIONS) - set(ids))
            extra = sorted(set(ids) - set(REQUIRED_CORE1_ASSERTIONS))
            raise CoreRehearsalError(
                f"CORE-1 assertion set mismatch: missing={missing} extra={extra}"
            )

        expected_all_passed = all(item.passed for item in self.assertions)
        if self.all_passed != expected_all_passed:
            raise CoreRehearsalError(
                "all_passed does not match CORE-1 assertion evidence"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def build_core_rehearsal_report(
    candidate_revision: str,
    core_verification_receipt_digest: str,
    assertions: tuple[CoreRehearsalAssertion, ...],
) -> CoreRehearsalReport:
    canonical_assertions = tuple(
        sorted(assertions, key=lambda item: item.assertion_id)
    )
    return CoreRehearsalReport(
        candidate_revision=candidate_revision,
        core_verification_receipt_digest=core_verification_receipt_digest,
        assertions=canonical_assertions,
        all_passed=all(item.passed for item in canonical_assertions),
    )
