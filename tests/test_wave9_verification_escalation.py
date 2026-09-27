from dataclasses import replace

import pytest

from general_execution import (
    CheckpointEvidence,
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    PortfolioEntry,
    PortfolioState,
    ResumeTickObservation,
    SqlitePortfolioHeadStore,
    TransitionPolicy,
    TransitionRule,
    resume_tick,
    sha256_digest,
)
from general_execution.verification_escalation import (
    IndependentVerificationResponse,
    RedTeamResponse,
    VerificationEscalationError,
    admit_independent_verification,
    admit_red_team_response,
    build_verification_observation,
    prepare_independent_verification,
    prepare_red_team_escalation,
)


REVISION = "9" * 40


def digest(value):
    return sha256_digest(value)


def active(state="running"):
    return PortfolioEntry(
        work_id="ACTIVE",
        role="active",
        state=state,
        objective="Advance bounded work",
        active_gate="VERIFY",
        next_action_ref="action://execute" if state == "running" else "action://verify",
        source_revision="source-wave9",
        evidence_required=("result",),
    )


def secondary():
    return PortfolioEntry(
        work_id="SECONDARY",
        role="secondary",
        state="ready",
        objective="Wait for promotion",
        active_gate="SECONDARY",
        next_action_ref="action://secondary",
        source_revision="source-secondary",
    )


def portfolio():
    return PortfolioState(
        portfolio_id="durable-wave9",
        generation=0,
        active=active(),
        secondary=secondary(),
        passive=(),
    )


def policy():
    return TransitionPolicy(
        policy_id="wave9-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-complete",
                from_state="running",
                event="execution_completed",
                to_state="verifying",
                next_action_ref="action://independent-verification",
                required_evidence=("execution_result",),
            ),
            TransitionRule(
                rule_id="02-pass",
                from_state="verifying",
                event="verification_passed",
                to_state="complete",
                next_action_ref="action://complete",
                required_evidence=("verifier_pass",),
            ),
            TransitionRule(
                rule_id="03-reject",
                from_state="verifying",
                event="verification_failed",
                to_state="rework",
                next_action_ref="action://rework",
                required_evidence=("verifier_reject",),
            ),
        ),
    )


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://wave9",
        required_verifier_ref="verifier://wave9",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://core-pass",
        evidence_digest=digest("core-pass"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-09-27T12:00:00Z",
        passed=True,
        test_count=1,
    )
    return requirement, receipt


def enter_verifying(tmp_path):
    state = portfolio()
    p = policy()
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    requirement, receipt = gate()
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event="execution_completed",
        evidence=(
            CheckpointEvidence(
                kind="execution_result",
                locator="artifact://execution-result",
                digest=digest("execution-result"),
            ),
        ),
        action_ref="action://execution-completed",
        observed_at="2026-09-27T12:01:00Z",
        summary="Execution fragment completed",
        canonical_refs=("artifact://execution-result",),
    )
    tick = resume_tick(
        store,
        state.portfolio_id,
        p,
        observation,
        core_requirement=requirement,
        core_verification=receipt,
    )
    checkpoint = store.latest_checkpoint(state.portfolio_id)
    assert checkpoint is not None
    request = prepare_independent_verification(
        tick,
        checkpoint,
        policy_digest=p.digest,
        executor_id="executor-a",
        worker_id="worker-a",
        subject_digest=digest("candidate-output"),
        evidence_digest=digest("execution-evidence"),
    )
    return store, p, requirement, receipt, tick, checkpoint, request


def reject_response(request, **changes):
    values = dict(
        request_digest=request.digest,
        verifier_system="project_assurance",
        verifier_id="project-assurance-a",
        subject_digest=request.subject_digest,
        evidence_digest=digest("pa-rejection"),
        outcome="reject",
        findings=("finding-a",),
        red_team_recommended=False,
    )
    values.update(changes)
    return IndependentVerificationResponse(**values)


def pass_response(request, **changes):
    values = dict(
        request_digest=request.digest,
        verifier_system="project_assurance",
        verifier_id="project-assurance-a",
        subject_digest=request.subject_digest,
        evidence_digest=digest("pa-pass"),
        outcome="pass",
    )
    values.update(changes)
    return IndependentVerificationResponse(**values)


