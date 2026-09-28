#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.continuity_adapters import (
    build_colony_from_mapping,
    candidate_from_mapping,
    conversation_from_mapping,
    durable_from_mapping,
    gates_from_mappings,
    provider_from_mapping,
    repository_from_mapping,
)
from general_execution.continuity_check import ContinuitySnapshot, inspect_continuity, render_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Continuity Check V1")
    parser.add_argument("--input", required=True, help="Normalized evidence JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    snapshot = ContinuitySnapshot(
        checked_at=str(data["checked_at"]),
        query=str(data["query"]),
        candidates=tuple(candidate_from_mapping(item) for item in data.get("candidates", [])),
        conversation=conversation_from_mapping(data.get("conversation")),
        repository=repository_from_mapping(data.get("repository")),
        durable=durable_from_mapping(data.get("durable")),
        build_colony=build_colony_from_mapping(data.get("build_colony")),
        provider=provider_from_mapping(data.get("provider")),
        gates=gates_from_mappings(data.get("gates")),
        canonical_integration_required=bool(data.get("canonical_integration_required", True)),
    )
    report = inspect_continuity(snapshot)
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
