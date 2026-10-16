#!/usr/bin/env python3
"""Create and compare read-only evidence manifests for a directory tree.

This is a deliberately small commercial-discovery probe.  It never edits source
files and does not claim forensic, legal, or production suitability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "wrm.construction-evidence-snapshot/v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path, *, observed_at: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        stat = path.stat()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema": SCHEMA,
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
        "root_label": root.name,
        "files": files,
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if before.get("schema") != SCHEMA or after.get("schema") != SCHEMA:
        raise ValueError("unsupported manifest schema")

    old = {item["path"]: item for item in before["files"]}
    new = {item["path"]: item for item in after["files"]}
    removed = set(old) - set(new)
    added = set(new) - set(old)

    # A one-to-one identical-content move is a rename. Ambiguous duplicate hashes
    # remain separate remove/add events rather than being guessed.
    old_by_hash: dict[str, list[str]] = {}
    new_by_hash: dict[str, list[str]] = {}
    for path in removed:
        old_by_hash.setdefault(old[path]["sha256"], []).append(path)
    for path in added:
        new_by_hash.setdefault(new[path]["sha256"], []).append(path)

    renamed: list[dict[str, str]] = []
    for digest in sorted(set(old_by_hash) & set(new_by_hash)):
        if len(old_by_hash[digest]) == len(new_by_hash[digest]) == 1:
            source = old_by_hash[digest][0]
            target = new_by_hash[digest][0]
            renamed.append({"from": source, "to": target, "sha256": digest})
            removed.remove(source)
            added.remove(target)

    changed: list[dict[str, Any]] = []
    metadata_only: list[dict[str, Any]] = []
    for path in sorted(set(old) & set(new)):
        a, b = old[path], new[path]
        if a["sha256"] != b["sha256"]:
            changed.append(
                {
                    "path": path,
                    "before_sha256": a["sha256"],
                    "after_sha256": b["sha256"],
                    "before_size": a["size"],
                    "after_size": b["size"],
                    "same_size": a["size"] == b["size"],
                }
            )
        elif a["mtime_ns"] != b["mtime_ns"]:
            metadata_only.append(
                {
                    "path": path,
                    "sha256": a["sha256"],
                    "before_mtime_ns": a["mtime_ns"],
                    "after_mtime_ns": b["mtime_ns"],
                }
            )

    return {
        "schema": SCHEMA,
        "before_observed_at": before["observed_at"],
        "after_observed_at": after["observed_at"],
        "added": [new[path] for path in sorted(added)],
        "removed": [old[path] for path in sorted(removed)],
        "renamed": renamed,
        "content_changed": changed,
        "metadata_only": metadata_only,
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("root", type=Path)
    compare = sub.add_parser("diff")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    args = parser.parse_args()
    result = snapshot(args.root) if args.command == "snapshot" else diff(_load(args.before), _load(args.after))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
