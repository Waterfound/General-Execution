from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

from general_execution.git_state_plane_transport import GitStatePlaneTransport
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.state_plane_host import execute_event_over_state_plane
from tests.test_persistent_runtime import (
    bootstrap_event,
    gate,
    portfolio,
    transition_event,
)
from general_execution.persistent_runtime import process_persistent_runtime_event


def sh(*args, cwd=None):
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def seed_state_remote(tmp_path):
    db = tmp_path / "seed.db"
    process_persistent_runtime_event(db, bootstrap_event())

    seed = tmp_path / "seed"
    remote = tmp_path / "remote.git"
    seed.mkdir()
    sh("git", "init", "-q", cwd=seed)
    sh("git", "config", "user.name", "fixture", cwd=seed)
    sh("git", "config", "user.email", "fixture@example.invalid", cwd=seed)

    root = seed / "opaque"
    state_dir = root / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "state.sqlite.b64").write_text(
        base64.b64encode(db.read_bytes()).decode("ascii") + "\n"
    )

    sh("git", "add", ".", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    sh("git", "branch", "-M", "state", cwd=seed)
    sh("git", "init", "--bare", "-q", str(remote))
    sh("git", "remote", "add", "origin", str(remote), cwd=seed)
    sh("git", "push", "-q", "origin", "state", cwd=seed)
    return remote


def checkout_remote(remote, target):
    sh("git", "clone", "-q", str(remote), str(target))
    sh("git", "checkout", "-q", "state", cwd=target)


def test_current_single_event_host_runs_over_git_state_plane_and_recovers(tmp_path):
    remote = seed_state_remote(tmp_path)
    transport = GitStatePlaneTransport(
        remote=str(remote),
        branch="state",
        root="opaque",
        state_ref="s_1234567890abcdef",
        workdir=tmp_path / "runtime",
    )
    requirement, receipt, core_report = gate()

    execution, host = execute_event_over_state_plane(
        transport,
        transition_event(),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
        persist_private_ledger=True,
        runtime_source_revision="a" * 40,
        trigger_commit="b" * 40,
    )

    assert execution.status == "committed"
    assert execution.pre_generation == 0
    assert execution.post_generation == 1
    assert execution.human_required
    assert execution.requested_action_ref == "authority://persistent-runtime"
    assert host.pre_blob_digest != host.post_blob_digest
    assert host.execution_report_digest == execution.digest
    assert not host.authority_created

    verify = tmp_path / "verify"
    checkout_remote(remote, verify)
    root = verify / "opaque"

    encoded = (root / "state" / "state.sqlite.b64").read_text().strip()
    recovered_db = tmp_path / "recovered.db"
    recovered_db.write_bytes(base64.b64decode(encoded, validate=True))

    state, checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(recovered_db),
        portfolio().portfolio_id,
    )
    assert state.generation == 1
    assert state.active.state == "human_gate"
    assert checkpoint is not None
    assert checkpoint.authority_stop

    report_path = root / "ledger" / "reports" / "transition-001.json"
    processed_path = root / "ledger" / "processed" / "transition-001.json"
    manifest_path = root / "state" / "manifest.json"
    assert report_path.is_file()
    assert processed_path.is_file()
    assert manifest_path.is_file()

    report = json.loads(report_path.read_text())
    processed = json.loads(processed_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    assert report["event_report_digest"] == execution.digest
    assert processed["event_report_digest"] == execution.digest
    assert processed["authority_created"] is False
    assert manifest["last_event_id"] == "transition-001"
    assert manifest["authority_created"] is False


def test_current_host_redelivery_remains_idempotent_over_external_state(tmp_path):
    remote = seed_state_remote(tmp_path)
    requirement, receipt, core_report = gate()

    first = GitStatePlaneTransport(
        remote=str(remote),
        branch="state",
        root="opaque",
        state_ref="s_1234567890abcdef",
        workdir=tmp_path / "first",
    )
    one, _ = execute_event_over_state_plane(
        first,
        transition_event(),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )
    assert one.status == "committed"

    second = GitStatePlaneTransport(
        remote=str(remote),
        branch="state",
        root="opaque",
        state_ref="s_1234567890abcdef",
        workdir=tmp_path / "second",
    )
    two, _ = execute_event_over_state_plane(
        second,
        transition_event(),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )
    assert two.status == "already_applied"
    assert two.pre_generation == two.post_generation == 1
