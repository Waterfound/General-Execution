#!/usr/bin/env python3
"""Verify a Git bundle by restoring it into a disposable mirror.

The source bundle is opened read-only. The only mutation is inside a temporary
directory which is deleted before the process exits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def run_git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_expected(values: list[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for value in values:
        ref, separator, commit = value.partition("=")
        if not separator or not ref.startswith("refs/") or not commit:
            raise ValueError(f"invalid expected ref: {value!r}; use refs/...=<object-id>")
        expected[ref] = commit.lower()
    return expected


def restored_refs(repository: Path) -> dict[str, str]:
    result = run_git("for-each-ref", "--format=%(refname) %(objectname)", cwd=repository)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git for-each-ref failed")
    return {
        ref: object_id.lower()
        for line in result.stdout.splitlines()
        for ref, object_id in [line.split(" ", 1)]
    }


def probe(bundle: Path, expected: dict[str, str]) -> tuple[dict[str, object], int]:
    started_at = datetime.now(UTC)
    monotonic_start = time.monotonic()
    checks: list[dict[str, object]] = []
    observed: dict[str, str] = {}

    verify = run_git("bundle", "verify", str(bundle))
    checks.append(
        {
            "name": "bundle_verify",
            "passed": verify.returncode == 0,
            "detail": (verify.stderr or verify.stdout).strip(),
        }
    )

    if verify.returncode == 0:
        with tempfile.TemporaryDirectory(prefix="wrm-restore-probe-") as directory:
            restored = Path(directory) / "restored.git"
            clone = run_git("clone", "--mirror", str(bundle), str(restored))
            checks.append(
                {
                    "name": "clean_room_restore",
                    "passed": clone.returncode == 0,
                    "detail": clone.stderr.strip(),
                }
            )
            if clone.returncode == 0:
                fsck = run_git("fsck", "--full", "--strict", cwd=restored)
                checks.append(
                    {
                        "name": "object_integrity",
                        "passed": fsck.returncode == 0,
                        "detail": (fsck.stderr or fsck.stdout).strip(),
                    }
                )
                observed = restored_refs(restored)

    missing = sorted(ref for ref in expected if ref not in observed)
    mismatched = {
        ref: {"expected": object_id, "observed": observed.get(ref)}
        for ref, object_id in expected.items()
        if ref in observed and observed[ref] != object_id
    }
    checks.append(
        {
            "name": "expected_refs",
            "passed": not missing and not mismatched,
            "missing": missing,
            "mismatched": mismatched,
        }
    )

    passed = all(bool(check["passed"]) for check in checks)
    finished_at = datetime.now(UTC)
    report: dict[str, object] = {
        "schema": "waterfound.repository-restore-readiness.v1",
        "result": "pass" if passed else "fail",
        "artifact": {
            "name": bundle.name,
            "bytes": bundle.stat().st_size,
            "sha256": sha256_file(bundle),
        },
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_ms": round((time.monotonic() - monotonic_start) * 1000),
        "checks": checks,
        "observed_refs": dict(sorted(observed.items())),
        "limitations": [
            "Git bundles do not contain GitHub/GitLab issues, pull requests, settings, packages, or Actions artifacts.",
            "LFS objects require a separate inventory and restore test.",
            "A passing result proves this artifact restored in this isolated run; it does not prove production recovery time.",
        ],
    }
    return report, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="path to the Git bundle to test")
    parser.add_argument(
        "--expect-ref",
        action="append",
        default=[],
        metavar="REF=OBJECT_ID",
        help="required restored ref and object ID; may be repeated",
    )
    parser.add_argument("--output", type=Path, help="write the JSON report to this path")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    if not bundle.is_file():
        parser.error(f"bundle is not a file: {bundle}")
    try:
        expected = parse_expected(args.expect_ref)
    except ValueError as error:
        parser.error(str(error))

    report, exit_code = probe(bundle, expected)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
