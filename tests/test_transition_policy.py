import json
from dataclasses import replace

import pytest

from general_execution import (
    AdmittedEvidence,
    PortfolioEntry,
    TransitionDecision,
    TransitionPolicy,
    TransitionPolicyError,
    TransitionRequest,
    TransitionRule,
    deserialize_transition_decision,
    deserialize_transition_policy,
    deserialize_transition_request,
    evaluate_transition,
    serialize_transition_decision,
    serialize_transition_policy,
    serialize_transition_request,
    transition_policy_from_dict,
    transition_policy_to_dict,
    transition_request_to_dict,
    verify_transition_decision,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64


def entry(**changes):
    values = dict(
        work_id="FAE-BE-04",
        role="active",
        state="running",
        objective="Bind explorer",
        active_gate="PUBLIC_NODE_BINDING",
        next_action_ref="action://deploy",
        source_revision="abc123",
        evidence_required=("deployment_url",),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def evidence(kind="execution_report", digest=D1):
    return AdmittedEvidence(
        kind=kind,
        locator=f"artifact://{kind}",
        content_digest=digest,
    )


def rule(**changes):
    values = dict(
        rule_id="010-running-completed",
        from_role="active",
        from_state="running",
        signal="execution_completed",
        target_role="active",
        target_state="verifying",
        action_ref="action://verify",
        required_evidence=("execution_report",),
    )
    values.update(changes)
    return TransitionRule(**values)


def policy(*rules):
    return TransitionPolicy(
        policy_id="durable-asp-v1",
        policy_revision="rev-001",
        rules=tuple(rules or (rule(),)),
    )


def request(**changes):
    item = entry()
    values = dict(
        work_id=item.work_id,
        entry_digest=item.digest,
        from_role=item.role,
        from_state=item.state,
        signal="execution_completed",
        admitted_evidence=(evidence(),),
    )
    values.update(changes)
    return TransitionRequest(**values)


def test_transition_policy_round_trip_is_canonical():
    p = policy()
    encoded = serialize_transition_policy(p)
    decoded = deserialize_transition_policy(encoded)
    assert decoded == p
    assert decoded.digest == p.digest
    assert encoded == serialize_transition_policy(decoded)


def test_transition_request_round_trip_is_canonical():
    r = request()
    encoded = serialize_transition_request(r)
    decoded = deserialize_transition_request(encoded)
    assert decoded == r
    assert encoded == serialize_transition_request(decoded)


def test_transition_decision_round_trip_is_canonical():
    p = policy()
    r = request()
    d = evaluate_transition(p, r)
    encoded = serialize_transition_decision(d)
    decoded = deserialize_transition_decision(encoded)
    assert decoded == d
    assert encoded == serialize_transition_decision(decoded)


def test_evaluate_transition_binds_policy_rule_request_and_evidence():
    p = policy()
    r = request()
    d = evaluate_transition(p, r)
    assert d.policy_digest == p.digest
    assert d.rule_digest == p.rules[0].digest
    assert d.request_digest == r.digest
    assert d.entry_digest == r.entry_digest
    assert d.evidence_digests == (r.admitted_evidence[0].digest,)
    assert verify_transition_decision(p, r, d)


def test_tampered_decision_fails_reproduction():
    p = policy()
    r = request()
    d = evaluate_transition(p, r)
    assert not verify_transition_decision(
        p,
        r,
        replace(d, action_ref="action://tampered"),
    )


def test_missing_required_evidence_fails_closed():
    with pytest.raises(TransitionPolicyError, match="evidence requirements unsatisfied"):
        evaluate_transition(policy(), request(admitted_evidence=()))


def test_wrong_evidence_kind_does_not_satisfy_rule():
    with pytest.raises(TransitionPolicyError, match="evidence requirements unsatisfied"):
        evaluate_transition(
            policy(),
            request(admitted_evidence=(evidence("other", D2),)),
        )


def test_no_matching_rule_fails_closed():
    with pytest.raises(TransitionPolicyError, match="no unique admissible"):
        evaluate_transition(
            policy(),
            request(signal="failure_confirmed", admitted_evidence=(evidence("failure", D2),)),
        )


def test_policy_rejects_ambiguous_match_keys():
    a = rule(rule_id="010-a")
    b = rule(rule_id="020-b", action_ref="action://other")
    with pytest.raises(TransitionPolicyError, match="ambiguous match keys"):
        policy(a, b)


def test_policy_requires_canonical_rule_order():
    with pytest.raises(TransitionPolicyError, match="sorted by rule_id"):
        policy(
            rule(rule_id="020-b", signal="failure_confirmed", target_state="failed", required_evidence=("failure",)),
            rule(rule_id="010-a"),
        )


def test_rule_rejects_invalid_role_state_combinations():
    with pytest.raises(TransitionPolicyError, match="invalid source role/state"):
        rule(from_role="secondary", from_state="running")
    with pytest.raises(TransitionPolicyError, match="invalid target role/state"):
        rule(target_role="passive", target_state="ready")


def test_observed_signals_require_declared_evidence_kinds():
    with pytest.raises(TransitionPolicyError, match="requires explicit evidence kinds"):
        rule(required_evidence=())


def test_start_authorized_can_be_policy_only():
    start = TransitionRule(
        rule_id="001-start",
        from_role="active",
        from_state="ready",
        signal="start_authorized",
        target_role="active",
        target_state="running",
        action_ref="action://start",
    )
    p = policy(start)
    item = entry(state="ready")
    r = TransitionRequest(
        work_id=item.work_id,
        entry_digest=item.digest,
        from_role="active",
        from_state="ready",
        signal="start_authorized",
    )
    d = evaluate_transition(p, r)
    assert d.target_state == "running"
    assert d.evidence_digests == ()


def test_human_gate_transition_names_authority_boundary():
    gate = TransitionRule(
        rule_id="050-gate",
        from_role="active",
        from_state="running",
        signal="authority_boundary_reached",
        target_role="active",
        target_state="human_gate",
        action_ref="authority://request-human",
        required_evidence=("boundary_evidence",),
        authority_boundary="spend_above_budget",
    )
    assert gate.target_state == "human_gate"
    assert not gate.authority_required


def test_human_gate_without_boundary_is_rejected():
    with pytest.raises(TransitionPolicyError, match="human_gate transition"):
        TransitionRule(
            rule_id="050-gate",
            from_role="active",
            from_state="running",
            signal="authority_boundary_reached",
            target_role="active",
            target_state="human_gate",
            action_ref="authority://request-human",
            required_evidence=("boundary_evidence",),
        )


def test_authority_consuming_rule_requires_boundary():
    with pytest.raises(TransitionPolicyError, match="must name authority_boundary"):
        TransitionRule(
            rule_id="060-authorize",
            from_role="active",
            from_state="human_gate",
            signal="authority_presented",
            target_role="active",
            target_state="running",
            action_ref="action://resume",
            authority_required=True,
        )


def test_authority_consuming_transition_requires_admitted_authority_ref():
    auth_rule = TransitionRule(
        rule_id="060-authorize",
        from_role="active",
        from_state="human_gate",
        signal="authority_presented",
        target_role="active",
        target_state="running",
        action_ref="action://resume",
        authority_required=True,
        authority_boundary="spend_above_budget",
    )
    p = policy(auth_rule)
    item = entry(state="human_gate", authority_boundary="spend_above_budget")
    r = TransitionRequest(
        work_id=item.work_id,
        entry_digest=item.digest,
        from_role="active",
        from_state="human_gate",
        signal="authority_presented",
    )
    with pytest.raises(TransitionPolicyError, match="requires admitted authority reference"):
        evaluate_transition(p, r)

    authorized = replace(r, authority_ref=D3)
    d = evaluate_transition(p, authorized)
    assert d.authority_ref == D3
    assert d.authority_boundary == "spend_above_budget"


def test_policy_can_express_secondary_promotion_without_executing_it():
    promote = TransitionRule(
        rule_id="100-promote-secondary",
        from_role="secondary",
        from_state="ready",
        signal="start_authorized",
        target_role="active",
        target_state="ready",
        action_ref="portfolio://promote-secondary",
    )
    assert promote.from_role == "secondary"
    assert promote.target_role == "active"


def test_policy_can_express_active_parking_without_executing_it():
    park = TransitionRule(
        rule_id="110-park-active",
        from_role="active",
        from_state="waiting_external",
        signal="external_blocker_confirmed",
        target_role="passive",
        target_state="passive",
        action_ref="portfolio://park-active",
        required_evidence=("external_blocker",),
    )
    assert park.target_role == "passive"
    assert park.target_state == "passive"


def test_duplicate_admitted_evidence_kinds_are_rejected():
    with pytest.raises(TransitionPolicyError, match="evidence kinds must be unique"):
        request(
            admitted_evidence=(
                evidence("execution_report", D1),
                evidence("execution_report", D2),
            )
        )


def test_authority_ref_must_be_immutable_digest():
    with pytest.raises(TransitionPolicyError, match="authority_ref must be sha256"):
        request(authority_ref="authority://mutable")


def test_unknown_fields_fail_closed():
    data = transition_policy_to_dict(policy())
    data["unexpected"] = True
    with pytest.raises(TransitionPolicyError, match="fields mismatch"):
        transition_policy_from_dict(data)

    req = transition_request_to_dict(request())
    req["unexpected"] = True
    with pytest.raises(TransitionPolicyError, match="fields mismatch"):
        deserialize_transition_request(json.dumps(req))


def test_malformed_json_fails_closed():
    with pytest.raises(TransitionPolicyError, match="not valid JSON"):
        deserialize_transition_policy("{broken")