def test_request_binds_exact_committed_checkpoint(tmp_path):
    _, p, _, _, tick, checkpoint, request = enter_verifying(tmp_path)
    assert request.portfolio_id == checkpoint.portfolio_id
    assert request.generation == checkpoint.portfolio_generation
    assert request.state_digest == checkpoint.portfolio_state_digest
    assert request.checkpoint_digest == checkpoint.digest
    assert request.tick_digest == tick.digest
    assert request.policy_digest == p.digest
    assert not request.self_verification_authorized
    assert not request.integration_authorized
    assert not request.repair_authorized


def test_non_verifying_or_stale_provenance_is_rejected(tmp_path):
    _, p, _, _, tick, checkpoint, _ = enter_verifying(tmp_path)
    with pytest.raises(VerificationEscalationError, match="durable provenance"):
        prepare_independent_verification(
            replace(tick, post_state_digest=digest("other-state")),
            checkpoint,
            policy_digest=p.digest,
            executor_id="executor-a",
            worker_id="worker-a",
            subject_digest=digest("candidate-output"),
            evidence_digest=digest("execution-evidence"),
        )
    non_verifying = replace(checkpoint, state_after="rework")
    with pytest.raises(VerificationEscalationError, match="state_after=verifying"):
        prepare_independent_verification(
            replace(tick, checkpoint_digest=non_verifying.digest),
            non_verifying,
            policy_digest=p.digest,
            executor_id="executor-a",
            worker_id="worker-a",
            subject_digest=digest("candidate-output"),
            evidence_digest=digest("execution-evidence"),
        )


@pytest.mark.parametrize("identity_attr", ["executor_id", "worker_id"])
def test_executor_or_worker_cannot_self_verify(tmp_path, identity_attr):
    *_, request = enter_verifying(tmp_path)
    response = pass_response(request, verifier_id=getattr(request, identity_attr))
    with pytest.raises(VerificationEscalationError, match="self-verify"):
        admit_independent_verification(
            request,
            response,
            authenticated_response_digest=response.digest,
        )


def test_response_authentication_and_subject_binding_fail_closed(tmp_path):
    *_, request = enter_verifying(tmp_path)
    response = pass_response(request)
    with pytest.raises(VerificationEscalationError, match="independently admitted"):
        admit_independent_verification(
            request,
            response,
            authenticated_response_digest=digest("wrong-auth"),
        )
    substituted = replace(response, subject_digest=digest("other-subject"))
    with pytest.raises(VerificationEscalationError, match="provenance mismatch"):
        admit_independent_verification(
            request,
            substituted,
            authenticated_response_digest=substituted.digest,
        )


def test_pass_admission_builds_policy_bound_evidence_only(tmp_path):
    store, p, _, _, _, _, request = enter_verifying(tmp_path)
    response = pass_response(request)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    observation = build_verification_observation(
        request,
        response,
        admission,
        observed_at="2026-09-27T12:02:00Z",
        summary="Independent verification passed",
    )
    state_before, _ = store.load(request.portfolio_id)
    assert state_before.active.state == "verifying"
    assert admission.disposition == "verified"
    assert observation.event == "verification_passed"
    assert observation.policy_digest == p.digest
    assert observation.evidence[0].kind == "verifier_pass"
    assert observation.evidence[0].digest == response.evidence_digest
    assert not admission.integration_authorized
    assert not admission.repair_authorized
    state_after, _ = store.load(request.portfolio_id)
    assert state_after == state_before


def test_rejection_enters_rework_only_through_explicit_transition_policy(tmp_path):
    store, p, requirement, receipt, _, _, request = enter_verifying(tmp_path)
    response = reject_response(request)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    observation = build_verification_observation(
        request,
        response,
        admission,
        observed_at="2026-09-27T12:03:00Z",
        summary="Independent verification rejected output",
    )
    before, _ = store.load(request.portfolio_id)
    assert before.active.state == "verifying"
    assert admission.disposition == "rework_required"
    assert observation.event == "verification_failed"
    assert observation.evidence[0].kind == "verifier_reject"

    result = resume_tick(
        store,
        request.portfolio_id,
        p,
        observation,
        core_requirement=requirement,
        core_verification=receipt,
    )
    after, _ = store.load(request.portfolio_id)
    assert result.disposition == "committed"
    assert after.active.state == "rework"
    assert after.active.next_action_ref == "action://rework"


def test_rejection_requires_canonical_findings(tmp_path):
    *_, request = enter_verifying(tmp_path)
    with pytest.raises(VerificationEscalationError, match="requires findings"):
        reject_response(request, findings=())
    with pytest.raises(VerificationEscalationError, match="canonical-sorted"):
        reject_response(request, findings=("z", "a"))


