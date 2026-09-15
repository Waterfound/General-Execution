from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest, stable_id
from .dispatch import DispatchIntentState, DispatchPermit
from .dispatch_guard import LiveDispatchPermit, verify_live_dispatch_permit
from .durable import SqliteCapacityHeadStore
from .models import RunnerCapabilities
from .reconciliation import ProviderReconciliationContract, ReconciliationDecision

EnvironmentScope = Literal["sandbox", "production_equivalent"]
ConformanceCaseId = Literal[
    "same_request_semantics",
    "different_request_rejection",
    "lookup_identity_binding",
    "absence_semantics",
    "terminal_evidence_binding",
]

CASE_SCHEMA = "ge.provider-conformance-case.v1"
EVIDENCE_SCHEMA = "ge.provider-conformance-evidence.v1"
ATTESTATION_SCHEMA = "ge.provider-contract-attestation.v1"
RESUBMIT_PERMIT_SCHEMA = "ge.attested-resubmission-permit.v1"
SUITE_VERSION = "ge.provider-reconciliation-conformance.v1"

REVISION = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
SHA256 = re.compile(r"^sha256:[a-f0-9]{64}$")

MANDATORY_CASES = frozenset(
    {
        "same_request_semantics",
        "different_request_rejection",
        "lookup_identity_binding",
        "absence_semantics",
    }
)
ALLOWED_CASES = MANDATORY_CASES | {"terminal_evidence_binding"}


class ConformanceError(ValueError):
    pass


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"{name} must be sha256:<64-lowercase-hex>")


def _revision(name: str, value: str) -> None:
    if not isinstance(value, str) or not REVISION.fullmatch(value):
        raise ValueError(f"{name} must be an immutable 40- or 64-hex revision")


