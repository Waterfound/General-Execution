#!/usr/bin/env python3
"""Consume one host-authenticated human authorization at a durable human gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from general_execution.canonical import canonical_json
from general_execution.human_authority import consume_human_authority
from general_execution.persistent_runtime import _observation
from general_execution.portfolio_persistence import SqlitePortfolioHeadStore
from general_execution.transition_policy import transition_policy_from_dict
from run_persistent_runtime_event import load_gate

EVENT_SCHEMA = "ge.human-authority-event.v1"
EXECUTION_SCHEMA = "ge.human-authority-execution.v1"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def encode(value):
    return json.loads(canonical_json(value))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--provider-actor", required=True)
    parser.add_argument("--authority-ref", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    obj = exact(
        payload,
        {
            "schema_version",
            "event_id",
            "approved_action_ref",
            "approved_at",
            "policy",
            "observation",
        },
        "human authority event",
    )
    if obj["schema_version"] != EVENT_SCHEMA:
        raise ValueError("unsupported human authority event schema")
    if not isinstance(obj["event_id"], str) or not obj["event_id"].strip():
        raise ValueError("event_id must be non-empty")

    policy = transition_policy_from_dict(obj["policy"])
    observation = _observation(obj["observation"])
    if observation.authority_grant is not None:
        raise ValueError("human authority event cannot self-carry a grant")

    requirement, verification, core_report = load_gate()
    if not core_report.all_passed:
        raise ValueError("CORE-1 gate is not PASS")

    store = SqlitePortfolioHeadStore(args.database)
    receipt, bound, result = consume_human_authority(
        store,
        policy,
        observation,
        event_id=obj["event_id"],
        approved_action_ref=obj["approved_action_ref"],
        approved_at=obj["approved_at"],
        provider_actor=args.provider_actor,
        authority_ref=args.authority_ref,
        core_requirement=requirement,
        core_verification=verification,
    )
    if result.disposition != "committed":
        raise ValueError(f"human authority transition did not commit: {result.disposition}")

    envelope = {
        "schema_version": EXECUTION_SCHEMA,
        "event_id": obj["event_id"],
        "provider_actor": args.provider_actor,
        "authority_ref": args.authority_ref,
        "authority_receipt": encode(receipt),
        "authority_receipt_digest": receipt.digest,
        "authority_grant_digest": bound.authority_grant.digest,
        "observation_digest": bound.digest,
        "tick": encode(result),
        "database_sha256": sha256_file(args.database),
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
