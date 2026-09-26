import json
from dataclasses import replace

import pytest

from general_execution import (
    TransitionPolicy,
    TransitionPolicyError,
    TransitionRule,
    deserialize_transition_policy,
    match_transition_rule,
    serialize_transition_policy,
    transition_policy_from_dict,
    transition_policy_to_dict,
)


def rule(rule_id="01-start", **changes):
    values = dict(
        rule_id=rule_id,
        from_state="ready",
        event="execution_started",
        to_state="running",
        next_action_ref="action://execute-current-fragment",
        required_evidence=("execution_authorization",),
    )
    values.update(changes)
    return TransitionRule(**values)


def policy(*rules):
    if not rules:
        rules = (
            rule("01-start"),
            rule(
                "02-completed",
                from_state="running",
                event="execution_completed",
                to_state="verifying",
                next_action_ref="action://independent-verification",
                required_evidence=("execution_result",),
            ),
            rule(
                "03-verify-pass",
                from_state="verifying",
                event="verification_passed",
                to_state="complete",
                next_action_ref="action://promote-secondary",
                effect="promote_secondary",
                required_evidence=("verifier_pass",),
            ),
            rule(
                "04-external-blocker",
                from_state="running",
                event="external_blocker",
                to_state="passive",
                next_action_ref="action://park-active",
                effect="park_active",
                required_evidence=("blocker_evidence",),
            ),
            rule(
                "05-di",
                from_state="running",
                event="diagnosis_required",
                to_state="di_required",
                next_action_ref="action://invoke-di",
                effect="request_di",
                required_evidence=("failure_evidence",),
            ),
            rule(
                "06-human",
                from_state="running",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://request-human-decision",
                effect="stop_human_gate",
                authority_mode="human_required",
                authority_boundary="spend above preauthorized ceiling",
            ),
            rule(
                "07-wake",
                from_state="passive",
                event="wake_satisfied",
                to_state="ready",
                next_action_ref="action://reenter-ready-queue",
                effect="wake_passive",
                required_evidence=("wake_evidence",),
            ),
        )
    return TransitionPolicy(
        policy_id="durable-asp-v1",
        revision="policy-rev-001",
        rules=tuple(rules),
    )


def test_transition_policy_identity_is_deterministic():
    assert policy().digest == policy().digest


def test_transition_policy_round_trip_is_canonical():
    original = policy()
    encoded = serialize_transition_policy(original)
    decoded = deserialize_transition_policy(encoded)
    assert decoded == original
    assert decoded.digest == original.digest
    assert serialize_transition_policy(decoded) == encoded


def test_transition_policy_dict_round_trip():
    original = policy()
    decoded = transition_policy_from_dict(
        json.loads(json.dumps(transition_policy_to_dict(original)))
    )
    assert decoded == original


def test_policy_default_is_fail_closed_stop():
    assert policy().default_disposition == "stop"


def test_policy_rejects_non_stop_default():
    with pytest.raises(TransitionPolicyError, match="fail closed with stop"):
        TransitionPolicy(
            policy_id="p",
            revision="r",
            rules=(rule(),),
            default_disposition="continue",
        )


def test_policy_requires_rules():
    with pytest.raises(TransitionPolicyError, match="requires at least one rule"):
        TransitionPolicy(policy_id="p", revision="r", rules=())


def test_policy_requires_sorted_rule_ids():
    with pytest.raises(TransitionPolicyError, match="sorted by rule_id"):
        policy(rule("02-b"), rule("01-a"))


def test_policy_rejects_duplicate_rule_ids():
    with pytest.raises(TransitionPolicyError, match="rule_id values must be unique"):
        policy(rule("01-a"), rule("01-a", from_state="running", event="execution_completed"))


def test_policy_rejects_ambiguous_match_keys():
    with pytest.raises(TransitionPolicyError, match="ambiguous"):
        policy(
            rule("01-a"),
            rule("02-b", to_state="failed", next_action_ref="action://other"),
        )