def test_verifier_cannot_smuggle_repair_or_integration_authority(tmp_path):
    *_, request = enter_verifying(tmp_path)
    with pytest.raises(VerificationEscalationError, match="cannot grant"):
        pass_response(request, repair_authorized=True)
    with pytest.raises(VerificationEscalationError, match="cannot grant"):
        pass_response(request, integration_authorized=True)


def test_red_team_escalation_requires_explicit_rejected_recommendation(tmp_path):
    *_, request = enter_verifying(tmp_path)
    rejected = reject_response(request)
    admission = admit_independent_verification(
        request,
        rejected,
        authenticated_response_digest=rejected.digest,
    )
    with pytest.raises(VerificationEscalationError, match="explicit recommendation"):
        prepare_red_team_escalation(
            request,
            rejected,
            admission,
            requested_scope_ref="redteam://bounded-wave9",
        )

    passed = pass_response(request)
    passed_admission = admit_independent_verification(
        request,
        passed,
        authenticated_response_digest=passed.digest,
    )
    with pytest.raises(VerificationEscalationError):
        prepare_red_team_escalation(
            request,
            passed,
            passed_admission,
            requested_scope_ref="redteam://bounded-wave9",
        )


def test_recommended_rejection_creates_authority_free_red_team_request(tmp_path):
    *_, request = enter_verifying(tmp_path)
    response = reject_response(request, red_team_recommended=True)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    escalation = prepare_red_team_escalation(
        request,
        response,
        admission,
        requested_scope_ref="redteam://bounded-wave9",
    )
    assert escalation.target_system == "red_team"
    assert escalation.verification_request_digest == request.digest
    assert escalation.verification_response_digest == response.digest
    assert escalation.verification_admission_digest == admission.digest
    assert not escalation.authority_created
    assert not escalation.repair_authorized
    assert not escalation.integration_authorized
    assert not escalation.transport_authorized


def test_red_team_responder_must_be_independent(tmp_path):
    *_, request = enter_verifying(tmp_path)
    response = reject_response(request, red_team_recommended=True)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    escalation = prepare_red_team_escalation(
        request,
        response,
        admission,
        requested_scope_ref="redteam://bounded-wave9",
    )
    for responder in (request.executor_id, request.worker_id, response.verifier_id):
        red = RedTeamResponse(
            request_digest=escalation.digest,
            responder_id=responder,
            evidence_digest=digest("red-team"),
            available=True,
            findings=("attack-finding",),
        )
        with pytest.raises(VerificationEscalationError, match="independent"):
            admit_red_team_response(
                escalation,
                red,
                authenticated_response_digest=red.digest,
            )


def test_red_team_response_is_advisory_only(tmp_path):
    *_, request = enter_verifying(tmp_path)
    response = reject_response(request, red_team_recommended=True)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    escalation = prepare_red_team_escalation(
        request,
        response,
        admission,
        requested_scope_ref="redteam://bounded-wave9",
    )
    red = RedTeamResponse(
        request_digest=escalation.digest,
        responder_id="red-team-a",
        evidence_digest=digest("red-team-evidence"),
        available=True,
        findings=("attack-finding",),
    )
    assert (
        admit_red_team_response(
            escalation,
            red,
            authenticated_response_digest=red.digest,
        )
        == "advisory_only"
    )
    with pytest.raises(VerificationEscalationError, match="cannot grant"):
        replace(red, repair_authorized=True)


def test_unavailable_red_team_waits_external_without_mutation(tmp_path):
    store, _, _, _, _, _, request = enter_verifying(tmp_path)
    response = reject_response(request, red_team_recommended=True)
    admission = admit_independent_verification(
        request,
        response,
        authenticated_response_digest=response.digest,
    )
    escalation = prepare_red_team_escalation(
        request,
        response,
        admission,
        requested_scope_ref="redteam://bounded-wave9",
    )
    red = RedTeamResponse(
        request_digest=escalation.digest,
        responder_id="red-team-a",
        evidence_digest=digest("unavailable"),
        available=False,
    )
    before, _ = store.load(request.portfolio_id)
    assert (
        admit_red_team_response(
            escalation,
            red,
            authenticated_response_digest=red.digest,
        )
        == "waiting_external"
    )
    after, _ = store.load(request.portfolio_id)
    assert after == before


def test_pass_cannot_hide_red_team_recommendation(tmp_path):
    *_, request = enter_verifying(tmp_path)
    with pytest.raises(VerificationEscalationError, match="cannot carry"):
        pass_response(request, red_team_recommended=True)
