#!/usr/bin/env python3
"""Execute one bounded immutable Autonomous Burst manifest against durable state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from general_execution.canonical import canonical_json
from general_execution.persistent_burst_host import (
    execute_persistent_burst,
    persistent_burst_manifest_from_dict,
)
from run_persistent_runtime_event import load_gate


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def safe_loader(root: Path):
    root = root.resolve()

    def load(path: str) -> bytes:
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("event path escaped events root") from exc
        return candidate.read_bytes()

    return load


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest = persistent_burst_manifest_from_dict(data)
    requirement, verification, core_report = load_gate()

    result = execute_persistent_burst(
        args.database,
        manifest,
        safe_loader(args.events_root),
        core_requirement=requirement,
        core_verification=verification,
        core_report=core_report,
    )
    material = {
        "schema_version": "ge.persistent-burst-host-envelope.v1",
        "burst_report": json.loads(canonical_json(result)),
        "burst_report_digest": result.digest,
        "database_sha256": sha256_file(args.database),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(material, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(material, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
