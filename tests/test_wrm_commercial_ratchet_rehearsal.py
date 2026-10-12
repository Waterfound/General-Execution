from scripts.run_wrm_commercial_ratchet_rehearsal import current_wrm_rehearsal


def test_current_wrm_rehearsal_selects_commercial_discovery_over_internal_support():
    result = current_wrm_rehearsal()
    decision = result["decision"]
    assert decision["disposition"] == "SELECTED"
    assert decision["selected_frontier_id"] == "wrm-commercial-discovery-pr46"
    assert decision["selected_kind"] == "COMPETITIVE_DIFFERENTIATION"
    assert decision["classification"] == "DIRECT_COMMERCIAL"
    assert decision["authority_created"] is False
    assert decision["execution_triggered"] is False
    assert "wrm-external-demand:human_gate" in decision["rejected_frontiers"]
