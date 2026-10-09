from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from tests.test_persistent_runtime import bootstrap_event, portfolio


ROOT = Path(__file__).resolve().parents[1]


def sh(*args, cwd=None):
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def empty_state_remote(tmp_path):
    seed = tmp_path / "seed"
    remote = tmp_path / "remote.git"
    seed.mkdir()
    sh("git", "init", "-q", cwd=seed)
    sh("git", "config", "user.name", "fixture", cwd=seed)
    sh("git", "config", "user.email", "fixture@example.invalid", cwd=seed)
    target = seed / "opaque" / "state"
    target.mkdir(parents=True)
    (target / "state.sqlite.b64").write_text("\n")
    sh("git", "add", ".", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    sh("git", "branch", "-M", "state", cwd=seed)
    sh("git", "init", "--bare", "-q", str(remote))
    sh("git", "remote", "add", "origin", str(remote), cwd=seed)
    sh("git", "push", "-q", "origin", "state", cwd=seed)
    return remote


def test_external_state_entrypoint_bootstraps_and_recovers(tmp_path):
    remote = empty_state_remote(tmp_path)
    event = tmp_path / "event.json"
    report = tmp_path / "report.json"
    event.write_text(json.dumps(bootstrap_event(), sort_keys=True))

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_persistent_runtime_external_state.py"),
            "--event",
            str(event),
            "--remote",
            str(remote),
            "--branch",
            "state",
            "--root",
            "opaque",
            "--state-ref",
            "s_1234567890abcdef",
            "--runtime-source-revision",
            "a" * 40,
            "--trigger-commit",
            "b" * 40,
            "--report",
            str(report),
            "--persist-private-ledger",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    envelope = json.loads(report.read_text())
    assert envelope["authority_created"] is False
    assert envelope["event_report"]["status"] == "bootstrapped"
    assert envelope["state_plane_host_report"]["state_ref"] == "s_1234567890abcdef"

    checkout = tmp_path / "checkout"
    sh("git", "clone", "-q", str(remote), str(checkout))
    sh("git", "checkout", "-q", "state", cwd=checkout)
    root = checkout / "opaque"

    payload = base64.b64decode(
        (root / "state" / "state.sqlite.b64").read_text().strip(),
        validate=True,
    )
    db = tmp_path / "recovered.db"
    db.write_bytes(payload)
    state, checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db),
        portfolio().portfolio_id,
    )
    assert state == portfolio()
    assert checkpoint is None
    assert (root / "ledger" / "reports" / "bootstrap-001.json").is_file()
    assert (root / "ledger" / "processed" / "bootstrap-001.json").is_file()
    assert (root / "state" / "manifest.json").is_file()
