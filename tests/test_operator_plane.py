from __future__ import annotations

from copy import deepcopy

import pytest

from general_execution.operator_plane import build_operator_projection, render_operator_projection


GE = "7c01302bd5be26fc93102652a161852c068a59da"
BC = "35326abd4e5897cafeb53449d9a253bb7ecf693b"
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def sample():
    return {
        "schema_version": "ge.operator-plane-input.v1",
        "portfolio_id": "governed-operator-plane-001",
        "observed_at": "2026-10-07T02:00:00Z",
        "sources": [
            {
                "source_id": "build-colony",
                "system": "Build Colony",
                "repository": "Waterfound/Build-Colony",
                "revision": BC,
                "artifact_ref": "github-actions://Waterfound/Build-Colony/actions/runs/37559186209",
                "artifact_digest": D1,
            },
            {
                "source_id": "general-execution",
                "system": "General Execution",
                "repository": "Waterfound/General-Execution",
                "revision": GE,
                "artifact_ref": "github-actions://Waterfound/General-Execution/actions/runs/37559540046",
                "artifact_digest": D2,
            },
        ],
        "lanes": [
            {
                "lane_id": "GOP-03-LIVENESS",
                "workstream_id": "GOP-001",
                "owner_system": "General Execution",
                "repository": "Waterfound/General-Execution",
                "source_revision": GE,
                "state": "DONE_TECHNICAL",
                "observed_at": "2026-10-07T01:56:43Z",
                "source_refs": ["general-execution"],
                "evidence_refs": ["github-actions://Waterfound/General-Execution/actions/runs/37559540046"],
                "current_frontier": "continuity-liveness-hardening",
                "executor": "github-actions",
                "dispatch_identity": "gop-ge-liveness-001",
                "blocking_gate": None,
            },
            {
                "lane_id": "GOP-01-CONTRACT",
                "workstream_id": "GOP-001",
                "owner_system": "Build Colony",
                "repository": "Waterfound/Build-Colony",
                "source_revision": BC,
                "state": "DONE_TECHNICAL",
                "observed_at": "2026-10-07T01:52:09Z",
                "source_refs": ["build-colony"],
                "evidence_refs": ["github-actions://Waterfound/Build-Colony/actions/runs/37559186209"],
                "current_frontier": "operator-plane-contract",
                "executor": "github-actions",
                "dispatch_identity": None,
                "blocking_gate": None,
            },
        ],
    }


def test_projection_is_deterministic_read_only_and_sorted():
    data = sample()
    projection = build_operator_projection(data)
    assert [lane["lane_id"] for lane in projection["lanes"]] == [
        "GOP-01-CONTRACT",
        "GOP-03-LIVENESS",
    ]
    assert projection["authority_created"] is False
    assert projection["execution_triggered"] is False
    assert projection["mutable_state_owned"] is False
    assert projection["summary"]["lane_count"] == 2
    assert projection == build_operator_projection({
        **data,
        "sources": list(reversed(data["sources"])),
        "lanes": list(reversed(data["lanes"])),
    })


def test_unknown_control_fields_fail_closed():
    data = sample()
    data["actions"] = [{"kind": "dispatch"}]
    with pytest.raises(ValueError, match="unknown"):
        build_operator_projection(data)


def test_stale_lane_revision_fails_closed():
    data = sample()
    data["lanes"][0]["source_revision"] = "0" * 40
    with pytest.raises(ValueError, match="conflicts"):
        build_operator_projection(data)


def test_unknown_source_reference_fails_closed():
    data = sample()
    data["lanes"][0]["source_refs"] = ["missing"]
    with pytest.raises(ValueError, match="unknown source"):
        build_operator_projection(data)


def test_duplicate_lane_identity_fails_closed():
    data = sample()
    data["lanes"][1]["lane_id"] = data["lanes"][0]["lane_id"]
    with pytest.raises(ValueError, match="lane_id values must be unique"):
        build_operator_projection(data)


def test_render_contains_no_action_surface():
    projection = build_operator_projection(sample())
    rendered = render_operator_projection(projection)
    assert "Governed Operator Plane" in rendered
    assert "Read-only" in rendered
    assert "execution_triggered=false" in rendered
