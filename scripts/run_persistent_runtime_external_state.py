#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from general_execution.canonical import canonical_json
from general_execution.git_state_plane_transport import GitStatePlaneTransport
from general_execution.state_plane_host import execute_event_over_state_plane
from run_persistent_runtime_event import load_gate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--remote", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--state-ref", required=True)
    parser.add_argument("--runtime-source-revision", required=True)
    parser.add_argument("--trigger-commit", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--persist-private-ledger", action="store_true")
    args = parser.parse_args(argv)

    payload = json.loads(args.event.read_text(encoding="utf-8"))
    kwargs = {}
    if payload.get("operation") == "transition":
        requirement, receipt, core_report = load_gate()
        kwargs = {
            "core_requirement": requirement,
            "core_verification": receipt,
            "core_report": core_report,
        }

    with tempfile.TemporaryDirectory() as td:
        transport = GitStatePlaneTransport(
            remote=args.remote,
            branch=args.branch,
            root=args.root,
            state_ref=args.state_ref,
            workdir=Path(td),
        )
        execution, host = execute_event_over_state_plane(
            transport,
            payload,
            persist_private_ledger=args.persist_private_ledger,
            runtime_source_revision=args.runtime_source_revision,
            trigger_commit=args.trigger_commit,
            **kwargs,
        )

    envelope = {
        "schema_version": "ge.external-state-runtime-execution.v1",
        "event_report": json.loads(canonical_json(execution)),
        "event_report_digest": execution.digest,
        "state_plane_host_report": json.loads(canonical_json(host)),
        "state_plane_host_report_digest": host.digest,
        "authority_created": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(envelope, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(envelope, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
