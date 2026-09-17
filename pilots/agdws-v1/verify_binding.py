from __future__ import annotations

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
EVIDENCE = ROOT / "binding-evidence.json"

EXPECTED_CASES = {
    "eligible_only_issue": {
        "issued": ["lane-a", "lane-b"],
        "left_ready": ["lane-c", "lane-d"],
        "event_count": 2,
        "all_events_bind_contract_digest": True,
        "all_events_bind_decision_digest": True,
        "all_events_bind_active_gate": True,
    },
    "missing_binding_fail_closed": {
        "outcome": "ERROR",
        "caller_input_event_count_after": 0,
    },
    "unclassified_gate_no_issue": {
        "issued": [],
        "di_advisory": True,
        "reason": "active_gate_unclassified",
    },
}

EXPECTED_BOUNDARY = {
    "selection_precedes_issue": True,
    "issue_uses_existing_ledger_append_primitive": True,
    "existing_dispatch_planner_modified": False,
    "existing_engine_modified": False,
    "runner_assignment_authority_added": False,
    "verification_authority_added": False,
    "integration_authority_added": False,
}

EXPECTED_BINDING_KEYS = {
    "binding_source_git_blob_sha1",
    "binding_test_git_blob_sha1",
    "selection_source_git_blob_sha1",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    raw = EVIDENCE.read_bytes()
    packet = json.loads(raw)
    if packet.get("schema_version") != 1:
        fail("unexpected schema")
    if packet.get("privacy") != "sanitized_no_private_source_or_project_labels":
        fail("privacy boundary marker missing")
    if packet.get("verification_scope") != "pre_dispatch_issue_binding":
        fail("unexpected verification scope")

    bindings = packet.get("origin_artifact_bindings")
    if not isinstance(bindings, dict) or set(bindings) != EXPECTED_BINDING_KEYS:
        fail("origin bindings malformed")
    for key, value in bindings.items():
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
            fail(f"{key} is not a Git blob id")

    cases = packet.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        fail("unexpected case count")
    case_map = {case.get("id"): case.get("observed") for case in cases}
    if len(case_map) != len(cases) or set(case_map) != set(EXPECTED_CASES):
        fail("case identities differ from frozen oracle")
    for case_id, expected in EXPECTED_CASES.items():
        if case_map[case_id] != expected:
            fail(f"{case_id}: binding behavior differs from frozen oracle")

    if packet.get("static_boundary_review") != EXPECTED_BOUNDARY:
        fail("authority/preservation boundary differs from frozen oracle")

    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    digest = hashlib.sha256(canonical).hexdigest()
    print("PASS: AGDWS v1 pre-ISSUE binding packet matches independent public oracle")
    print(f"cases={len(cases)}")
    print(f"canonical_binding_evidence_sha256={digest}")
    for key in sorted(bindings):
        print(f"{key}={bindings[key]}")


if __name__ == "__main__":
    main()
