from __future__ import annotations

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
PACKET = ROOT / "evidence.json"

EXPECTED_CASES = [
    "routing_fit",
    "methodology_only_cannot_masquerade",
    "ready_without_executor_is_honest",
    "running_requires_executor_and_evidence",
    "bounded_running_with_evidence",
    "completed_requires_100_and_evidence",
    "background_states_rejected",
    "blocked_positive_progress_requires_evidence",
    "checkpoints_ordered_gap_free",
    "route_mismatch_fails_closed",
    "narrative_evidence_rejected",
]

EXPECTED_SEMANTICS = {
    "checkpoint_prefix": [
        "request_received",
        "route_decided",
        "executor_selected",
        "executor_attached",
        "evidence_emitted",
    ],
    "cross_system_handoff_route": "system_interoperability_envelope",
    "invalid_background_statuses": ["QUEUED", "WAITING", "CONTINUING"],
    "methodology_only_progress_percent": 0,
    "real_execution_positive_progress_requires_attached_executor": True,
    "real_execution_positive_progress_requires_external_evidence": True,
    "runtime_execution_route": "general_execution",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    raw = PACKET.read_bytes()
    packet = json.loads(raw)
    if packet.get("schema_version") != 1:
        fail("unexpected schema")
    if packet.get("privacy") != "sanitized_no_private_source_or_project_labels":
        fail("privacy boundary marker missing")
    if packet.get("verification_scope") != "cii_execution_binding_contract_v1":
        fail("unexpected scope")

    bindings = packet.get("origin_artifact_bindings")
    expected_binding_keys = {
        "execution_binding_source_git_blob_sha1",
        "execution_binding_test_git_blob_sha1",
        "origin_commit_sha1",
    }
    if not isinstance(bindings, dict) or set(bindings) != expected_binding_keys:
        fail("origin artifact bindings malformed")
    for key, value in bindings.items():
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
            fail(f"{key} is not a 40-hex Git identity")

    summary = packet.get("test_summary")
    if summary != {"tests": 11, "pass": 11, "fail": 0, "cancelled": 0, "skipped": 0}:
        fail("test summary is not 11/11 clean")

    cases = packet.get("cases")
    if not isinstance(cases, list) or [case.get("id") for case in cases] != EXPECTED_CASES:
        fail("case identities/order differ from frozen oracle")
    if any(case.get("outcome") != "PASS" for case in cases):
        fail("at least one frozen case is not PASS")

    if packet.get("frozen_semantics") != EXPECTED_SEMANTICS:
        fail("execution-binding semantics differ from frozen oracle")

    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    digest = hashlib.sha256(canonical).hexdigest()
    print("PASS: CII Execution Binding Contract v1 packet matches independent public oracle")
    print("cases=11")
    print(f"canonical_evidence_sha256={digest}")
    for key in sorted(bindings):
        print(f"{key}={bindings[key]}")


if __name__ == "__main__":
    main()
