from dataclasses import replace

import pytest

from general_execution import ProviderReconciliationContract, attest_provider_contract
from general_execution.conformance_harness import (
    ConformanceHarnessError,
    ConformanceLookupResult,
    ReferenceConformanceTarget,
    run_provider_conformance,
)

D = "sha256:" + "d" * 64
REVISION = "a" * 40


def contract(**overrides):
    value = ProviderReconciliationContract(
        provider="reference-provider",
        adapter="reference-adapter",
        adapter_version="1",
    )
    return replace(value, **overrides) if overrides else value


def case_map(evidence):
    return {case.case_id: case for case in evidence.cases}


class WrongIdentityTarget(ReferenceConformanceTarget):
    provider = "other-provider"


class BrokenLookupBindingTarget(ReferenceConformanceTarget):
    def lookup(self, invocation_id, request_digest):
        result = super().lookup(invocation_id, request_digest)
        if result.status == "identity_mismatch":
            return ConformanceLookupResult(
                invocation_id=result.invocation_id,
                request_digest=result.request_digest,
                status="absent",
                provider_invocation_id=None,
                terminal_evidence_digest=None,
                evidence_digest=result.evidence_digest,
            )
        return result


class BrokenAbsenceTarget(ReferenceConformanceTarget):
    def lookup(self, invocation_id, request_digest):
        result = super().lookup(invocation_id, request_digest)
        if result.status == "accepted":
            return ConformanceLookupResult(
                invocation_id=result.invocation_id,
                request_digest=result.request_digest,
                status="absent",
                provider_invocation_id=None,
                terminal_evidence_digest=None,
                evidence_digest=result.evidence_digest,
            )
        return result


class BrokenTerminalTarget(ReferenceConformanceTarget):
    def mark_terminal(self, invocation_id, request_digest, terminal_evidence_digest):
        return None


def test_reference_target_generates_mechanical_sandbox_evidence():
    target = ReferenceConformanceTarget(adapter_revision=REVISION)
    evidence, run = run_provider_conformance(contract(), target)
    assert evidence.environment_scope == "sandbox"
    assert evidence.adapter_revision == REVISION
    assert run.environment_scope == "sandbox"
    assert run.conformance_evidence_digest == evidence.digest
    assert run.all_required_cases_passed is True
    assert all(case.passed for case in evidence.cases)
    attestation = attest_provider_contract(contract(), evidence)
    assert attestation.contract_conformant is True
    assert attestation.safe_resubmission_certified is False


def test_reference_harness_is_semantically_deterministic_across_clean_runs():
    target = ReferenceConformanceTarget(adapter_revision=REVISION)
    evidence_a, run_a = run_provider_conformance(contract(), target)
    evidence_b, run_b = run_provider_conformance(contract(), target)
    assert evidence_a == evidence_b
    assert evidence_a.digest == evidence_b.digest
    assert run_a == run_b
    assert run_a.digest == run_b.digest


def test_declared_same_operation_fails_when_target_rejects_duplicate():
    target = ReferenceConformanceTarget(
        adapter_revision=REVISION,
        same_key_same_request="duplicate_rejected",
    )
    evidence, run = run_provider_conformance(contract(same_key_same_request="same_operation"), target)
    cases = case_map(evidence)
    assert cases["same_request_semantics"].passed is False
    assert run.all_required_cases_passed is False
    attestation = attest_provider_contract(contract(same_key_same_request="same_operation"), evidence)
    assert attestation.contract_conformant is False


def test_matching_duplicate_rejected_semantics_passes():
    target = ReferenceConformanceTarget(
        adapter_revision=REVISION,
        same_key_same_request="duplicate_rejected",
    )
    c = contract(same_key_same_request="duplicate_rejected")
    evidence, run = run_provider_conformance(c, target)
    assert case_map(evidence)["same_request_semantics"].passed is True
    assert run.all_required_cases_passed is True


def test_may_duplicate_can_conform_but_never_be_safe_resubmission_contract():
    target = ReferenceConformanceTarget(
        adapter_revision=REVISION,
        same_key_same_request="may_duplicate",
    )
    c = contract(same_key_same_request="may_duplicate")
    evidence, run = run_provider_conformance(c, target)
    assert run.all_required_cases_passed is True
    attestation = attest_provider_contract(c, evidence)
    assert attestation.contract_conformant is True
    assert c.safe_idempotent_resubmission is False
    assert attestation.safe_resubmission_certified is False


def test_target_identity_mismatch_is_rejected_before_cases_run():
    target = WrongIdentityTarget(adapter_revision=REVISION)
    with pytest.raises(ConformanceHarnessError, match="identity does not match"):
        run_provider_conformance(contract(), target)


def test_malformed_adapter_revision_is_rejected_at_target_boundary():
    with pytest.raises(ValueError, match="adapter_revision"):
        ReferenceConformanceTarget(adapter_revision="not-a-revision")


def test_lookup_identity_violation_is_detected_as_failed_case():
    target = BrokenLookupBindingTarget(adapter_revision=REVISION)
    evidence, run = run_provider_conformance(contract(), target)
    assert case_map(evidence)["lookup_identity_binding"].passed is False
    assert run.all_required_cases_passed is False


def test_absence_semantics_violation_is_detected():
    target = BrokenAbsenceTarget(adapter_revision=REVISION)
    evidence, _ = run_provider_conformance(contract(), target)
    assert case_map(evidence)["absence_semantics"].passed is False


def test_terminal_evidence_violation_is_detected():
    target = BrokenTerminalTarget(adapter_revision=REVISION)
    evidence, _ = run_provider_conformance(contract(), target)
    assert case_map(evidence)["terminal_evidence_binding"].passed is False


def test_terminal_case_is_not_run_when_contract_does_not_claim_capability():
    c = contract(terminal_evidence_lookup=False)
    target = ReferenceConformanceTarget(adapter_revision=REVISION)
    evidence, run = run_provider_conformance(c, target)
    assert "terminal_evidence_binding" not in case_map(evidence)
    assert len(evidence.cases) == 4
    assert run.all_required_cases_passed is True


def test_distinct_request_digests_are_required():
    target = ReferenceConformanceTarget(adapter_revision=REVISION)
    with pytest.raises(ConformanceHarnessError, match="distinct digests"):
        run_provider_conformance(
            contract(),
            target,
            request_digest=D,
            different_request_digest=D,
        )
