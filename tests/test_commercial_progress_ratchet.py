import pytest

from general_execution.commercial_progress_ratchet import (
    CommercialFrontier,
    CommercialRatchetError,
    FrontierKind,
    RatchetDisposition,
    select_commercial_frontier,
)


def frontier(frontier_id, kind, gain, **overrides):
    values = dict(
        frontier_id=frontier_id,
        kind=kind,
        expected_information_gain=gain,
    )
    values.update(overrides)
    return CommercialFrontier(**values)


def test_direct_commercial_work_beats_internal_instrumentation_even_with_lower_gain():
    decision = select_commercial_frontier(
        (
            frontier(
                "runtime-preflight",
                FrontierKind.INTERNAL_SUPPORT,
                100,
                named_commercial_predicate="prove live runtime dependency",
            ),
            frontier(
                "competitive-falsification",
                FrontierKind.COMPETITIVE_DIFFERENTIATION,
                20,
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.disposition is RatchetDisposition.SELECTED
    assert decision.selected_frontier_id == "competitive-falsification"
    assert decision.classification == "DIRECT_COMMERCIAL"


def test_support_without_named_commercial_predicate_is_rejected_after_capability_proof():
    decision = select_commercial_frontier(
        (
            frontier("more-telemetry", FrontierKind.INTERNAL_SUPPORT, 90),
            frontier(
                "runtime-for-specific-experiment",
                FrontierKind.INTERNAL_SUPPORT,
                30,
                named_commercial_predicate="measure recovery during candidate product proof",
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.selected_frontier_id == "runtime-for-specific-experiment"
    assert "more-telemetry:support_without_named_commercial_predicate" in decision.rejected_frontiers


def test_support_can_be_selected_before_capability_proof_without_fake_commercial_predicate():
    decision = select_commercial_frontier(
        (frontier("initial-instrumentation", FrontierKind.INTERNAL_SUPPORT, 50),),
        technical_capability_proven=False,
    )
    assert decision.disposition is RatchetDisposition.SELECTED
    assert decision.classification == "SUPPORT_ONLY"


def test_later_human_gate_does_not_mask_machine_admissible_commercial_work():
    decision = select_commercial_frontier(
        (
            frontier(
                "customer-outreach",
                FrontierKind.EXTERNAL_DEMAND,
                100,
                human_gate=True,
            ),
            frontier(
                "buyer-problem-research",
                FrontierKind.BUYER_PROBLEM,
                40,
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.disposition is RatchetDisposition.SELECTED
    assert decision.selected_frontier_id == "buyer-problem-research"


def test_human_gate_only_when_no_machine_admissible_successor_exists():
    decision = select_commercial_frontier(
        (
            frontier(
                "customer-outreach",
                FrontierKind.EXTERNAL_DEMAND,
                100,
                human_gate=True,
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.disposition is RatchetDisposition.HUMAN_GATE
    assert decision.selected_frontier_id is None


def test_unsatisfied_product_prerequisite_keeps_competitive_falsification_ahead():
    decision = select_commercial_frontier(
        (
            frontier(
                "build-product",
                FrontierKind.NARROW_PRODUCT_PROOF,
                90,
                prerequisite_satisfied=False,
            ),
            frontier(
                "test-substitute-overlap",
                FrontierKind.COMPETITIVE_DIFFERENTIATION,
                60,
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.selected_frontier_id == "test-substitute-overlap"
    assert "build-product:prerequisite_unsatisfied" in decision.rejected_frontiers


def test_information_gain_is_primary_within_direct_commercial_frontiers():
    decision = select_commercial_frontier(
        (
            frontier("buyer-study", FrontierKind.BUYER_PROBLEM, 80),
            frontier("candidate-proof", FrontierKind.NARROW_PRODUCT_PROOF, 30),
        ),
        technical_capability_proven=True,
    )
    assert decision.selected_frontier_id == "buyer-study"


def test_later_stage_breaks_information_gain_tie():
    decision = select_commercial_frontier(
        (
            frontier("buyer-study", FrontierKind.BUYER_PROBLEM, 50),
            frontier("demand-proof", FrontierKind.EXTERNAL_DEMAND, 50),
        ),
        technical_capability_proven=True,
    )
    assert decision.selected_frontier_id == "demand-proof"


def test_condition_wait_when_only_unsatisfied_machine_frontiers_exist():
    decision = select_commercial_frontier(
        (
            frontier(
                "product-proof",
                FrontierKind.NARROW_PRODUCT_PROOF,
                50,
                prerequisite_satisfied=False,
            ),
        ),
        technical_capability_proven=True,
    )
    assert decision.disposition is RatchetDisposition.CONDITION_WAIT


def test_invalid_information_gain_fails_closed():
    with pytest.raises(CommercialRatchetError):
        frontier("bad", FrontierKind.BUYER_PROBLEM, 101)


def test_duplicate_frontier_ids_fail_closed():
    with pytest.raises(CommercialRatchetError):
        select_commercial_frontier(
            (
                frontier("same", FrontierKind.BUYER_PROBLEM, 10),
                frontier("same", FrontierKind.COMPETITIVE_DIFFERENTIATION, 20),
            ),
            technical_capability_proven=True,
        )
