#!/usr/bin/env python3
"""Read-only cold-open check of a Git-serialized SQLite source snapshot.

Accepts only local files already available to the runner. Does not emit private
table names, row contents, raw event payloads, metadata or database bytes.
This is SOURCE recovery assurance, not private-host migration or activation.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def verify_snapshot(encoded: bytes, manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("INVALID_MANIFEST")
    expected = manifest.get("database_sha256")
    if (not isinstance(expected, str) or len(expected) != 71
            or not expected.startswith("sha256:")
            or any(c not in "0123456789abcdef" for c in expected[7:])):
        raise ValueError("INVALID_MANIFEST_DIGEST")
    if manifest.get("authority_created") is not False:
        raise ValueError("UNAUTHORIZED_SNAPSHOT")
    try:
        raw = base64.b64decode(b"".join(encoded.split()), validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("INVALID_ENCODING") from None
    if not raw.startswith(b"SQLite format 3\x00"):
        raise ValueError("INVALID_SQLITE_HEADER")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise ValueError("SOURCE_DIGEST_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="state-readonly-rehearsal-") as d:
        db = Path(d) / "source.sqlite"
        db.write_bytes(raw)
        for check in ("quick_check", "integrity_check"):
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                try:
                    outcome = con.execute(f"PRAGMA {check}").fetchone()
                except sqlite3.DatabaseError:
                    raise ValueError("SQLITE_CHECK_FAILED") from None
            finally:
                con.close()
            if outcome != ("ok",):
                raise ValueError("SQLITE_" + check.upper() + "_FAILED")
        # New interpreter => independent SQLite opening; no operational transition.
        inspect = ("import sqlite3,sys; "
                   "c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); "
                   "assert c.execute('PRAGMA quick_check').fetchone()==('ok',);"
                   "c.close()")
        p = subprocess.run([sys.executable, "-c", inspect, str(db)],
                           capture_output=True, timeout=15, check=False)
        if p.returncode:
            raise ValueError("COLD_OPEN_FAILED")
    return {
        "schema_version": "ge.source-restore-rehearsal.v1",
        "exact_source_digest_match": True,
        "sqlite_quick_check": "PASS",
        "sqlite_integrity_check": "PASS",
        "independent_process_cold_open": "PASS",
        "private_host_restoration_proven": False,
        "runtime_activation_performed": False,
        "authority_created": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_snapshot(
            args.snapshot.read_bytes(),
            json.loads(args.manifest.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        print(json.dumps({"verdict": "FAIL_CLOSED", "sensitive_values_reported": False}))
        return 1
    print(json.dumps({"verdict": "PASS_SOURCE_REHEARSAL_ONLY", **result},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
