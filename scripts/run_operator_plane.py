#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.operator_plane import build_operator_projection, render_operator_projection


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed Operator Plane V1 read-only projection")
    parser.add_argument("--input", required=True, help="Normalized operator-plane input JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    projection = build_operator_projection(data)
    if args.format == "json":
        print(json.dumps(projection, indent=2, sort_keys=True))
    else:
        print(render_operator_projection(projection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
