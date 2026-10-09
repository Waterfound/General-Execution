#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from general_execution.canonical import sha256_digest
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-b64", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    encoded = Path(args.state_b64).read_text().strip()
    binary = base64.b64decode(encoded, validate=True)
    database_sha256 = "sha256:" + hashlib.sha256(binary).hexdigest()
    manifest = json.loads(Path(args.manifest).read_text())
    if database_sha256 != manifest["database_sha256"]:
        raise SystemExit("database digest does not match manifest")

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "state.sqlite"
        db.write_bytes(binary)

        with sqlite3.connect(db) as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT portfolio_id FROM portfolio_heads ORDER BY portfolio_id"
                ).fetchall()
            ]

        store = SqlitePortfolioHeadStore(db)
        reports = []
        for portfolio_id in ids:
            state, checkpoint, report = recover_portfolio_after_restart(
                store, portfolio_id
            )
            reports.append(
                {
                    "generation": state.generation,
                    "state_digest": state.digest,
                    "checkpoint_present": checkpoint is not None,
                    "recovery_report_digest": report.digest,
                }
            )

    result = {
        "schema_version": "ge.durable-snapshot-verification.v1",
        "database_sha256": database_sha256,
        "portfolio_count": len(reports),
        "recovery_set_digest": sha256_digest(reports),
        "all_recovered": True,
        "authority_created": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
