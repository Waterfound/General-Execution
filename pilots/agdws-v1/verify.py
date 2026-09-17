from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence.json"

EXPECTED = {
    "filter_wrong_phase": {
        "di": True,
        "eligible": ["lane-a", "lane-b", "lane-c", "lane-d"],
        "filtered": ["lane-e", "lane-f", "lane-g", "lane-h"],
        "reasons": ["generic_development_without_demonstrated_engineering_defect"],
    },
    "filter_stopped_routes": {
        "di": False,
        "eligible": ["route-a", "route-b"],
        "filtered": ["route-c", "route-d", "route-e", "route-f"],
    },
    "saturation_suspend": {"state": "deferred", "suspended": True},
    "material_reopen": {"state": "active", "suspended": False},
    "serial_dependency": {"eligible": ["dependency-a"]},
    "unclassified_gate": {
        "di": True,
        "eligible": [],
        "filtered": ["generic-a"],
        "reasons": ["active_gate_unclassified"],
    },
    "two_zero_yield": {
        "di": True,
        "eligible": ["route-a"],
        "reasons": ["two_consecutive_zero_yield_runs_without_hard_external_gate"],
    },
    "missing_binding": {"outcome": "ERROR"},
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    raw = EVIDENCE.read_bytes()
    packet = json.loads(raw)

    if packet.get("schema_version") != 1:
        fail("unexpected evidence schema")
    if packet.get("privacy") != "sanitized_no_private_source_or_project_labels":
        fail("privacy boundary marker missing")

    bindings = packet.get("origin_artifact_bindings")
    if not isinstance(bindings, dict) or set(bindings) != {
        "work_selection_git_blob_sha1",
        "test_work_selection_git_blob_sha1",
    }:
        fail("origin artifact bindings malformed")
    for key, value in bindings.items():
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
            fail(f"{key} is not a content-addressed Git blob id")

    cases = packet.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED):
        fail("unexpected case count")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        fail("duplicate case id")
    if set(ids) != set(EXPECTED):
        fail("case set differs from frozen public oracle")

    for case in cases:
        case_id = case["id"]
        observed = case.get("observed")
        expected = EXPECTED[case_id]
        if observed != expected:
            fail(f"{case_id}: observed behavior differs from frozen oracle")

    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    canonical_digest = hashlib.sha256(canonical + b"\n").hexdigest()
    print("PASS: AGDWS v1 sanitized behavior packet matches independent public oracle")
    print(f"cases={len(cases)}")
    print(f"canonical_evidence_sha256={canonical_digest}")
    print(f"work_selection_blob={bindings['work_selection_git_blob_sha1']}")
    print(f"test_blob={bindings['test_work_selection_git_blob_sha1']}")


if __name__ == "__main__":
    main()
