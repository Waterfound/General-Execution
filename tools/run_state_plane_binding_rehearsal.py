#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from general_execution.git_state_plane_transport import GitStatePlaneTransport
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import PortfolioEntry, PortfolioState, portfolio_state_to_dict
from general_execution.state_plane_host import execute_event_over_state_plane


def _run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git operation failed with rc={result.returncode}")
    return result.stdout.strip()


def _portfolio(rehearsal_id: str) -> PortfolioState:
    return PortfolioState(
        portfolio_id=f"binding-{rehearsal_id}",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="state-plane binding rehearsal",
            active_gate="REHEARSAL",
            next_action_ref="action://none",
            source_revision="binding-rehearsal",
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="remain ready",
            active_gate="SECONDARY",
            next_action_ref="action://none",
            source_revision="binding-rehearsal",
        ),
        passive=(),
    )


def _seed_shadow(
    *,
    remote: str,
    branch: str,
    root: str,
    rehearsal_id: str,
    workdir: Path,
) -> tuple[str, str]:
    checkout = workdir / "seed"
    _run("git", "clone", "--quiet", "--no-checkout", remote, str(checkout))
    _run("git", "fetch", "--quiet", "origin", branch, cwd=checkout)
    _run("git", "checkout", "--quiet", "-B", "state-plane", f"origin/{branch}", cwd=checkout)
    pre_head = _run("git", "rev-parse", "HEAD", cwd=checkout)

    source_root = checkout / root
    source_state = source_root / "state" / "state.sqlite.b64"
    if not source_state.is_file():
        raise RuntimeError("source private state blob is missing")

    shadow_root = source_root / "rehearsal" / rehearsal_id
    if shadow_root.exists():
        raise RuntimeError("shadow rehearsal root already exists")
    (shadow_root / "state").mkdir(parents=True)
    shutil.copy2(source_state, shadow_root / "state" / "state.sqlite.b64")

    _run("git", "config", "user.name", "durable-state-runtime", cwd=checkout)
    _run(
        "git",
        "config",
        "user.email",
        "durable-state-runtime@users.noreply.github.com",
        cwd=checkout,
    )
    _run("git", "add", "--", str(Path(root) / "rehearsal" / rehearsal_id), cwd=checkout)
    _run("git", "commit", "--quiet", "-m", "state: seed opaque binding rehearsal", cwd=checkout)

    result = subprocess.run(
        [
            "git",
            "push",
            "--quiet",
            "origin",
            f"HEAD:refs/heads/{branch}",
            f"--force-with-lease=refs/heads/{branch}:{pre_head}",
        ],
        cwd=str(checkout),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("shadow seed compare-and-swap failed")
    post_head = _run("git", "rev-parse", "HEAD", cwd=checkout)
    return pre_head, post_head


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--state-ref", required=True)
    parser.add_argument("--rehearsal-id", required=True)
    parser.add_argument("--runtime-source-revision", required=True)
    parser.add_argument("--trigger-commit", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    if "/" in args.rehearsal_id or ".." in args.rehearsal_id:
        raise SystemExit("unsafe rehearsal id")

    portfolio = _portfolio(args.rehearsal_id)
    event = {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": f"bootstrap-{args.rehearsal_id}",
        "operation": "bootstrap",
        "body": {"portfolio": portfolio_state_to_dict(portfolio)},
    }

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        seed_pre, seed_post = _seed_shadow(
            remote=args.remote,
            branch=args.branch,
            root=args.root,
            rehearsal_id=args.rehearsal_id,
            workdir=td_path,
        )
        shadow_root = f"{args.root}/rehearsal/{args.rehearsal_id}"
        transport = GitStatePlaneTransport(
            remote=args.remote,
            branch=args.branch,
            root=shadow_root,
            state_ref=args.state_ref,
            workdir=td_path / "runtime",
        )
        execution, host = execute_event_over_state_plane(
            transport,
            event,
            persist_private_ledger=True,
            runtime_source_revision=args.runtime_source_revision,
            trigger_commit=args.trigger_commit,
        )

        verify_transport = GitStatePlaneTransport(
            remote=args.remote,
            branch=args.branch,
            root=shadow_root,
            state_ref=args.state_ref,
            workdir=td_path / "verify",
        )
        receipt, payload = verify_transport.load()
        db = td_path / "recovered.sqlite"
        db.write_bytes(payload)
        state, checkpoint, recovery = recover_portfolio_after_restart(
            SqlitePortfolioHeadStore(db),
            portfolio.portfolio_id,
        )
        if state != portfolio or checkpoint is not None:
            raise RuntimeError("shadow recovery mismatch")

    output = {
        "schema_version": "ge.state-plane-binding-rehearsal.v1",
        "rehearsal_id": args.rehearsal_id,
        "state_ref": args.state_ref,
        "seed_cas": {
            "predecessor_present": bool(seed_pre),
            "successor_present": bool(seed_post),
            "pass": True,
        },
        "event_status": execution.status,
        "event_report_digest": execution.digest,
        "state_plane_host_report_digest": host.digest,
        "post_blob_digest": receipt.blob_digest,
        "recovery_report_digest": recovery.digest,
        "recovered_generation": state.generation,
        "private_ledger_persisted": True,
        "authority_created": False,
        "live_cutover": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n")
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
