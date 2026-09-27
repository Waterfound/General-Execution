"""Independent verification escalation contracts for Durable Execution Wave 9.

This module is intentionally transport-free. It binds Project Assurance evidence to
an exact durable checkpoint and can prepare policy-bound verification observations
or an optional Red Team advisory escalation. It never executes a tick, integrates
a result, grants repair authority, or dispatches a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest
from .execution_checkpoint import CheckpointEvidence, ExecutionCheckpoint
from .resume_tick import ResumeTickObservation, ResumeTickResult

PROJECT_ASSURANCE_SYSTEM = "project_assurance"
RED_TEAM_SYSTEM = "red_team"

VerificationOutcome = Literal["pass", "reject"]
VerificationDisposition = Literal["verified", "rework_required"]


class VerificationEscalationError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise VerificationEscalationError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise VerificationEscalationError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise VerificationEscalationError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _canonical_strings(name: str, values: tuple[str, ...]) -> None:
    if tuple(sorted(values)) != values:
        raise VerificationEscalationError(f"{name} must be canonical-sorted")
    if len(values) != len(set(values)):
        raise VerificationEscalationError(f"{name} must be unique")
    for value in values:
        _nonempty(name, value)


@dataclass(frozen=True, slots=True)
class IndependentVerificationRequest:
    portfolio_id: str
    generation: int
    state_digest: str
    checkpoint_digest: str
    policy_digest: str
    tick_digest: str
    work_id: str
    source_revision: str
    subject_digest: str
    evidence_digest: str
    executor_id: str
    worker_id: str
    verifier_system: str = PROJECT_ASSURANCE_SYSTEM
    authority_created: bool = False
    self_verification_authorized: bool = False
    integration_authorized: bool = False
    repair_authorized: bool = False
    schema_version: str = "ge.independent-verification-request.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.independent-verification-request.v1":
            raise VerificationEscalationError("unsupported verification request schema")
        if type(self.generation) is not int or self.generation < 0:
            raise VerificationEscalationError("generation must be a non-negative integer")
        for name in (
            "state_digest",
            "checkpoint_digest",
            "policy_digest",
            "tick_digest",
            "subject_digest",
            "evidence_digest",
        ):
            _digest(name, getattr(self, name))
        for name in (
            "portfolio_id",
            "work_id",
            "source_revision",
            "executor_id",
            "worker_id",
        ):
            _nonempty(name, getattr(self, name))
        if self.verifier_system != PROJECT_ASSURANCE_SYSTEM:
            raise VerificationEscalationError("verifier system is protocol-fixed")
        if any(
            value is not False
            for value in (
                self.authority_created,
                self.self_verification_authorized,
                self.integration_authorized,
                self.repair_authorized,
            )
        ):
            raise VerificationEscalationError(
                "verification request cannot create authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def prepare_independent_verification(
    tick: ResumeTickResult,
    checkpoint: ExecutionCheckpoint,
    *,
    policy_digest: str,
    executor_id: str,
    worker_id: str,
    subject_digest: str,
    evidence_digest: str,
) -> IndependentVerificationRequest:
    _digest("policy_digest", policy_digest)
    _digest("subject_digest", subject_digest)
    _digest("evidence_digest", evidence_digest)
    _nonempty("executor_id", executor_id)
    _nonempty("worker_id", worker_id)

    if tick.disposition != "committed":
        raise VerificationEscalationError(
            "independent verification requires a committed tick"
        )
    if tick.checkpoint_digest != checkpoint.digest:
        raise VerificationEscalationError("tick/checkpoint digest mismatch")
    if (
        tick.portfolio_id != checkpoint.portfolio_id
        or tick.post_generation != checkpoint.portfolio_generation
        or tick.post_state_digest != checkpoint.portfolio_state_digest
    ):
        raise VerificationEscalationError(
            "verification request durable provenance mismatch"
        )
    if checkpoint.state_after != "verifying":
        raise VerificationEscalationError(
            "independent verification requires state_after=verifying"
        )

    return IndependentVerificationRequest(
        portfolio_id=checkpoint.portfolio_id,
        generation=checkpoint.portfolio_generation,
        state_digest=checkpoint.portfolio_state_digest,
        checkpoint_digest=checkpoint.digest,
        policy_digest=policy_digest,
        tick_digest=tick.digest,
        work_id=checkpoint.work_id,
        source_revision=checkpoint.source_revision,
        subject_digest=subject_digest,
        evidence_digest=evidence_digest,
        executor_id=executor_id,
        worker_id=worker_id,
    )


@dataclass(frozen=True, slots=True)
class IndependentVerificationResponse:
    request_digest: str
    verifier_system: str
    verifier_id: str
    subject_digest: str
    evidence_digest: str
    outcome: VerificationOutcome
    findings: tuple[str, ...] = ()
    red_team_recommended: bool = False
    integration_authorized: bool = False
    repair_authorized: bool = False
    schema_version: str = "ge.independent-verification-response.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.independent-verification-response.v1":
            raise VerificationEscalationError("unsupported verification response schema")
        for name in ("request_digest", "subject_digest", "evidence_digest"):
            _digest(name, getattr(self, name))
        if self.verifier_system != PROJECT_ASSURANCE_SYSTEM:
            raise VerificationEscalationError("unexpected verifier system")
        _nonempty("verifier_id", self.verifier_id)
        if self.outcome not in {"pass", "reject"}:
            raise VerificationEscalationError("unsupported verification outcome")
        _canonical_strings("findings", self.findings)
        if self.outcome == "reject" and not self.findings:
            raise VerificationEscalationError("rejection requires findings")
        if self.outcome == "pass" and (self.findings or self.red_team_recommended):
            raise VerificationEscalationError(
                "passing verification cannot carry rejection findings or Red Team recommendation"
            )
        if type(self.red_team_recommended) is not bool:
            raise VerificationEscalationError("red_team_recommended must be boolean")
        if self.integration_authorized is not False or self.repair_authorized is not False:
            raise VerificationEscalationError(
                "verification response cannot grant integration or repair authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class VerificationAdmission:
    request_digest: str
    response_digest: str
    subject_digest: str
    verifier_id: str
    evidence_digest: str
    disposition: VerificationDisposition
    self_verified: bool = False
    integration_authorized: bool = False
    repair_authorized: bool = False
    schema_version: str = "ge.verification-admission.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.verification-admission.v1":
            raise VerificationEscalationError("unsupported verification admission schema")
        for name in (
            "request_digest",
            "response_digest",
            "subject_digest",
            "evidence_digest",
        ):
            _digest(name, getattr(self, name))
        _nonempty("verifier_id", self.verifier_id)
        if self.disposition not in {"verified", "rework_required"}:
            raise VerificationEscalationError("unsupported verification disposition")
        if (
            self.self_verified is not False
            or self.integration_authorized is not False
            or self.repair_authorized is not False
        ):
            raise VerificationEscalationError(
                "verification admission cannot create authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def admit_independent_verification(
    request: IndependentVerificationRequest,
    response: IndependentVerificationResponse,
    *,
    authenticated_response_digest: str,
) -> VerificationAdmission:
    _digest("authenticated_response_digest", authenticated_response_digest)
    if authenticated_response_digest != response.digest:
        raise VerificationEscalationError("verification response is not independently admitted")
    if (
        response.request_digest != request.digest
        or response.subject_digest != request.subject_digest
        or response.verifier_system != request.verifier_system
    ):
        raise VerificationEscalationError("verification response provenance mismatch")
    if response.verifier_id in {request.executor_id, request.worker_id}:
        raise VerificationEscalationError("executor or worker cannot self-verify")
    return VerificationAdmission(
        request_digest=request.digest,
        response_digest=response.digest,
        subject_digest=response.subject_digest,
        verifier_id=response.verifier_id,
        evidence_digest=response.evidence_digest,
        disposition="verified" if response.outcome == "pass" else "rework_required",
    )


def build_verification_observation(
    request: IndependentVerificationRequest,
    response: IndependentVerificationResponse,
    admission: VerificationAdmission,
    *,
    observed_at: str,
    summary: str,
) -> ResumeTickObservation:
    _nonempty("observed_at", observed_at)
    _nonempty("summary", summary)
    if (
        admission.request_digest != request.digest
        or admission.response_digest != response.digest
        or admission.subject_digest != request.subject_digest
        or admission.verifier_id != response.verifier_id
        or admission.evidence_digest != response.evidence_digest
    ):
        raise VerificationEscalationError("verification admission binding mismatch")
    expected = "verified" if response.outcome == "pass" else "rework_required"
    if admission.disposition != expected:
        raise VerificationEscalationError("verification admission disposition mismatch")

    passed = response.outcome == "pass"
    evidence = CheckpointEvidence(
        kind="verifier_pass" if passed else "verifier_reject",
        locator=f"verification://{response.verifier_system}/{response.verifier_id}",
        digest=response.evidence_digest,
    )
    return ResumeTickObservation(
        portfolio_id=request.portfolio_id,
        expected_generation=request.generation,
        expected_state_digest=request.state_digest,
        policy_digest=request.policy_digest,
        event="verification_passed" if passed else "verification_failed",
        evidence=(evidence,),
        action_ref=f"verification-admission:{admission.digest}",
        observed_at=observed_at,
        summary=summary,
        canonical_refs=(
            f"verification-request:{request.digest}",
            f"verification-response:{response.digest}",
            f"verification-admission:{admission.digest}",
        ),
    )


@dataclass(frozen=True, slots=True)
class RedTeamEscalationRequest:
    verification_request_digest: str
    verification_response_digest: str
    verification_admission_digest: str
    portfolio_id: str
    generation: int
    state_digest: str
    subject_digest: str
    evidence_digest: str
    executor_id: str
    worker_id: str
    originating_verifier_id: str
    requested_scope_ref: str
    target_system: str = RED_TEAM_SYSTEM
    authority_created: bool = False
    repair_authorized: bool = False
    integration_authorized: bool = False
    transport_authorized: bool = False
    schema_version: str = "ge.red-team-escalation-request.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.red-team-escalation-request.v1":
            raise VerificationEscalationError("unsupported Red Team escalation schema")
        if self.target_system != RED_TEAM_SYSTEM:
            raise VerificationEscalationError("Red Team target is protocol-fixed")
        if type(self.generation) is not int or self.generation < 0:
            raise VerificationEscalationError("generation must be a non-negative integer")
        for name in (
            "verification_request_digest",
            "verification_response_digest",
            "verification_admission_digest",
            "state_digest",
            "subject_digest",
            "evidence_digest",
        ):
            _digest(name, getattr(self, name))
        for name in (
            "portfolio_id",
            "executor_id",
            "worker_id",
            "originating_verifier_id",
            "requested_scope_ref",
        ):
            _nonempty(name, getattr(self, name))
        if any(
            value is not False
            for value in (
                self.authority_created,
                self.repair_authorized,
                self.integration_authorized,
                self.transport_authorized,
            )
        ):
            raise VerificationEscalationError(
                "Red Team escalation request cannot create authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def prepare_red_team_escalation(
    request: IndependentVerificationRequest,
    response: IndependentVerificationResponse,
    admission: VerificationAdmission,
    *,
    requested_scope_ref: str,
) -> RedTeamEscalationRequest:
    _nonempty("requested_scope_ref", requested_scope_ref)
    if response.outcome != "reject" or not response.red_team_recommended:
        raise VerificationEscalationError(
            "Red Team escalation requires a rejected verification with explicit recommendation"
        )
    if (
        response.request_digest != request.digest
        or admission.request_digest != request.digest
        or admission.response_digest != response.digest
        or admission.disposition != "rework_required"
        or admission.verifier_id != response.verifier_id
    ):
        raise VerificationEscalationError("Red Team escalation provenance mismatch")
    return RedTeamEscalationRequest(
        verification_request_digest=request.digest,
        verification_response_digest=response.digest,
        verification_admission_digest=admission.digest,
        portfolio_id=request.portfolio_id,
        generation=request.generation,
        state_digest=request.state_digest,
        subject_digest=request.subject_digest,
        evidence_digest=response.evidence_digest,
        executor_id=request.executor_id,
        worker_id=request.worker_id,
        originating_verifier_id=response.verifier_id,
        requested_scope_ref=requested_scope_ref,
    )


@dataclass(frozen=True, slots=True)
class RedTeamResponse:
    request_digest: str
    responder_id: str
    evidence_digest: str
    available: bool
    findings: tuple[str, ...] = ()
    repair_authorized: bool = False
    integration_authorized: bool = False
    schema_version: str = "ge.red-team-response.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.red-team-response.v1":
            raise VerificationEscalationError("unsupported Red Team response schema")
        _digest("request_digest", self.request_digest)
        _digest("evidence_digest", self.evidence_digest)
        _nonempty("responder_id", self.responder_id)
        if type(self.available) is not bool:
            raise VerificationEscalationError("available must be boolean")
        _canonical_strings("findings", self.findings)
        if self.available and not self.findings:
            raise VerificationEscalationError("available Red Team response requires findings")
        if not self.available and self.findings:
            raise VerificationEscalationError("unavailable Red Team response cannot carry findings")
        if self.repair_authorized is not False or self.integration_authorized is not False:
            raise VerificationEscalationError(
                "Red Team response cannot grant repair or integration authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def admit_red_team_response(
    request: RedTeamEscalationRequest,
    response: RedTeamResponse,
    *,
    authenticated_response_digest: str,
) -> str:
    _digest("authenticated_response_digest", authenticated_response_digest)
    if authenticated_response_digest != response.digest:
        raise VerificationEscalationError("Red Team response is not independently admitted")
    if response.request_digest != request.digest:
        raise VerificationEscalationError("Red Team response provenance mismatch")
    if response.responder_id in {
        request.executor_id,
        request.worker_id,
        request.originating_verifier_id,
    }:
        raise VerificationEscalationError(
            "Red Team responder must be independent of executor, worker, and verifier"
        )
    return "advisory_only" if response.available else "waiting_external"
