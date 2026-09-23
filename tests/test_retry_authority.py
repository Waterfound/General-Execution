import pytest

from general_execution import (
    FailureObservation,
    RetryAuthorityError,
    RetryDecision,
    RetryPolicy,
    decide_retry,
)

D = "sha256:" + "b" * 64


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
    )
    values.update(changes)
    return FailureObservation(**values)


def test_network_timeout_allows_only_bounded_retries():
    p = policy()
    first = decide_retry(p, observation("network_timeout", automatic_retry_count=0))
    second = decide_retry(p, observation("network_timeout", automatic_retry_count=1))
    exhausted = decide_retry(p, observation("network_timeout", automatic_retry_count=2))

    assert first.disposition == "retry"
    assert second.disposition == "retry"
    assert first.automatic_retry_authorized
    assert second.automatic_retry_authorized
    assert exhausted.disposition == "diagnose"
    assert not exhausted.automatic_retry_authorized


def test_provider_throttle_uses_bounded_exponential_backoff():
    p = policy()
    delays = [
        decide_retry(
            p,
            observation("provider_throttled", automatic_retry_count=count),
        ).delay_seconds
        for count in (0, 1, 2)
    ]
    assert delays == [5, 10, 12]

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


def test_unknown_failure_gets_one_independent_reproduction_then_diagnosis():
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
    assert not first.automatic_retry_authorized
    assert second.disposition == "diagnose"


@pytest.mark.parametrize(
    "failure_class,boundary",
    [
        ("cost_boundary", "preauthorized budget ceiling reached"),
        ("security_boundary", "security-sensitive operation reached"),
        ("authority_boundary", "release authority required"),
    ],
)
def test_boundaries_stop_at_human_gate(failure_class, boundary):
    decision = decide_retry(
        policy(),
        observation(failure_class, boundary_detail=boundary),
    )
    assert decision.disposition == "human_gate"
    assert decision.human_required
    assert decision.authority_boundary == boundary
    assert not decision.automatic_retry_authorized
    assert not decision.independent_reproduction_authorized
    assert not decision.transport_authority


def test_boundary_failure_requires_explicit_boundary_detail():
    with pytest.raises(
        RetryAuthorityError,
        match="requires boundary_detail",
    ):
        observation("authority_boundary")


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


def test_negative_limits_and_counts_fail_closed():
    with pytest.raises(RetryAuthorityError, match="non-negative integer"):
        policy(network_retry_limit=-1)
    with pytest.raises(RetryAuthorityError, match="non-negative integer"):
        observation("network_timeout", automatic_retry_count=-1)


def test_backoff_ceiling_must_not_be_below_initial():
    with pytest.raises(
        RetryAuthorityError,
        match="must be >= initial backoff",
    ):
        policy(
            throttle_initial_backoff_seconds=10,
            throttle_max_backoff_seconds=5,
        )


def test_retry_decision_cannot_grant_transport_authority():
    with pytest.raises(
        RetryAuthorityError,
        match="cannot grant transport authority",
    ):
        RetryDecision(
            policy_digest=policy().digest,
            observation_digest=observation("network_timeout").digest,
            disposition="retry",
            next_action_ref="retry://network-timeout",
            automatic_retry_authorized=True,
            transport_authority=True,
        )


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
        )
