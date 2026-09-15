from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    SqliteDispatchIntentStore,
    authorize_live_dispatch,
    authorize_physical_attempt,
    bind_session,
    initialize_capacity_state,
    plan_execution,
    prepare_dispatch_intent,
    reference_runner,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.reconciliation import (
    ProviderReconciliationContract,
    ProviderReconciliationEvidence,
    ProviderReconciliationObservation,
    ReconciliationError,
    admit_reconciliation_observation,
    create_reconciliation_query,
    decide_reconciliation,
)

D = "sha256:" + "d" * 64
E = "sha256:" + "e" * 64
F = "sha256:" + "f" * 64


def make_context(tmp_path, suffix="base", runner=None):
    runner = runner or reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-reconciliation-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Reconciliation conformance {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://reconciliation/{suffix}", D),),
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
    unknown, permit = dispatch_store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    live = authorize_live_dispatch(unknown, permit, capacity_store, runner)
    contract = ProviderReconciliationContract(
        provider=authorization.request.provider,
        adapter=authorization.request.adapter,
        adapter_version=authorization.request.adapter_version,
    )
    query = create_reconciliation_query(unknown, permit, authorization, contract)
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
        "intent": intent,
        "dispatch_store": dispatch_store,
        "unknown": unknown,
        "permit": permit,
        "live": live,
        "contract": contract,
        "query": query,
    }


def observation(context, status, *, terminal_evidence=True):
    query = context["query"]
    common = dict(
        query_digest=query.digest,
        invocation_id=query.invocation_id,
        request_digest=query.request_digest,
        provider=query.provider,
        adapter=query.adapter,
        adapter_version=query.adapter_version,
        status=status,
        evidence_digest=E,
    )
    if status == "absent":
        return ProviderReconciliationObservation(**common)
    if status == "accepted":
        return ProviderReconciliationObservation(
            **common,
            provider_invocation_id="provider-op-1",
        )
    if status == "terminal":
        return ProviderReconciliationObservation(
            **common,
            provider_invocation_id="provider-op-1",
            terminal_evidence_digest=F if terminal_evidence else None,
        )
    return ProviderReconciliationObservation(**common)


def admitted(context, status, *, terminal_evidence=True):
    obs = observation(context, status, terminal_evidence=terminal_evidence)
    return admit_reconciliation_observation(context["query"], context["contract"], obs)


def decide(context, evidence, **overrides):
    kwargs = dict(
        state=context["unknown"],
        permit=context["permit"],
        authorization=context["authorization"],
        contract=context["contract"],
        evidence=evidence,
        live_permit=context["live"],
        capacity_store=context["capacity_store"],
        runner=context["runner"],
    )
    kwargs.update(overrides)
    return decide_reconciliation(**kwargs)


def test_safe_contract_uses_invocation_identity_and_request_binding(tmp_path):
    context = make_context(tmp_path, "contract")
    contract = context["contract"]
    assert contract.reconciliation_capable is True
    assert contract.safe_idempotent_resubmission is True
    assert contract.idempotency_key == "invocation_id"
    assert contract.request_digest_bound is True
    assert context["query"].invocation_id == context["authorization"].request.invocation_id
    assert context["query"].request_digest == context["authorization"].request.digest


def test_contract_rejects_different_request_under_same_key_semantics():
    with pytest.raises(ValueError, match="different request must be rejected"):
        ProviderReconciliationContract(
            provider="p",
            adapter="a",
            adapter_version="1",
            same_key_different_request="allow",
        )


def test_query_rejects_provider_contract_mismatch(tmp_path):
    context = make_context(tmp_path, "mismatch")
    bad = replace(context["contract"], adapter="other-adapter")
    with pytest.raises(ReconciliationError, match="does not match physical authorization"):
        create_reconciliation_query(
            context["unknown"],
            context["permit"],
            context["authorization"],
            bad,
        )


def test_query_rejects_contract_without_lookup_or_request_binding(tmp_path):
    context = make_context(tmp_path, "incapable")
    for bad in (
        replace(context["contract"], lookup_by_invocation=False),
        replace(context["contract"], request_digest_bound=False),
    ):
        with pytest.raises(ReconciliationError, match="cannot reconcile"):
            create_reconciliation_query(
                context["unknown"],
                context["permit"],
                context["authorization"],
                bad,
            )


