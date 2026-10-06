#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from general_execution.work_sparse_unattended import (
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    WorkSparseError,
    decision_to_dict,
    decide_work_sparse_route,
)


def _load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise WorkSparseError(f"{path} must contain a JSON object")
    return value


def _tuple(value: Any, field: str) -> tuple[str,...]:
    if not isinstance(value,list):
        raise WorkSparseError(f"{field} must be a list")
    return tuple(value)


def _envelope(data: dict[str,Any]) -> UnattendedAuthorityEnvelope:
    return UnattendedAuthorityEnvelope(
        envelope_id=data["envelope_id"],
        authority_ref=data["authority_ref"],
        allowed_repositories=_tuple(data["allowed_repositories"],"allowed_repositories"),
        allowed_actions=_tuple(data["allowed_actions"],"allowed_actions"),
        forbidden_actions=_tuple(data.get("forbidden_actions",[]),"forbidden_actions"),
        max_work_invocations=data.get("max_work_invocations",0),
        max_paid_spend_cents=data.get("max_paid_spend_cents",0),
        authority_created=data.get("authority_created",False),
        schema_version=data.get("schema_version","ge.work-sparse-authority-envelope.v1"),
    )


def _work(data: dict[str,Any]) -> UnattendedWorkItem:
    return UnattendedWorkItem(
        work_id=data["work_id"],
        objective=data["objective"],
        repository=data["repository"],
        source_revision=data["source_revision"],
        authority_ref=data["authority_ref"],
        required_capabilities=_tuple(data["required_capabilities"],"required_capabilities"),
        requested_actions=_tuple(data["requested_actions"],"requested_actions"),
        existing_execution_ref=data.get("existing_execution_ref"),
        schema_version=data.get("schema_version","ge.work-sparse-work-item.v1"),
    )


def _executors(data: dict[str,Any]) -> tuple[ExecutorCapability,...]:
    raw=data.get("executors")
    if not isinstance(raw,list):
        raise WorkSparseError("executors must be a list")
    return tuple(
        ExecutorCapability(
            executor_id=item["executor_id"],
            capabilities=_tuple(item["capabilities"],"capabilities"),
            cost_rank=item["cost_rank"],
            estimated_cost_cents=item.get("estimated_cost_cents",0),
            requires_work=item.get("requires_work",False),
            paid=item.get("paid",False),
            available=item.get("available",True),
            evidence_ref=item["evidence_ref"],
            authority_created=item.get("authority_created",False),
            schema_version=item.get("schema_version","ge.work-sparse-executor-capability.v1"),
        )
        for item in raw
    )


def _usage(data: dict[str,Any]) -> ControllerUsage:
    return ControllerUsage(
        work_invocations_used=data.get("work_invocations_used",0),
        paid_spend_cents=data.get("paid_spend_cents",0),
    )


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--envelope",type=Path,required=True)
    parser.add_argument("--work-item",type=Path,required=True)
    parser.add_argument("--executors",type=Path,required=True)
    parser.add_argument("--usage",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        envelope=_envelope(_load(args.envelope))
        work=_work(_load(args.work_item))
        executors=_executors(_load(args.executors))
        usage=_usage(_load(args.usage)) if args.usage else ControllerUsage()
        decision=decision_to_dict(
            decide_work_sparse_route(envelope,work,executors,usage)
        )
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(decision,sort_keys=True,indent=2)+"\n",
            encoding="utf-8",
        )
        print(json.dumps(decision,sort_keys=True))
        return 0
    except (KeyError, json.JSONDecodeError, OSError, WorkSparseError) as exc:
        print(json.dumps({"error":str(exc)},sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
