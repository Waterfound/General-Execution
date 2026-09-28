from __future__ import annotations

from general_execution.continuity_adapters import candidate_from_mapping, durable_from_mapping, repository_from_mapping
from general_execution.continuity_check import (
    ContinuitySnapshot,
    DurableStateEvidence,
    FailureScope,
    ProviderEvidence,
    ProviderState,
    WorkstreamCandidate,
    inspect_continuity,
)


def test_mapping_adapters_freeze_sequences_to_tuples():
    c = candidate_from_mapping({"workstream_id":"x","canonical_name":"X","aliases":["alias"]})
    d = durable_from_mapping({"validated":True,"workstream_id":"x","completed_frontiers":["X-00"],"admissible_next":["X-01"]})
    assert c.aliases == ("alias",)
    assert d is not None and d.admissible_next == ("X-01",)


def test_real_rde_pr263_replay_done_canonical():
    c = WorkstreamCandidate("rde", "FAE — Representative Device Evidence Readiness", repository="Waterfound/FAE-testnet", branch="colony/fae-representative-device-evidence-readiness-001")
    r = repository_from_mapping({
        "repository":"Waterfound/FAE-testnet",
        "main_revision":"a52fa9eb7747d227245e4e38b522c0b56888b503",
        "branch":"colony/fae-representative-device-evidence-readiness-001",
        "branch_head":"53bb05f95fe1a31d6414a15303bed6d08cccfb91",
        "pull_request_number":263,
        "pull_request_state":"closed",
        "pull_request_merged":True,
        "canonical_contains_workstream":True
    })
    report = inspect_continuity(ContinuitySnapshot("2026-09-28T21:50:00Z", "Representative Device Evidence Readiness", (c,), repository=r))
    assert report.development_verdict == "DONE_CANONICAL"


def test_real_be06_oracle_capacity_replay_condition_wait():
    c = WorkstreamCandidate("be06", "FAE — Block Explorer BE-06", repository="Waterfound/FAE-testnet", branch="lab/block-explorer-be06-a1-capacity-block-20260923", aliases=("Block Explorer", "BE-06"))
    r = repository_from_mapping({
        "repository":"Waterfound/FAE-testnet",
        "branch":"lab/block-explorer-be06-a1-capacity-block-20260923",
        "branch_head":"d4fc49bd1f3d436b4a16615d40792377e0fa0de7",
        "pull_request_number":257,
        "pull_request_state":"open",
        "pull_request_merged":False
    })
    d = DurableStateEvidence(
        validated=True,
        workstream_id="be06",
        bound_repository="Waterfound/FAE-testnet",
        bound_branch="lab/block-explorer-be06-a1-capacity-block-20260923",
        bound_branch_head="d4fc49bd1f3d436b4a16615d40792377e0fa0de7",
        current_frontier="BE-06",
        wake_condition="Oracle sa-saopaulo-1 A1 Always Free host capacity becomes available",
    )
    report = inspect_continuity(ContinuitySnapshot("2026-09-28T21:50:00Z", "Block Explorer", (c,), repository=r, durable=d))
    assert report.development_verdict == "CONDITION_WAIT"


def test_real_systems_docs_provider_failure_does_not_override_canonical_done():
    c = WorkstreamCandidate("systems-docs", "Waterfound Systems Documentation Foundation", repository="Waterfound/Systems", branch="colony/systems-documentation-foundation-001")
    r = repository_from_mapping({
        "repository":"Waterfound/Systems",
        "main_revision":"21cfbd04728e64dcd9373a074667bfcf89b8c771",
        "branch":"colony/systems-documentation-foundation-001",
        "branch_head":"1ee8efd2e806919ff04535bdc12717e932c73ee1",
        "pull_request_number":1,
        "pull_request_state":"closed",
        "pull_request_merged":True,
        "canonical_contains_workstream":True
    })
    p = ProviderEvidence("github-actions", ProviderState.FAILED, subject_revision="1ee8efd2e806919ff04535bdc12717e932c73ee1", failure_scope=FailureScope.PROVIDER, detail="failed before any step started")
    report = inspect_continuity(ContinuitySnapshot("2026-09-28T21:50:00Z", "Waterfound Systems Documentation Foundation", (c,), repository=r, provider=p))
    assert report.development_verdict == "DONE_CANONICAL"
    assert report.infrastructure_status == "PROVIDER_FAILURE"
