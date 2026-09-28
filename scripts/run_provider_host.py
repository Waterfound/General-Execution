#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.canonical import canonical_json
from general_execution.provider_host import (
    build_provider_runtime_event,
    load_provider_snapshot,
    load_provider_watch,
)


def _write_exclusive(path: Path, payload: dict) -> None:
    if path.exists():
        raise AssertionError(f"refusing to overwrite existing output: {path}")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--watch", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    watch = load_provider_watch(args.watch)
    snapshot = load_provider_snapshot(args.snapshot)
    result = build_provider_runtime_event(args.database, watch, snapshot)

    report = json.loads(canonical_json(result))
    if args.report is not None:
        _write_exclusive(args.report, report)

    if result.matched:
        if args.output is None:
            raise AssertionError("--output is required when provider state matches")
        assert result.event is not None
        _write_exclusive(args.output, result.event)

    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
