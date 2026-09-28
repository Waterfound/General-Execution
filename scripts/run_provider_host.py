#!/usr/bin/env python3
"""Build one deterministic Durable Execution event from a bounded provider input.

This script does not execute provider APIs, mutate durable state, grant authority,
or run arbitrary commands. It binds an already-authenticated provider observation
to a repository-frozen ProviderWatchContract and the exact current portfolio head.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution import canonical_json
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.provider_host import (
    ProviderHostError,
    build_provider_runtime_event,
    provider_input_from_dict,
    provider_watch_contract_from_dict,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--event-out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    provider_input = provider_input_from_dict(load_json(args.input))
    contract = provider_watch_contract_from_dict(load_json(args.contract))

    store = SqlitePortfolioHeadStore(args.database)
    state, checkpoint, recovery = recover_portfolio_after_restart(
        store, contract.portfolio_id
    )

    event, result = build_provider_runtime_event(state, contract, provider_input)
    report = {
        "schema_version": "ge.provider-host-execution.v1",
        "result": json.loads(canonical_json(result)),
        "portfolio_checkpoint_digest": checkpoint.digest if checkpoint else None,
        "recovery_report_digest": recovery.digest,
        "provider_input_path": str(args.input),
        "contract_path": str(args.contract),
        "event_path": str(args.event_out) if event is not None else None,
        "authority_created": False,
        "provider_command_executed": False,
    }

    if event is None:
        if args.event_out.exists():
            raise ProviderHostError("refusing stale event-out file for unsatisfied input")
    else:
        if args.event_out.exists():
            raise ProviderHostError("refusing to overwrite existing provider event")
        write_json(args.event_out, event)

    write_json(args.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
