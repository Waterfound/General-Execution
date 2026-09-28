#!/usr/bin/env python3
"""Consume one explicit Waterfound reject/supersede decision at a durable human gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from general_execution.canonical import canonical_json, sha256_digest
from general_execution.execution_checkpoint import CheckpointEvidence
from general_execution.human_gate_decision import (
    HumanGateDecision,
    consume_human_gate_decision,
)
from general_execution.portfolio_persistence import SqlitePortfolioHeadStore
from run_persistent_runtime_event import load_gate

EVENT_SCHEMA = "ge.human-gate-decision-event.v1"
EXECUTION_SCHEMA = "ge.human-gate-decision-execution.v1"


def exact(data, expected, label):
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise ValueError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


def encode(value):
    return json.loads(canonical_json(value))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--provider-actor", required=True)
    parser.add_argument("--decision-ref", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(args.decision.read_text(encoding="utf-8"))
    obj = exact(
        payload,
        {
            "schema_version",
            "event_id",
            "portfolio_id",
            "expected_generation",
            "expected_state_digest",
            "pending_action_ref",
            "decision",
            "reason",
            "target_state",
            "next_action_ref",
            "observed_at",
            "evidence",
            "canonical_refs",
        },
        "human gate decision event",
    )
    if obj["schema_version"] != EVENT_SCHEMA:
        raise ValueError("unsupported human gate decision event schema")
    evidence = obj["evidence"]
    refs = obj["canonical_refs"]
    if not isinstance(evidence, list) or not isinstance(refs, list):
        raise ValueError("evidence and canonical_refs must be lists")

    decision = HumanGateDecision(
        event_id=obj["event_id"],
        portfolio_id=obj["portfolio_id"],
        expected_generation=obj["expected_generation"],
        expected_state_digest=obj["expected_state_digest"],
        pending_action_ref=obj["pending_action_ref"],
        decision=obj["decision"],
        reason=obj["reason"],
        target_state=obj["target_state"],
        next_action_ref=obj["next_action_ref"],
        observed_at=obj["observed_at"],
        evidence=tuple(CheckpointEvidence(**item) for item in evidence),
        canonical_refs=tuple(refs),
    )

    _, _, core_report = load_gate()
    if not core_report.all_passed:
        raise ValueError("CORE-1 gate is not PASS")

    store = SqlitePortfolioHeadStore(args.database)
    result = consume_human_gate_decision(
        store,
        decision,
        provider_actor=args.provider_actor,
        decision_ref=args.decision_ref,
    )
    material = {
        "schema_version": EXECUTION_SCHEMA,
        "event_id": decision.event_id,
        "provider_actor": args.provider_actor,
        "decision_ref": args.decision_ref,
        "decision_digest": decision.digest,
        "receipt": encode(result.receipt),
        "receipt_digest": result.receipt.digest,
        "state": encode(result.state),
        "state_digest": result.state.digest,
        "checkpoint": encode(result.checkpoint),
        "checkpoint_digest": result.checkpoint.digest,
        "recovery_digest": result.recovery_digest,
        "database_sha256": sha256_file(args.database),
        "authority_grant_created": False,
    }
    envelope = {**material, "execution_report_digest": sha256_digest(material)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(envelope, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(envelope, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
