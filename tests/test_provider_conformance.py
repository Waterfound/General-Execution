from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    ProviderReconciliationContract,
    ProviderReconciliationObservation,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    SqliteDispatchIntentStore,
    admit_reconciliation_observation,
    authorize_live_dispatch,
    authorize_physical_attempt,
    bind_session,
    create_reconciliation_query,
    decide_reconciliation,
    initialize_capacity_state,
    plan_execution,
    prepare_dispatch_intent,
    reference_runner,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.conformance import (
    AttestedResubmissionPermit,
    ConformanceError,
    ProviderConformanceCaseResult,
    ProviderConformanceEvidence,
    ProviderContractAttestation,
    attest_provider_contract,
    authorize_attested_resubmission,
    verify_attested_resubmission_permit,
    verify_provider_attestation,
)

D = "sha256:" + "d" * 64
E = "sha256:" + "e" * 64
F = "sha256:" + "f" * 64
ADAPTER_REVISION = "a" * 40
OTHER_REVISION = "b" * 40


def runtime_context(tmp_path, suffix="base", contract_override=None):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-provider-attestation",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Provider conformance {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://provider-attestation/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-{suffix}-1",
    )

    genesis = initialize_capacity_state(runner)
    capacity_state, grant, _ = reserve_capacity(
        genesis,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    capacity_store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    capacity_store.initialize(runner, genesis)
    capacity_store.commit(runner, genesis.digest, capacity_state)

    intent = prepare_dispatch_intent(capacity_state, runner, grant.lease, authorization)
    dispatch_store = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    prepared = dispatch_store.initialize(intent)
    unknown, dispatch_permit = dispatch_store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    live_permit = authorize_live_dispatch(
        unknown,
        dispatch_permit,
        capacity_store,
        runner,
    )

    contract = ProviderReconciliationContract(
        provider=authorization.request.provider,
        adapter=authorization.request.adapter,
        adapter_version=authorization.request.adapter_version,
    )
    if contract_override is not None:
        contract = contract_override(contract)

    query = create_reconciliation_query(
        unknown,
        dispatch_permit,
        authorization,
        contract,
    )
    observation = ProviderReconciliationObservation(
        query_digest=query.digest,
        invocation_id=query.invocation_id,
        request_digest=query.request_digest,
        provider=query.provider,
        adapter=query.adapter,
        adapter_version=query.adapter_version,
        status="absent",
        evidence_digest=E,
    )
    reconciliation_evidence = admit_reconciliation_observation(
        query,
        contract,
        observation,
    )
    decision = decide_reconciliation(
        unknown,
        dispatch_permit,
        authorization,
        contract,
        reconciliation_evidence,
        live_permit=live_permit,
        capacity_store=capacity_store,
        runner=runner,
    )
    return {
        "runner": runner,
        "spec": spec,
        "registry": registry,
        "plan": plan,
        "session": session,
        "authorization": authorization,
        "capacity_state": capacity_state,
        "capacity_store": capacity_store,
        "grant": grant,
        "dispatch_store": dispatch_store,
        "unknown": unknown,
        "dispatch_permit": dispatch_permit,
        "live_permit": live_permit,
        "contract": contract,
        "reconciliation_evidence": reconciliation_evidence,
        "decision": decision,
    }


def case(case_id, passed=True, digest=F):
    return ProviderConformanceCaseResult(
        case_id=case_id,
        passed=passed,
        evidence_digest=digest,
    )


def all_cases(*, terminal=True, failed=None):
    failed = set(failed or ())
    ids = [
        "same_request_semantics",
        "different_request_rejection",
        "lookup_identity_binding",
        "absence_semantics",
    ]
    if terminal:
        ids.append("terminal_evidence_binding")
    return tuple(case(case_id, passed=case_id not in failed) for case_id in ids)


def conformance_evidence(contract, *, scope="production_equivalent", cases=None, revision=ADAPTER_REVISION):
    return ProviderConformanceEvidence(
        contract_digest=contract.digest,
        adapter_revision=revision,
        environment_scope=scope,
        cases=cases if cases is not None else all_cases(terminal=contract.terminal_evidence_lookup),
    )


def attested_args(context, evidence, attestation):
    return dict(
        decision=context["decision"],
        contract=context["contract"],
        evidence=evidence,
        attestation=attestation,
        adapter_revision=ADAPTER_REVISION,
        dispatch_state=context["unknown"],
        dispatch_permit=context["dispatch_permit"],
        live_permit=context["live_permit"],
        capacity_store=context["capacity_store"],
        runner=context["runner"],
    )


def test_production_equivalent_all_required_cases_certifies_safe_resubmission(tmp_path):
    context = runtime_context(tmp_path, "prod-pass")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    assert attestation.contract_conformant is True
    assert attestation.safe_resubmission_certified is True
    assert attestation.terminal_evidence_certified is True
    assert attestation.authority == "NONE"
    assert verify_provider_attestation(
        context["contract"],
        evidence,
        attestation,
        ADAPTER_REVISION,
        require_safe_resubmission=True,
    )


def test_sandbox_can_be_conformant_but_cannot_certify_safe_resubmission(tmp_path):
    context = runtime_context(tmp_path, "sandbox")
    evidence = conformance_evidence(context["contract"], scope="sandbox")
    attestation = attest_provider_contract(context["contract"], evidence)
    assert attestation.contract_conformant is True
    assert attestation.safe_resubmission_certified is False
    assert attestation.terminal_evidence_certified is False
    assert not verify_provider_attestation(
        context["contract"],
        evidence,
        attestation,
        ADAPTER_REVISION,
        require_safe_resubmission=True,
    )


def test_missing_required_case_is_rejected(tmp_path):
    context = runtime_context(tmp_path, "missing")
    evidence = conformance_evidence(
        context["contract"],
        cases=all_cases()[:-1],
    )
    with pytest.raises(ConformanceError, match="missing required conformance cases"):
        attest_provider_contract(context["contract"], evidence)


def test_duplicate_case_ids_are_rejected(tmp_path):
    context = runtime_context(tmp_path, "duplicate")
    duplicate = (
        case("same_request_semantics"),
        case("same_request_semantics"),
    )
    with pytest.raises(ValueError, match="must be unique"):
        conformance_evidence(context["contract"], cases=duplicate)


def test_failed_mandatory_case_produces_nonconformant_attestation(tmp_path):
    context = runtime_context(tmp_path, "failed")
    evidence = conformance_evidence(
        context["contract"],
        cases=all_cases(failed={"absence_semantics"}),
    )
    attestation = attest_provider_contract(context["contract"], evidence)
    assert attestation.contract_conformant is False
    assert attestation.safe_resubmission_certified is False
    assert "absence_semantics" in attestation.failed_cases


def test_unsafe_contract_never_certifies_resubmission_even_if_cases_pass(tmp_path):
    context = runtime_context(
        tmp_path,
        "unsafe-contract",
        contract_override=lambda contract: replace(
            contract,
            same_key_same_request="may_duplicate",
        ),
    )
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    assert attestation.contract_conformant is True
    assert context["contract"].safe_idempotent_resubmission is False
    assert attestation.safe_resubmission_certified is False


def test_terminal_case_is_required_only_when_contract_claims_terminal_lookup(tmp_path):
    context = runtime_context(tmp_path, "terminal-required")
    without_terminal = conformance_evidence(
        context["contract"],
        cases=all_cases(terminal=False),
    )
    with pytest.raises(ConformanceError, match="terminal_evidence_binding"):
        attest_provider_contract(context["contract"], without_terminal)

    no_terminal_contract = replace(context["contract"], terminal_evidence_lookup=False)
    evidence = conformance_evidence(
        no_terminal_contract,
        cases=all_cases(terminal=False),
    )
    attestation = attest_provider_contract(no_terminal_contract, evidence)
    assert attestation.contract_conformant is True
    assert attestation.terminal_evidence_certified is False


def test_wrong_contract_digest_is_rejected(tmp_path):
    context = runtime_context(tmp_path, "wrong-contract")
    evidence = replace(
        conformance_evidence(context["contract"]),
        contract_digest=D,
    )
    with pytest.raises(ConformanceError, match="contract digest mismatch"):
        attest_provider_contract(context["contract"], evidence)


def test_revision_mismatch_or_tampered_attestation_does_not_verify(tmp_path):
    context = runtime_context(tmp_path, "revision")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    assert not verify_provider_attestation(
        context["contract"],
        evidence,
        attestation,
        OTHER_REVISION,
    )
    tampered = replace(attestation, safe_resubmission_certified=False)
    assert not verify_provider_attestation(
        context["contract"],
        evidence,
        tampered,
        ADAPTER_REVISION,
    )


def test_sandbox_attestation_cannot_elevate_provisional_resubmit_decision(tmp_path):
    context = runtime_context(tmp_path, "sandbox-gate")
    evidence = conformance_evidence(context["contract"], scope="sandbox")
    attestation = attest_provider_contract(context["contract"], evidence)
    with pytest.raises(ConformanceError, match="lacks production-equivalent"):
        authorize_attested_resubmission(**attested_args(context, evidence, attestation))


def test_production_attestation_emits_same_invocation_only_permit(tmp_path):
    context = runtime_context(tmp_path, "permit")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    permit = authorize_attested_resubmission(**attested_args(context, evidence, attestation))
    assert permit.authority == "IDEMPOTENT_RESUBMIT_ONLY"
    assert permit.new_physical_attempt_authorized is False
    assert permit.invocation_id == context["authorization"].request.invocation_id
    assert permit.request_digest == context["authorization"].request.digest
    assert permit.reconciliation_evidence_digest == context["decision"].evidence_digest
    assert permit.conformance_evidence_digest == evidence.digest
    assert verify_attested_resubmission_permit(
        permit,
        context["decision"],
        context["contract"],
        evidence,
        attestation,
        adapter_revision=ADAPTER_REVISION,
        dispatch_state=context["unknown"],
        dispatch_permit=context["dispatch_permit"],
        live_permit=context["live_permit"],
        capacity_store=context["capacity_store"],
        runner=context["runner"],
    )


def test_stale_live_permit_after_revocation_blocks_attested_resubmission(tmp_path):
    context = runtime_context(tmp_path, "stale-live")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    revoked = revoke_session(context["session"])
    released, _, _ = release_capacity_for_revocation(
        context["capacity_state"],
        context["runner"],
        context["grant"].lease,
        revoked,
    )
    context["capacity_store"].commit(
        context["runner"],
        context["capacity_state"].digest,
        released,
    )
    with pytest.raises(ConformanceError, match="live dispatch permit is stale"):
        authorize_attested_resubmission(**attested_args(context, evidence, attestation))


def test_attested_permit_tampering_does_not_verify(tmp_path):
    context = runtime_context(tmp_path, "tamper-permit")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    permit = authorize_attested_resubmission(**attested_args(context, evidence, attestation))
    tampered = replace(permit, request_digest=D)
    assert not verify_attested_resubmission_permit(
        tampered,
        context["decision"],
        context["contract"],
        evidence,
        attestation,
        adapter_revision=ADAPTER_REVISION,
        dispatch_state=context["unknown"],
        dispatch_permit=context["dispatch_permit"],
        live_permit=context["live_permit"],
        capacity_store=context["capacity_store"],
        runner=context["runner"],
    )


def test_reconciliation_and_conformance_evidence_are_independent_lineages(tmp_path):
    context = runtime_context(tmp_path, "lineages")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    permit = authorize_attested_resubmission(**attested_args(context, evidence, attestation))
    assert context["decision"].evidence_digest != evidence.digest
    assert permit.reconciliation_evidence_digest == context["decision"].evidence_digest
    assert permit.conformance_evidence_digest == evidence.digest


def test_attestation_constructor_rejects_unknown_case_identity(tmp_path):
    context = runtime_context(tmp_path, "attestation-hardening")
    evidence = conformance_evidence(context["contract"])
    attestation = attest_provider_contract(context["contract"], evidence)
    with pytest.raises(ValueError, match="unknown conformance case"):
        replace(attestation, passed_cases=attestation.passed_cases + ("invented",))
