import pytest
from general_execution.revenue_value_proof import project_value_proof

def observation():
    return {
        "workflow_id": "synthetic-fixture",
        "representative_workflow_class": "unit-test",
        "terminal_state": "DONE_TECHNICAL",
        "intent_timestamp": "2026-10-07T12:00:00Z",
        "terminal_timestamp": "2026-10-07T12:05:00Z",
        "autonomous_resolutions": 4,
        "resolution_opportunities": 5,
        "provenance_items_present": 4,
        "provenance_items_expected": 5,
    }

def test_derived_metrics_only_from_observations():
    result = project_value_proof(observation())
    assert result["derived"]["mission_completion_latency_seconds"] == 300
    assert result["derived"]["autonomous_resolution_rate"] == 0.8
    assert result["derived"]["provenance_coverage"] == 0.8
    assert result["authority_created"] is False
    assert result["execution_triggered"] is False
    assert all(value is None for value in result["unproven_value_claims"].values())

def test_unknown_values_remain_unknown():
    item = observation()
    item["terminal_state"] = "HUMAN_GATE"
    item["terminal_timestamp"] = None
    item["autonomous_resolutions"] = None
    assert project_value_proof(item)["derived"]["mission_completion_latency_seconds"] is None
    assert project_value_proof(item)["derived"]["autonomous_resolution_rate"] is None

@pytest.mark.parametrize("field,value", [
    ("autonomous_resolutions", 6),
    ("provenance_items_present", 6),
    ("terminal_timestamp", "2026-10-07T11:00:00Z"),
    ("intent_timestamp", "2026-10-07T12:00:00"),
    ("retries", -1),
])
def test_inconsistent_observations_fail_closed(field, value):
    item = observation()
    item[field] = value
    with pytest.raises(ValueError):
        project_value_proof(item)
