#!/usr/bin/env python3
"""Detect webhook paths that acknowledge success after zero entitlement updates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def analyze(payload: dict) -> dict:
    findings = []
    for path in payload.get("event_paths", []):
        if not path.get("affects_paid_access"):
            continue
        silent_drop = all(
            (
                path.get("zero_updates_possible") is True,
                path.get("zero_updates_is_error") is False,
                200 <= int(path.get("terminal_http_status", 0)) < 300,
                path.get("durable_retry_queue") is False,
            )
        )
        if silent_drop:
            findings.append(
                {
                    "id": f"silent-entitlement-drop:{path['event_type']}",
                    "severity": "BLOCKER",
                    "event_type": path["event_type"],
                    "predicate": "paid-access mutation can affect zero users and still be acknowledged",
                    "evidence": path["evidence"],
                    "bounded_consequence": "provider records successful delivery while application access can remain unchanged",
                }
            )

    findings.sort(key=lambda item: item["id"])
    return {
        "schema_version": 1,
        "fixture": payload["fixture"],
        "read_only": True,
        "finding_count": len(findings),
        "severity_counts": {"BLOCKER": len(findings)},
        "findings": findings,
        "claims_not_established": [
            "a real customer paid and lost access",
            "revenue leakage occurred",
            "operator time was saved",
            "willingness to try or pay",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(json.loads(args.fixture.read_text()))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