def test_match_returns_exact_rule():
    matched = match_transition_rule(policy(), "running", "execution_completed")
    assert matched.rule_id == "02-completed"
    assert matched.to_state == "verifying"


def test_missing_match_fails_closed():
    with pytest.raises(TransitionPolicyError, match="default disposition is stop"):
        match_transition_rule(policy(), "ready", "fatal_failure")


def test_unknown_current_state_fails_closed():
    with pytest.raises(TransitionPolicyError, match="unsupported current state"):
        match_transition_rule(policy(), "mystery", "execution_started")


def test_unknown_event_fails_closed():
    with pytest.raises(TransitionPolicyError, match="unsupported transition event"):
        match_transition_rule(policy(), "ready", "mystery")


def test_human_required_needs_boundary():
    with pytest.raises(TransitionPolicyError, match="requires authority_boundary"):
        rule(
            authority_mode="human_required",
            to_state="human_gate",
            effect="stop_human_gate",
            authority_boundary=None,
        )


def test_human_required_must_stop_at_human_gate():
    with pytest.raises(TransitionPolicyError, match="transition to human_gate"):
        rule(
            authority_mode="human_required",
            authority_boundary="release approval",
            effect="stop_human_gate",
        )


def test_human_required_must_use_stop_effect():
    with pytest.raises(TransitionPolicyError, match="stop_human_gate effect"):
        rule(
            authority_mode="human_required",
            authority_boundary="release approval",
            to_state="human_gate",
            effect="none",
        )


def test_authority_boundary_rejected_when_mode_none():
    with pytest.raises(TransitionPolicyError, match="requires an authority mode"):
        rule(authority_boundary="release approval")


def test_preauthorized_mode_requires_boundary():
    with pytest.raises(TransitionPolicyError, match="requires authority_boundary"):
        rule(authority_mode="preauthorized_required")


def test_promote_secondary_is_constrained_to_verified_completion():
    with pytest.raises(TransitionPolicyError, match="verification_passed -> complete"):
        rule(effect="promote_secondary")


def test_park_active_is_constrained_to_external_blocker():
    with pytest.raises(TransitionPolicyError, match="external_blocker -> passive"):
        rule(effect="park_active")


def test_wake_passive_is_constrained_to_passive_wake():
    with pytest.raises(TransitionPolicyError, match=r"passive \+ wake_satisfied"):
        rule(effect="wake_passive")


def test_wake_passive_must_return_ready():
    with pytest.raises(TransitionPolicyError, match="transition to ready"):
        rule(
            from_state="passive",
            event="wake_satisfied",
            effect="wake_passive",
            to_state="running",
        )


def test_request_di_must_target_di_required():
    with pytest.raises(TransitionPolicyError, match="transition to di_required"):
        rule(effect="request_di")


def test_stop_human_gate_requires_human_authority_mode():
    with pytest.raises(TransitionPolicyError, match="human_required authority mode"):
        rule(effect="stop_human_gate")


def test_unknown_policy_field_fails_closed():
    data = transition_policy_to_dict(policy())
    data["unexpected"] = True
    with pytest.raises(TransitionPolicyError, match="fields mismatch"):
        transition_policy_from_dict(data)


def test_nested_unknown_rule_field_fails_closed():
    data = transition_policy_to_dict(policy())
    data["rules"][0]["unexpected"] = True
    with pytest.raises(TransitionPolicyError, match="transition rule fields mismatch"):
        transition_policy_from_dict(data)


def test_schema_tamper_fails_closed():
    data = transition_policy_to_dict(policy())
    data["schema_version"] = "ge.transition-policy.v999"
    with pytest.raises(TransitionPolicyError, match="unsupported transition policy schema"):
        transition_policy_from_dict(data)


def test_duplicate_required_evidence_is_rejected():
    with pytest.raises(TransitionPolicyError, match="must not contain duplicates"):
        rule(required_evidence=("x", "x"))


def test_malformed_json_fails_closed():
    with pytest.raises(TransitionPolicyError, match="not valid JSON"):
        deserialize_transition_policy("{broken")
