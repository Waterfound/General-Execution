from dataclasses import replace

import pytest

from general_execution.abundant_resource import (
    AbundantResourceAuthorityEnvelope,
    AbundantResourceError,
    ResourceEconomics,
    ResourceOffer,
    admission_to_dict,
    admit_abundant_resources,
    verify_abundant_resource_admission,
)


def envelope(**changes):
    base = AbundantResourceAuthorityEnvelope(
        envelope_id="acrd-test",
        authority_ref="authority://acrd/test",
        allowed_resource_ids=("included", "local", "paid", "unknown", "fallback", "large"),
        allowed_capabilities=("reasoning", "verification", "simulation"),
        max_total_parallelism=8,
    )
    return replace(base, **changes)


def offer(resource_id, economics, parallelism=2, **changes):
    base = ResourceOffer(
        resource_id=resource_id,
        capabilities=("reasoning",),
        max_parallelism=parallelism,
        economics=economics,
        incremental_cost_cents_per_invocation=0,
        automatic_paid_fallback=False,
        available=True,
        evidence_refs=(f"evidence://{resource_id}",),
    )
    return replace(base, **changes)


def test_admits_zero_incremental_included_and_local_capacity():
    decision = admit_abundant_resources(
        envelope(),
        (
            offer("included", ResourceEconomics.INCLUDED_ALLOWANCE, 3),
            offer("local", ResourceEconomics.OWNED_LOCAL, 4),
        ),
    )
    assert decision.admitted_resource_ids == ("included", "local")
    assert decision.admitted_parallelism == 7
    assert decision.incremental_paid_spend_cents == 0
    assert decision.authority_created is False
    assert decision.execution_triggered is False


def test_paid_and_unknown_resources_are_not_abundant():
    decision = admit_abundant_resources(
        envelope(),
        (
            offer("paid", ResourceEconomics.PAID),
            offer("unknown", ResourceEconomics.UNKNOWN),
        ),
    )
    assert decision.admitted_resource_ids == ()
    reasons = {item.resource_id: item.reasons for item in decision.rejected}
    assert "economics_not_abundant:paid" in reasons["paid"]
    assert "economics_not_abundant:unknown" in reasons["unknown"]


def test_included_resource_with_paid_fallback_fails_closed():
    decision = admit_abundant_resources(
        envelope(),
        (
            offer(
                "fallback",
                ResourceEconomics.INCLUDED_ALLOWANCE,
                automatic_paid_fallback=True,
            ),
        ),
    )
    assert decision.admitted_resource_ids == ()
    assert decision.rejected[0].reasons == ("automatic_paid_fallback_enabled",)


def test_nonzero_cost_cannot_be_declared_abundant():
    with pytest.raises(AbundantResourceError):
        offer(
            "included",
            ResourceEconomics.INCLUDED_ALLOWANCE,
            incremental_cost_cents_per_invocation=1,
        )


def test_global_parallelism_envelope_is_fail_closed_not_partially_mutated():
    decision = admit_abundant_resources(
        envelope(max_total_parallelism=5),
        (
            offer("included", ResourceEconomics.INCLUDED_ALLOWANCE, 4),
            offer("local", ResourceEconomics.OWNED_LOCAL, 3),
        ),
    )
    assert decision.admitted_resource_ids == ("included",)
    assert decision.admitted_parallelism == 4
    rejected = {item.resource_id: item.reasons for item in decision.rejected}
    assert rejected["local"] == ("resource_capacity_exceeds_remaining_envelope",)


def test_resource_outside_authority_is_rejected():
    external = ResourceOffer(
        resource_id="external",
        capabilities=("reasoning",),
        max_parallelism=1,
        economics=ResourceEconomics.ZERO_COST_PROVIDER,
        incremental_cost_cents_per_invocation=0,
        automatic_paid_fallback=False,
        available=True,
        evidence_refs=("evidence://external",),
    )
    decision = admit_abundant_resources(envelope(), (external,))
    assert decision.admitted_resource_ids == ()
    assert "resource_outside_authority_envelope" in decision.rejected[0].reasons


def test_replay_detects_tampering():
    offers = (offer("included", ResourceEconomics.INCLUDED_ALLOWANCE, 3),)
    decision = admission_to_dict(admit_abundant_resources(envelope(), offers))
    assert verify_abundant_resource_admission(envelope(), offers, decision)
    tampered = dict(decision)
    tampered["admitted_parallelism"] = 99
    assert not verify_abundant_resource_admission(envelope(), offers, tampered)


def test_duplicate_resource_identity_is_rejected():
    same = offer("included", ResourceEconomics.INCLUDED_ALLOWANCE)
    with pytest.raises(AbundantResourceError):
        admit_abundant_resources(envelope(), (same, same))
