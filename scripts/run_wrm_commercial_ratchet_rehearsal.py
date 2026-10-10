"""Executable WRM-CPR-001 current-state rehearsal.

Projects the currently known Revenue Mission frontiers without dispatching them.
"""

from __future__ import annotations

import json

from general_execution.commercial_progress_ratchet import (
    CommercialFrontier,
    FrontierKind,
    select_commercial_frontier,
)


def current_wrm_rehearsal() -> dict[str, object]:
    frontiers = (
        CommercialFrontier(
            frontier_id="wrm-commercial-discovery-pr46",
            kind=FrontierKind.COMPETITIVE_DIFFERENTIATION,
            expected_information_gain=85,
            evidence_refs=(
                "github://Waterfound/General-Execution/pull/46",
            ),
        ),
        CommercialFrontier(
            frontier_id="wrm-commercial-evidence-pr43",
            kind=FrontierKind.INTERNAL_SUPPORT,
            expected_information_gain=95,
            named_commercial_predicate="admit_exact_representative_workflow_evidence",
            evidence_refs=(
                "github://Waterfound/General-Execution/pull/43",
            ),
        ),
        CommercialFrontier(
            frontier_id="wrm-persistent-runtime-pr44",
            kind=FrontierKind.INTERNAL_SUPPORT,
            expected_information_gain=100,
            named_commercial_predicate="prove_unattended_cycle_when_a_selected_experiment_requires_it",
            evidence_refs=(
                "github://Waterfound/General-Execution/pull/44",
            ),
        ),
        CommercialFrontier(
            frontier_id="wrm-external-demand",
            kind=FrontierKind.EXTERNAL_DEMAND,
            expected_information_gain=100,
            human_gate=True,
            evidence_refs=(
                "authority://waterfound/revenue-mission/customer-outreach-not-yet-authorized",
            ),
        ),
    )
    decision = select_commercial_frontier(
        frontiers,
        technical_capability_proven=True,
    )
    return {
        "schema": "wrm.cpr.current-state-rehearsal.v1",
        "frontiers": [frontier.frontier_id for frontier in frontiers],
        "decision": {
            "disposition": decision.disposition.value,
            "selected_frontier_id": decision.selected_frontier_id,
            "selected_kind": decision.selected_kind.value if decision.selected_kind else None,
            "classification": decision.classification,
            "reasons": list(decision.reasons),
            "rejected_frontiers": list(decision.rejected_frontiers),
            "authority_created": decision.authority_created,
            "execution_triggered": decision.execution_triggered,
        },
    }


if __name__ == "__main__":
    print(json.dumps(current_wrm_rehearsal(), indent=2, sort_keys=True))
