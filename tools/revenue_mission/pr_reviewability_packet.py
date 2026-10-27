#!/usr/bin/env python3
"""Generate an evidence-bound reviewability packet for an AI-authored PR.

The input is a deliberately small, provider-neutral JSON export.  The tool is
read-only: it neither calls a forge API nor changes pull-request state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RISK_PREFIXES = (
    ".github/workflows/",
    "migrations/",
    "infra/",
    "security/",
    "auth/",
)


def _check_index(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(check.get("name", "")): str(check.get("conclusion", "unknown"))
        for check in payload.get("checks", [])
    }


def build_packet(payload: dict[str, Any]) -> dict[str, Any]:
    checks = _check_index(payload)
    changed_files = [str(path) for path in payload.get("changed_files", [])]
    high_risk_files = [
        path for path in changed_files if path.startswith(RISK_PREFIXES)
    ]
    evidence: list[dict[str, Any]] = []
    unsupported_claims: list[dict[str, Any]] = []

    for claim in payload.get("claims", []):
        text = str(claim.get("text", ""))
        required = [str(name) for name in claim.get("requires_checks", [])]
        missing = [name for name in required if name not in checks]
        failing = [
            name
            for name in required
            if checks.get(name) not in {"success", "neutral", "skipped"}
        ]
        record = {
            "claim": text,
            "required_checks": required,
            "observed": {name: checks.get(name, "missing") for name in required},
        }
        if missing or failing:
            record["reason"] = {
                "missing_checks": missing,
                "non_passing_checks": failing,
            }
            unsupported_claims.append(record)
        else:
            evidence.append(record)

    unresolved_threads = [
        thread
        for thread in payload.get("review_threads", [])
        if not bool(thread.get("resolved", False))
    ]
    human_owner = payload.get("human_owner")
    ai_authored = bool(payload.get("ai_authored", False))
    targeted_validation = bool(payload.get("targeted_validation", False))
    review_decision = str(payload.get("review_decision", "")).lower()

    uncertainties: list[str] = [
        str(item) for item in payload.get("declared_uncertainties", [])
    ]
    if high_risk_files and not targeted_validation:
        uncertainties.append("high-risk paths changed without targeted validation")
    if ai_authored and not human_owner:
        uncertainties.append("AI-authored change has no identified human steward")
    if ai_authored and not payload.get("agent_session_links"):
        uncertainties.append("AI-authored change has no linked agent session")

    blockers: list[str] = []
    if unsupported_claims:
        blockers.append("one or more completion claims lack passing evidence")
    if unresolved_threads:
        blockers.append("review threads remain unresolved")
    if review_decision == "changes_requested":
        blockers.append("native review decision remains changes requested")
    if any(value in {"failure", "cancelled", "timed_out", "action_required"} for value in checks.values()):
        blockers.append("one or more checks are non-passing")

    if blockers:
        disposition = "BLOCK"
    elif uncertainties:
        disposition = "HUMAN_VERIFY"
    else:
        disposition = "REVIEWABLE"

    return {
        "schema_version": "wrm.reviewability-packet.v1",
        "pull_request": payload.get("pull_request", {}),
        "disposition": disposition,
        "verified_claims": evidence,
        "unsupported_claims": unsupported_claims,
        "unresolved_threads": unresolved_threads,
        "review_decision": review_decision or None,
        "high_risk_files": high_risk_files,
        "residual_uncertainties": uncertainties,
        "blockers": blockers,
        "human_owner": human_owner,
        "next_action": _next_action(blockers, uncertainties),
    }


def _next_action(blockers: list[str], uncertainties: list[str]) -> str:
    if blockers:
        return blockers[0]
    if uncertainties:
        return uncertainties[0]
    return "begin human code review"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    packet = build_packet(json.loads(args.input.read_text(encoding="utf-8")))
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
