from __future__ import annotations

import pytest

from general_execution.continuity_adapters import (
    candidate_from_mapping,
    conversation_from_mapping,
    durable_from_mapping,
    provider_from_mapping,
    repository_from_mapping,
)
from general_execution.continuity_check import ContinuitySnapshot, inspect_continuity
from general_execution.liveness_evidence import apply_liveness_to_snapshot_mapping


REV = "299549f2af4222e9ac81beacdaa24da6d8fef55c"


def base():
    return {
        "checked_at": "2026-10-07T01:55:00Z",
        "query": "GOP-001",
        "candidates": [{
            "workstream_id": "GOP-001",
            "canonical_name": "Governed Operator Plane",
            "repository": "Waterfound/General-Execution",
            "branch": "colony/governed-operator-plane-ge-001",
        }],
        "conversation": {"assessment": "CONVERSATION_STATE_UNKNOWN"},
        "repository": {
            "repository": "Waterfound/General-Execution",
            "main_revision": REV,
            "branch": "colony/governed-operator-plane-ge-001",
            "branch_head": REV,
        },
        "durable": {
            "validated": True,
            "workstream_id": "GOP-001",
            "bound_repository": "Waterfound/General-Execution",
            "bound_branch": "colony/governed-operator-plane-ge-001",
            "bound_branch_head": REV,
            "current_frontier": "continuity-liveness-hardening",
            "completed_frontiers": ["operator-plane-contract"],
            "admissible_next": ["continuity-liveness-hardening"],
            "execution_expected": True,
        },
    }


def report(data):
    data = apply_liveness_to_snapshot_mapping(data)
    snap = ContinuitySnapshot(
        checked_at=data["checked_at"],
        query=data["query"],
        candidates=tuple(candidate_from_mapping(x) for x in data["candidates"]),
        conversation=conversation_from_mapping(data.get("conversation")),
        repository=repository_from_mapping(data.get("repository")),
        durable=durable_from_mapping(data.get("durable")),
        provider=provider_from_mapping(data.get("provider")),
    )
    return inspect_continuity(snap)


def liveness(kind, *, detail=None, extra=None):
    obs = [{"sequence": 0, "kind": kind, "observed_at": "2026-10-07T01:56:00Z"}]
    if detail:
        obs[0]["detail"] = detail
    if extra:
        obs.extend(extra)
    return {
        "workstream_id": "GOP-001",
        "repository": "Waterfound/General-Execution",
        "source_revision": REV,
        "provider": "github-actions",
        "dispatch_identity": "gop-live-001",
        "execution_expected": True,
        "observations": obs,
    }


def test_heartbeat_projects_active_without_time_threshold():
    data = base()
    data["liveness"] = liveness("heartbeat")
    out = report(data)
    assert out.development_verdict == "DEVELOPMENT_PROGRESSING"
    assert out.infrastructure_status == "HEALTHY"


def test_provider_unavailable_is_infrastructure_not_workload_failure():
    data = base()
    data["liveness"] = liveness("provider_unavailable", detail="runner allocation unavailable")
    out = report(data)
    assert out.development_verdict == "CHECKPOINTED_RESUMABLE"
    assert out.infrastructure_status == "PROVIDER_RUNNER_UNAVAILABLE"


def test_recovery_exhaustion_can_prove_stalled_only_with_durable_frontier():
    data = base()
    data["liveness"] = liveness(
        "started",
        extra=[{
            "sequence": 1,
            "kind": "recovery_exhausted",
            "observed_at": "2026-10-07T01:57:00Z",
            "detail": "bounded recovery contract exhausted",
        }],
    )
    out = report(data)
    assert out.development_verdict == "DEVELOPMENT_STALLED"


def test_workload_failure_remains_failure():
    data = base()
    data["liveness"] = liveness("workload_failed", detail="test workload failed")
    out = report(data)
    assert out.development_verdict == "FAILED"


def test_recovery_exhaustion_without_durable_state_fails_closed():
    data = base()
    del data["durable"]
    data["liveness"] = liveness(
        "started",
        extra=[{
            "sequence": 1,
            "kind": "recovery_exhausted",
            "observed_at": "2026-10-07T01:57:00Z",
        }],
    )
    with pytest.raises(ValueError, match="requires existing durable-state evidence"):
        apply_liveness_to_snapshot_mapping(data)


def test_liveness_revision_conflict_fails_closed():
    data = base()
    data["liveness"] = liveness("heartbeat")
    data["liveness"]["source_revision"] = "0" * 40
    with pytest.raises(ValueError, match="revision binding conflicts"):
        apply_liveness_to_snapshot_mapping(data)
