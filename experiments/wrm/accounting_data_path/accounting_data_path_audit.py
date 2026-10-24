#!/usr/bin/env python3
"""Read-only cross-system receipt comparator for a synthetic WRM proof."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def audit(receipts: dict, max_delay_minutes: int = 15) -> list[dict]:
    sources = {event["event_id"]: event for event in receipts["source_events"]}
    destinations = defaultdict(list)
    findings: list[dict] = []

    for event in receipts["destination_events"]:
        source_id = event.get("source_event_id")
        if not source_id or source_id not in sources:
            findings.append(
                {
                    "code": "UNCORRELATED_DESTINATION",
                    "record_key": event["record_key"],
                    "evidence": [event["event_id"]],
                }
            )
            continue
        destinations[source_id].append(event)

    approvals = {
        event["approval_id"]: event
        for event in receipts.get("approval_events", [])
        if event.get("status") == "approved"
    }

    for source_id, source in sources.items():
        linked = sorted(destinations[source_id], key=lambda item: _time(item["at"]))
        creates = [event for event in linked if event["action"] == "create"]

        if not linked:
            findings.append(
                {
                    "code": "MISSING_DESTINATION",
                    "record_key": source["record_key"],
                    "evidence": [source_id],
                }
            )
            continue

        if len(creates) > 1:
            findings.append(
                {
                    "code": "DUPLICATE_DESTINATION",
                    "record_key": source["record_key"],
                    "evidence": [source_id, *[event["event_id"] for event in creates]],
                }
            )

        first_create = creates[0] if creates else linked[0]
        delay = (_time(first_create["at"]) - _time(source["at"])).total_seconds() / 60
        if delay > max_delay_minutes:
            findings.append(
                {
                    "code": "DELAYED_SYNC",
                    "record_key": source["record_key"],
                    "delay_minutes": int(delay),
                    "evidence": [source_id, first_create["event_id"]],
                }
            )

        approval_id = source.get("required_approval_id")
        approval = approvals.get(approval_id) if approval_id else None
        if approval_id and (
            approval is None or _time(approval["at"]) > _time(first_create["at"])
        ):
            evidence = [source_id, first_create["event_id"]]
            if approval:
                evidence.append(approval["event_id"])
            findings.append(
                {
                    "code": "MISSING_APPROVAL_EVIDENCE",
                    "record_key": source["record_key"],
                    "evidence": evidence,
                }
            )

        manual_edits = [
            event
            for event in linked
            if event["action"] == "update"
            and event.get("actor_type") == "human"
            and _time(event["at"]) > _time(first_create["at"])
        ]
        for edit in manual_edits:
            findings.append(
                {
                    "code": "POST_SYNC_MANUAL_EDIT",
                    "record_key": source["record_key"],
                    "evidence": [source_id, first_create["event_id"], edit["event_id"]],
                }
            )

    return sorted(findings, key=lambda item: (item["record_key"], item["code"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--max-delay-minutes", type=int, default=15)
    args = parser.parse_args()
    receipts = json.loads(args.fixture.read_text())
    print(json.dumps(audit(receipts, args.max_delay_minutes), indent=2))


if __name__ == "__main__":
    main()