def test_absent_with_strong_idempotency_and_fresh_live_permit_authorizes_same_invocation(tmp_path):
    context = make_context(tmp_path, "absent-safe")
    evidence = admitted(context, "absent")
    decision = decide(context, evidence)
    assert decision.action == "resubmit_same_invocation"
    assert decision.resubmit_authorized is True
    assert decision.requires_fresh_live_permit is True
    assert decision.live_permit_digest == context["live"].digest
    assert decision.invocation_id == context["authorization"].request.invocation_id
    assert decision.request_digest == context["authorization"].request.digest


def test_absent_without_strong_idempotency_holds_even_when_provider_can_reconcile(tmp_path):
    context = make_context(tmp_path, "absent-unsafe")
    unsafe = replace(context["contract"], same_key_same_request="may_duplicate")
    query = create_reconciliation_query(
        context["unknown"],
        context["permit"],
        context["authorization"],
        unsafe,
    )
    obs = replace(observation(context, "absent"), query_digest=query.digest)
    evidence = admit_reconciliation_observation(query, unsafe, obs)
    decision = decide_reconciliation(
        context["unknown"],
        context["permit"],
        context["authorization"],
        unsafe,
        evidence,
        live_permit=context["live"],
        capacity_store=context["capacity_store"],
        runner=context["runner"],
    )
    assert unsafe.reconciliation_capable is True
    assert unsafe.safe_idempotent_resubmission is False
    assert decision.action == "hold"
    assert decision.resubmit_authorized is False


def test_absent_safe_contract_still_requires_fresh_live_permit(tmp_path):
    context = make_context(tmp_path, "fresh-live")
    evidence = admitted(context, "absent")
    with pytest.raises(ReconciliationError, match="requires a fresh live dispatch permit"):
        decide_reconciliation(
            context["unknown"],
            context["permit"],
            context["authorization"],
            context["contract"],
            evidence,
        )


def test_stale_live_permit_after_revocation_blocks_absent_resubmission(tmp_path):
    context = make_context(tmp_path, "stale-live")
    evidence = admitted(context, "absent")
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
    with pytest.raises(ReconciliationError, match="stale or invalid"):
        decide(context, evidence)


def test_accepted_provider_operation_is_polled_not_resubmitted(tmp_path):
    context = make_context(tmp_path, "accepted")
    decision = decide(context, admitted(context, "accepted"))
    assert decision.action == "poll_existing"
    assert decision.resubmit_authorized is False
    assert decision.live_permit_digest is None


def test_terminal_with_retrievable_evidence_routes_to_native_admission(tmp_path):
    context = make_context(tmp_path, "terminal")
    decision = decide(context, admitted(context, "terminal"))
    assert decision.action == "admit_terminal_evidence"
    assert decision.resubmit_authorized is False


def test_terminal_without_retrievable_evidence_holds(tmp_path):
    context = make_context(tmp_path, "terminal-hold")
    contract = replace(context["contract"], terminal_evidence_lookup=False)
    query = create_reconciliation_query(
        context["unknown"],
        context["permit"],
        context["authorization"],
        contract,
    )
    obs = ProviderReconciliationObservation(
        query_digest=query.digest,
        invocation_id=query.invocation_id,
        request_digest=query.request_digest,
        provider=query.provider,
        adapter=query.adapter,
        adapter_version=query.adapter_version,
        status="terminal",
        evidence_digest=E,
        provider_invocation_id="provider-op-1",
        terminal_evidence_digest=None,
    )
    evidence = admit_reconciliation_observation(query, contract, obs)
    decision = decide_reconciliation(
        context["unknown"],
        context["permit"],
        context["authorization"],
        contract,
        evidence,
    )
    assert decision.action == "hold"
    assert decision.resubmit_authorized is False


def test_unknown_provider_state_preserves_ambiguity_even_with_safe_idempotency(tmp_path):
    context = make_context(tmp_path, "unknown")
    decision = decide(context, admitted(context, "unknown"))
    assert decision.action == "hold"
    assert decision.resubmit_authorized is False
    assert "preserve ambiguity" in decision.reason


def test_observation_identity_mismatch_is_rejected(tmp_path):
    context = make_context(tmp_path, "obs-mismatch")
    obs = replace(observation(context, "absent"), request_digest=F)
    with pytest.raises(ReconciliationError, match="identity mismatch"):
        admit_reconciliation_observation(context["query"], context["contract"], obs)


def test_manually_forged_evidence_is_revalidated_at_decision_time(tmp_path):
    context = make_context(tmp_path, "forged")
    valid = admitted(context, "absent")
    forged_observation = replace(valid.observation, invocation_id="gei-forged")
    forged = ProviderReconciliationEvidence(
        query=valid.query,
        observation=forged_observation,
        contract_digest=valid.contract_digest,
    )
    with pytest.raises(ReconciliationError):
        decide(context, forged)