@dataclass(frozen=True, slots=True)
class ProviderConformanceCaseResult:
    case_id: ConformanceCaseId
    passed: bool
    evidence_digest: str
    detail: str = ""
    schema_version: str = CASE_SCHEMA

    def __post_init__(self) -> None:
        if self.case_id not in ALLOWED_CASES:
            raise ValueError("unsupported provider conformance case")
        _digest("evidence_digest", self.evidence_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderConformanceEvidence:
    contract_digest: str
    adapter_revision: str
    environment_scope: EnvironmentScope
    cases: tuple[ProviderConformanceCaseResult, ...]
    suite_version: str = SUITE_VERSION
    schema_version: str = EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        _digest("contract_digest", self.contract_digest)
        _revision("adapter_revision", self.adapter_revision)
        if self.environment_scope not in {"sandbox", "production_equivalent"}:
            raise ValueError("unsupported conformance environment scope")
        if self.suite_version != SUITE_VERSION:
            raise ValueError("unsupported provider conformance suite version")
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("provider conformance cases must be unique")
        if any(case_id not in ALLOWED_CASES for case_id in ids):
            raise ValueError("provider conformance evidence contains unknown case")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderContractAttestation:
    contract_digest: str
    adapter_revision: str
    conformance_evidence_digest: str
    environment_scope: EnvironmentScope
    passed_cases: tuple[str, ...]
    failed_cases: tuple[str, ...]
    contract_conformant: bool
    safe_resubmission_certified: bool
    terminal_evidence_certified: bool
    authority: str = "NONE"
    suite_version: str = SUITE_VERSION
    schema_version: str = ATTESTATION_SCHEMA

    def __post_init__(self) -> None:
        _digest("contract_digest", self.contract_digest)
        _digest("conformance_evidence_digest", self.conformance_evidence_digest)
        _revision("adapter_revision", self.adapter_revision)
        if self.environment_scope not in {"sandbox", "production_equivalent"}:
            raise ValueError("unsupported attestation environment scope")
        if self.authority != "NONE":
            raise ValueError("provider conformance attestation cannot create project authority")
        if self.suite_version != SUITE_VERSION:
            raise ValueError("unsupported attestation suite version")
        passed = set(self.passed_cases)
        failed = set(self.failed_cases)
        if passed & failed:
            raise ValueError("conformance case cannot be both passed and failed")
        if not (passed | failed).issubset(ALLOWED_CASES):
            raise ValueError("attestation contains unknown conformance case")
        if len(self.passed_cases) != len(passed) or len(self.failed_cases) != len(failed):
            raise ValueError("attestation conformance cases must be unique")
        if self.contract_conformant and self.failed_cases:
            raise ValueError("conformant attestation cannot contain failed required cases")
        if self.safe_resubmission_certified and (
            not self.contract_conformant or self.environment_scope != "production_equivalent"
        ):
            raise ValueError("safe resubmission certification requires production-equivalent conformance")
        if self.terminal_evidence_certified and self.environment_scope != "production_equivalent":
            raise ValueError("terminal evidence certification requires production-equivalent conformance")

    @property
    def attestation_id(self) -> str:
        return stable_id("gepca", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AttestedResubmissionPermit:
    decision_digest: str
    reconciliation_evidence_digest: str
    contract_digest: str
    attestation_digest: str
    conformance_evidence_digest: str
    live_permit_digest: str
    adapter_revision: str
    invocation_id: str
    request_digest: str
    authority: str = "IDEMPOTENT_RESUBMIT_ONLY"
    new_physical_attempt_authorized: bool = False
    schema_version: str = RESUBMIT_PERMIT_SCHEMA

    def __post_init__(self) -> None:
        for name in (
            "decision_digest",
            "reconciliation_evidence_digest",
            "contract_digest",
            "attestation_digest",
            "conformance_evidence_digest",
            "live_permit_digest",
            "request_digest",
        ):
            _digest(name, getattr(self, name))
        _revision("adapter_revision", self.adapter_revision)
        if not self.invocation_id or not self.invocation_id.strip():
            raise ValueError("invocation_id must be non-empty")
        if self.authority != "IDEMPOTENT_RESUBMIT_ONLY":
            raise ValueError("attested permit authority is limited to same-invocation idempotent resubmission")
        if self.new_physical_attempt_authorized:
            raise ValueError("attested resubmission cannot authorize a new physical attempt")

    @property
    def permit_id(self) -> str:
        return stable_id("gearp", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _case_map(evidence: ProviderConformanceEvidence) -> dict[str, ProviderConformanceCaseResult]:
    return {case.case_id: case for case in evidence.cases}


def attest_provider_contract(
    contract: ProviderReconciliationContract,
    evidence: ProviderConformanceEvidence,
) -> ProviderContractAttestation:
    if evidence.contract_digest != contract.digest:
        raise ConformanceError("conformance evidence contract digest mismatch")
    cases = _case_map(evidence)
    required = set(MANDATORY_CASES)
    if contract.terminal_evidence_lookup:
        required.add("terminal_evidence_binding")
    missing = sorted(required - set(cases))
    if missing:
        raise ConformanceError(f"missing required conformance cases: {','.join(missing)}")

    considered = sorted(required)
    passed = tuple(case_id for case_id in considered if cases[case_id].passed)
    failed = tuple(case_id for case_id in considered if not cases[case_id].passed)
    contract_conformant = not failed
    production_equivalent = evidence.environment_scope == "production_equivalent"
    safe_resubmission_certified = (
        contract_conformant
        and production_equivalent
        and contract.safe_idempotent_resubmission
    )
    terminal_evidence_certified = (
        contract.terminal_evidence_lookup
        and production_equivalent
        and cases["terminal_evidence_binding"].passed
    )
    return ProviderContractAttestation(
        contract_digest=contract.digest,
        adapter_revision=evidence.adapter_revision,
        conformance_evidence_digest=evidence.digest,
        environment_scope=evidence.environment_scope,
        passed_cases=passed,
        failed_cases=failed,
        contract_conformant=contract_conformant,
        safe_resubmission_certified=safe_resubmission_certified,
        terminal_evidence_certified=terminal_evidence_certified,
    )


def verify_provider_attestation(
    contract: ProviderReconciliationContract,
    evidence: ProviderConformanceEvidence,
    attestation: ProviderContractAttestation,
    adapter_revision: str,
    *,
    require_safe_resubmission: bool = False,
) -> bool:
    try:
        _revision("adapter_revision", adapter_revision)
        expected = attest_provider_contract(contract, evidence)
    except (ConformanceError, ValueError):
        return False
    if evidence.adapter_revision != adapter_revision or attestation != expected:
        return False
    if require_safe_resubmission and not attestation.safe_resubmission_certified:
        return False
    return True


def authorize_attested_resubmission(
    decision: ReconciliationDecision,
    contract: ProviderReconciliationContract,
    evidence: ProviderConformanceEvidence,
    attestation: ProviderContractAttestation,
    *,
    adapter_revision: str,
    dispatch_state: DispatchIntentState,
    dispatch_permit: DispatchPermit,
    live_permit: LiveDispatchPermit,
    capacity_store: SqliteCapacityHeadStore,
    runner: RunnerCapabilities,
) -> AttestedResubmissionPermit:
    if (
        decision.action != "resubmit_same_invocation"
        or not decision.resubmit_authorized
        or not decision.requires_fresh_live_permit
    ):
        raise ConformanceError("reconciliation decision does not authorize same-invocation resubmission")
    if decision.contract_digest != contract.digest:
        raise ConformanceError("reconciliation decision contract binding mismatch")
    if decision.live_permit_digest != live_permit.digest:
        raise ConformanceError("reconciliation decision live permit binding mismatch")
    if (
        decision.invocation_id != dispatch_state.intent.invocation_id
        or decision.request_digest != dispatch_state.intent.request_digest
    ):
        raise ConformanceError("reconciliation decision invocation binding mismatch")
    if not verify_provider_attestation(
        contract,
        evidence,
        attestation,
        adapter_revision,
        require_safe_resubmission=True,
    ):
        raise ConformanceError("provider contract lacks production-equivalent safe-resubmission attestation")
    if not verify_live_dispatch_permit(
        dispatch_state,
        dispatch_permit,
        live_permit,
        capacity_store,
        runner,
    ):
        raise ConformanceError("live dispatch permit is stale or invalid at attested resubmission gate")

    return AttestedResubmissionPermit(
        decision_digest=decision.digest,
        reconciliation_evidence_digest=decision.evidence_digest,
        contract_digest=contract.digest,
        attestation_digest=attestation.digest,
        conformance_evidence_digest=evidence.digest,
        live_permit_digest=live_permit.digest,
        adapter_revision=adapter_revision,
        invocation_id=decision.invocation_id,
        request_digest=decision.request_digest,
    )


def verify_attested_resubmission_permit(
    permit: AttestedResubmissionPermit,
    decision: ReconciliationDecision,
    contract: ProviderReconciliationContract,
    evidence: ProviderConformanceEvidence,
    attestation: ProviderContractAttestation,
    *,
    adapter_revision: str,
    dispatch_state: DispatchIntentState,
    dispatch_permit: DispatchPermit,
    live_permit: LiveDispatchPermit,
    capacity_store: SqliteCapacityHeadStore,
    runner: RunnerCapabilities,
) -> bool:
    try:
        expected = authorize_attested_resubmission(
            decision,
            contract,
            evidence,
            attestation,
            adapter_revision=adapter_revision,
            dispatch_state=dispatch_state,
            dispatch_permit=dispatch_permit,
            live_permit=live_permit,
            capacity_store=capacity_store,
            runner=runner,
        )
    except (ConformanceError, ValueError):
        return False
    return permit == expected
