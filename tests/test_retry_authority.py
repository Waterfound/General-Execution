from dataclasses import replace

import pytest

from general_execution import (
    FailureObservation,
    RetryAuthorityError,
    RetryDecision,
    RetryPolicy,
    decide_retry,
)

D = "sha256:" + "b" * 64
E = "sha256:" + "e" * 64


def policy(**changes):
    values = dict(
        policy_id="durable-retry-v1",
        revision="1",
        authority_ref="artifact://retry-authority",
        authority_digest=D,
        network_retry_limit=2,
        throttle_retry_limit=3,
        throttle_initial_backoff_seconds=5,
        throttle_max_backoff_seconds=12,
        unknown_reproduction_limit=1,
    )
    values.update(changes)
    return RetryPolicy(**values)


def observation(failure_class, **changes):
    values = dict(
        failure_class=failure_class,
        failure_code=f"failure.{failure_class}",
        evidence_digest=E,
    )
    values.update(changes)
    return FailureObservation(**values)


def test_network_timeout_allows_exactly_two_bounded_retries():
    p = policy()
    first = decide_retry(p, observation("network_timeout", automatic_retry_count=0))
    second = decide_retry(p, observation("network_timeout", automatic_retry_count=1))
    exhausted = decide_retry(p, observation("network_timeout", automatic_retry_count=2))

    assert first.disposition == "retry"
    assert second.disposition == "retry"
    assert first.automatic_retry_authorized
    assert second.automatic_retry_authorized
    assert first.authority_ref == p.authority_ref
    assert first.authority_digest == p.authority_digest
    assert not first.transport_authority
    assert exhausted.disposition == "diagnose"
    assert not exhausted.automatic_retry_authorized
    assert exhausted.authority_ref is None


def test_provider_throttle_uses_bounded_exponential_backoff():
    p = policy()
    decisions = [
        decide_retry(
            p,
            observation("provider_throttled", automatic_retry_count=count),
        )
        for count in (0, 1, 2)
    ]
    assert [decision.delay_seconds for decision in decisions] == [5, 10, 12]
    assert all(decision.automatic_retry_authorized for decision in decisions)

    exhausted = decide_retry(
        p,
        observation("provider_throttled", automatic_retry_count=3),
    )
    assert exhausted.disposition == "diagnose"
    assert exhausted.delay_seconds == 0


def test_deterministic_assertion_never_retries():
    decision = decide_retry(policy(), observation("deterministic_assertion"))
    assert decision.disposition == "diagnose"
    assert not decision.automatic_retry_authorized
    assert not decision.independent_reproduction_authorized
    assert decision.authority_ref is None


def test_unknown_failure_gets_one_reproduction_then_diagnosis():
    p = policy()
    first = decide_retry(
        p,
        observation("unknown_failure", independent_reproduction_count=0),
    )
    second = decide_retry(
        p,
        observation("unknown_failure", independent_reproduction_count=1),
    )
    assert first.disposition == "independent_reproduction"
    assert first.independent_reproduction_authorized
    assert first.authority_ref == p.authority_ref
    assert first.authority_digest == p.authority_digest
    assert not first.transport_authority
    assert second.disposition == "diagnose"
    assert second.authority_ref is None


def test_cost_boundary_stops_immediately_without_human_authority():
    decision = decide_retry(
        policy(),
        observation(
            "cost_boundary",
            boundary_detail="preauthorized budget ceiling reached",
        ),
    )
    assert decision.disposition == "stop"
    assert decision.next_action_ref == "stop://cost-boundary"
    assert not decision.human_required
    assert decision.authority_boundary is None
    assert decision.authority_ref is None


@pytest.mark.parametrize(
    "failure_class,boundary",
    [
        ("security_boundary", "security-sensitive operation reached"),
        ("authority_boundary", "release authority required"),
    ],
)
def test_security_and_authority_boundaries_stop_at_human_gate(
    failure_class,
    boundary,
):
    decision = decide_retry(
        policy(),
        observation(failure_class, boundary_detail=boundary),
    )
    assert decision.disposition == "human_gate"
    assert decision.human_required
    assert decision.authority_boundary == boundary
    assert not decision.automatic_retry_authorized
    assert not decision.independent_reproduction_authorized
    assert decision.authority_ref is None
    assert not decision.transport_authority


def test_failure_observation_requires_evidence_binding():
    with pytest.raises(RetryAuthorityError, match="evidence_digest"):
        observation("network_timeout", evidence_digest="bad")


def test_boundary_failure_requires_explicit_detail():
    with pytest.raises(RetryAuthorityError, match="requires boundary_detail"):
        observation("authority_boundary")
    with pytest.raises(RetryAuthorityError, match="requires boundary_detail"):
        observation("cost_boundary")


def test_nonboundary_failure_cannot_smuggle_authority_boundary():
    with pytest.raises(
        RetryAuthorityError,
        match="valid only for boundary failures",
    ):
        observation("network_timeout", boundary_detail="hidden authority")


def test_retry_policy_requires_external_authority_artifact():
    with pytest.raises(RetryAuthorityError, match="authority_ref"):
        policy(authority_ref="")
    with pytest.raises(RetryAuthorityError, match="sha256"):
        policy(authority_digest="bad")


def test_unknown_reproduction_limit_is_frozen_to_one():
    with pytest.raises(RetryAuthorityError, match="frozen to exactly 1"):
        policy(unknown_reproduction_limit=2)


def test_negative_limits_and_counts_fail_closed():
    with pytest.raises(RetryAuthorityError, match="non-negative integer"):
        policy(network_retry_limit=-1)
    with pytest.raises(RetryAuthorityError, match="non-negative integer"):
        observation("network_timeout", automatic_retry_count=-1)


def test_backoff_ceiling_must_not_be_below_initial():
    with pytest.raises(RetryAuthorityError, match="must be >= initial backoff"):
        policy(
            throttle_initial_backoff_seconds=10,
            throttle_max_backoff_seconds=5,
        )


def test_retry_decision_cannot_grant_transport_authority():
    normal = decide_retry(policy(), observation("network_timeout"))
    with pytest.raises(
        RetryAuthorityError,
        match="cannot grant transport authority",
    ):
        replace(normal, transport_authority=True)


def test_retry_decision_requires_bounded_authority_artifact():
    normal = decide_retry(policy(), observation("network_timeout"))
    with pytest.raises(
        RetryAuthorityError,
        match="requires bounded authority artifact",
    ):
        replace(normal, authority_ref=None)


def test_diagnose_and_stop_cannot_carry_authority():
    diagnose = decide_retry(policy(), observation("deterministic_assertion"))
    with pytest.raises(RetryAuthorityError, match="cannot carry authority or delay"):
        replace(diagnose, authority_ref="artifact://bad", authority_digest=D)

    stopped = decide_retry(
        policy(),
        observation("cost_boundary", boundary_detail="budget reached"),
    )
    with pytest.raises(RetryAuthorityError, match="cannot carry authority or delay"):
        replace(stopped, authority_ref="artifact://bad", authority_digest=D)


def test_retry_decision_identity_is_deterministic():
    p = policy()
    o = observation("network_timeout")
    left = decide_retry(p, o)
    right = decide_retry(p, o)
    assert left == right
    assert left.digest == right.digest
    assert left.decision_id == right.decision_id


def test_unsupported_failure_class_fails_closed():
    with pytest.raises(RetryAuthorityError, match="unsupported failure class"):
        FailureObservation(
            failure_class="mystery",
            failure_code="failure.mystery",
            evidence_digest=E,
        )
