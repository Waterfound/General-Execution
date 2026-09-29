#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.provider_host import provider_watch_contract_from_dict
from general_execution.workstream_result_handoff import (
    ObservedWorkstreamResult,
    handoff_to_dict,
    reconcile_workstream_result,
    select_result_outcome,
    workstream_result_watch_from_dict,
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
    p = argparse.ArgumentParser()
    p.add_argument("--watch", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--observed-at", required=True)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--event-out", type=Path, required=True)
    p.add_argument("--provider-input-out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args(argv)

    watch = workstream_result_watch_from_dict(load_json(args.watch))
    raw = args.result.read_bytes()
    payload = json.loads(raw)
    outcome = select_result_outcome(watch, payload)
    contract = provider_watch_contract_from_dict(
        load_json(Path(outcome.provider_contract_path))
    )

    state, checkpoint, recovery = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(args.database), contract.portfolio_id
    )
    observed = ObservedWorkstreamResult(
        source_commit=args.source_commit,
        observed_at=args.observed_at,
        content_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        payload=payload,
    )
    handoff = reconcile_workstream_result(state, watch, contract, observed)
    payload = handoff_to_dict(handoff)
    report = {
        "schema_version": "ge.workstream-result-handoff-execution.v1",
        "handoff": payload,
        "pre_generation": state.generation,
        "pre_state_digest": state.digest,
        "checkpoint_digest": checkpoint.digest if checkpoint else None,
        "recovery_report_digest": recovery.digest,
        "watch_path": str(args.watch),
        "result_path": str(args.result),
        "provider_contract_path": outcome.provider_contract_path,
        "authority_created": False,
        "workload_executed": False,
    }
    write_json(args.event_out, handoff.runtime_event)
    write_json(args.provider_input_out, payload["provider_input"])
    write_json(args.report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
