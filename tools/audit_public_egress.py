#!/usr/bin/env python3
"""Git candidate diff egress audit; prints categories/counts only."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from general_execution.publication_boundary import classify_public


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def audit(base, head):
    changed = git("diff", "--name-only", "--diff-filter=AM", "--no-renames", base, head)
    paths = changed.decode("utf-8").splitlines()
    categories = {}
    for path in paths:
        data = git("show", f"{head}:{path}")
        for category in classify_public(path, data):
            categories[category] = categories.get(category, 0) + 1
    return {
        "schema_version": "ge.public-egress-candidate-audit.v1",
        "verdict": "FAIL_CLOSED" if categories else "PASS",
        "changed_files_checked": len(paths),
        "findings_by_category": categories,
        "payload_data_emitted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        report = audit(args.base, args.head)
    except (ValueError, OSError, subprocess.CalledProcessError, UnicodeError):
        report = {"verdict": "FAIL_CLOSED", "error": "AUDIT_UNAVAILABLE"}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
