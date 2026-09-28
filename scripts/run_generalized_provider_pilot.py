#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from general_execution import (
    PortfolioEntry,
    PortfolioState,
    SqlitePortfolioHeadStore,
    canonical_json,
    recover_portfolio_after_restart,
)
from general_execution.provider_host import (
    build_provider_runtime_event,
    load_provider_snapshot,
    load_provider_watch,
)

ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def bootstrap(database: Path) -> None:
    state = PortfolioState(
        portfolio_id="durable-generalized-provider-pilot",
        generation=0,
        active=PortfolioEntry(
            work_id="GENERALIZED-PROVIDER-PILOT",
            role="active",
            state="running",
            objective="Prove a non-FAE provider can wake Durable Execution without chat control.",
            active_gate="GENERALIZED-PROVIDER-PILOT",
            next_action_ref="action://observe-github-provider",
            source_revision="generalized-provider-pilot",
            evidence_required=("github_provider_observed",),
        ),
        secondary=PortfolioEntry(
            work_id="GENERALIZED-PROVIDER-PILOT-SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain inert during provider wake proof.",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="generalized-provider-pilot",
        ),
    )
    SqlitePortfolioHeadStore(database).initialize(state)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--watch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.output.exists():
        raise AssertionError("Refusing to overwrite generalized provider pilot evidence")
    args.output.mkdir(parents=True)

    database = args.output / "pilot.db"
    bootstrap(database)

    watch = load_provider_watch(args.watch)
    snapshot = load_provider_snapshot(args.snapshot)
    host = build_provider_runtime_event(database, watch, snapshot)
    assert host.matched and host.event is not None
    event_path = args.output / "provider-event.json"
    write(event_path, host.event)
    write(args.output / "provider-host-result.json", json.loads(canonical_json(host)))

    digest = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "scripts/run_persistent_runtime_event.py"),
            "--event",
            str(event_path),
            "--print-trigger-digest",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    assert digest.startswith("sha256:")

    runtime_report = args.output / "runtime-report.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_persistent_runtime_event.py"),
            "--event",
            str(event_path),
            "--database",
            str(database),
            "--report",
            str(runtime_report),
            "--authenticated-trigger-digest",
            digest,
        ],
        cwd=ROOT,
        check=True,
    )

    state, checkpoint, recovery = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(database),
        "durable-generalized-provider-pilot",
    )
    assert state.generation == 1
    assert state.active.state == "human_gate"
    assert checkpoint is not None and checkpoint.authority_stop

    report = {
        "schema_version": "ge.generalized-provider-pilot.v1",
        "status": "PASS",
        "provider": snapshot.provider,
        "provider_event_id": snapshot.provider_event_id,
        "snapshot_digest": snapshot.digest,
        "watch_digest": watch.digest,
        "host_result_digest": host.digest,
        "event_id": host.event_id,
        "event_digest": host.event_digest,
        "final_generation": state.generation,
        "final_state": state.active.state,
        "human_required": True,
        "chat_context_required": False,
        "provider_host_used": True,
        "persistent_runtime_used": True,
        "authority_created": False,
        "checkpoint_digest": checkpoint.digest,
        "recovery_report_digest": recovery.digest,
    }
    write(args.output / "pilot-report.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
