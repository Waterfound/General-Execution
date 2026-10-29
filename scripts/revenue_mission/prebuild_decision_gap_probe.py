#!/usr/bin/env python3
"""Deterministic read-only probe for cross-artifact pre-build gaps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    rules = {
        (item["subject"], item["predicate"]): item
        for item in payload.get("business_rules", [])
    }
    for claim in payload.get("design_claims", []):
        rule = rules.get((claim["subject"], claim["predicate"]))
        if rule and rule["object"] != claim["object"]:
            findings.append(
                {
                    "id": f"CONTRADICTION:{claim['id']}:{rule['id']}",
                    "severity": "BLOCKER",
                    "kind": "cross_artifact_contradiction",
                    "evidence": [claim["id"], rule["id"]],
                    "message": (
                        f"{claim['subject']} {claim['predicate']} is "
                        f"{claim['object']!r} in design but {rule['object']!r} "
                        "in the business rule."
                    ),
                }
            )

    permissions = {
        role: set(actions)
        for role, actions in payload.get("permissions", {}).items()
    }
    for workflow in payload.get("workflows", []):
        for step in workflow.get("steps", []):
            role, action = step["role"], step["action"]
            if action not in permissions.get(role, set()):
                findings.append(
                    {
                        "id": f"PERMISSION_GAP:{workflow['id']}:{step['id']}",
                        "severity": "BLOCKER",
                        "kind": "workflow_permission_gap",
                        "evidence": [workflow["id"], step["id"], f"permissions:{role}"],
                        "message": f"Workflow requires {role!r} to {action!r}, but RBAC does not grant it.",
                    }
                )

    decisions = payload.get("decisions", {})
    for required in payload.get("required_decisions", []):
        if required["id"] not in decisions or decisions[required["id"]] in (None, "", "TBD"):
            findings.append(
                {
                    "id": f"DECISION_REQUIRED:{required['id']}",
                    "severity": required.get("severity", "HIGH"),
                    "kind": "product_decision_required",
                    "evidence": required.get("evidence", []),
                    "message": required["question"],
                }
            )

    order = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda item: (order.get(item["severity"], 9), item["id"]))
    counts = {level: 0 for level in order}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1

    return {
        "schema": "waterfound.prebuild-decision-gap-proof.v1",
        "fixture_id": payload.get("fixture_id"),
        "read_only": True,
        "finding_count": len(findings),
        "severity_counts": counts,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze(json.loads(args.fixture.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
