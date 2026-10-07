#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.canonical_constitution import (
    admit_constitutionally_governed_launch,
    constitutional_admission_receipt_to_dict,
    constitutional_assessment_from_dict,
)
from general_execution.execution_launch_admission import (
    execution_launch_order_from_dict,
    execution_launch_receipt_from_dict,
    launch_receipt_to_dict,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Canonical-Constitution -> ELG-01 execution launch admission"
    )
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--constitutional-assessment", type=Path)
    parser.add_argument("--authenticated-actor")
    parser.add_argument("--authenticated-order-digest")
    parser.add_argument("--existing-launch-receipt", type=Path)
    parser.add_argument("--constitutional-receipt-out", type=Path)
    parser.add_argument("--launch-receipt-out", type=Path)
    parser.add_argument("--result-out", type=Path)
    parser.add_argument("--print-order-digest", action="store_true")
    args = parser.parse_args(argv)

    order = execution_launch_order_from_dict(load(args.order))
    if args.print_order_digest:
        print(order.digest)
        return 0

    required = {
        "--constitutional-assessment": args.constitutional_assessment,
        "--authenticated-actor": args.authenticated_actor,
        "--authenticated-order-digest": args.authenticated_order_digest,
        "--constitutional-receipt-out": args.constitutional_receipt_out,
        "--result-out": args.result_out,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error("required for governed admission: " + ", ".join(missing))

    assessment = constitutional_assessment_from_dict(
        load(args.constitutional_assessment)
    )
    existing = (
        execution_launch_receipt_from_dict(load(args.existing_launch_receipt))
        if args.existing_launch_receipt
        else None
    )

    governed = admit_constitutionally_governed_launch(
        order,
        assessment,
        authenticated_order_digest=args.authenticated_order_digest,
        authenticated_actor=args.authenticated_actor,
        existing_launch_receipt=existing,
    )

    constitutional_receipt = governed.constitutional_receipt
    write(
        args.constitutional_receipt_out,
        constitutional_admission_receipt_to_dict(constitutional_receipt),
    )

    launch_receipt = None
    launch_result = governed.launch_result
    if launch_result is not None:
        if args.launch_receipt_out is None:
            parser.error("--launch-receipt-out is required when constitutional gate admits")
        launch_receipt = launch_result.receipt
        write(args.launch_receipt_out, launch_receipt_to_dict(launch_receipt))
    elif args.existing_launch_receipt is not None:
        parser.error(
            "existing launch receipt cannot be supplied when constitutional gate blocks"
        )

    write(
        args.result_out,
        {
            "schema_version": "ge.constitutionally-governed-launch-result.v1",
            "workstream_id": order.workstream_id,
            "order_id": order.order_id,
            "order_digest": order.digest,
            "constitutional_assessment_digest": assessment.digest,
            "constitutional_receipt_id": constitutional_receipt.receipt_id,
            "constitutional_receipt_digest": constitutional_receipt.digest,
            "constitutional_disposition": constitutional_receipt.constitutional_disposition,
            "constitutional_admission_disposition": constitutional_receipt.admission_disposition,
            "constitutional_gate_passed": constitutional_receipt.constitutional_gate_passed,
            "launch_admission_materialized": launch_result is not None,
            "launch_replay_status": (
                launch_result.replay_status if launch_result is not None else None
            ),
            "launch_receipt_id": (
                launch_receipt.receipt_id if launch_receipt is not None else None
            ),
            "launch_receipt_digest": (
                launch_receipt.digest if launch_receipt is not None else None
            ),
            "launch_disposition": (
                launch_receipt.disposition if launch_receipt is not None else None
            ),
            "launch_id": (
                launch_receipt.launch_id if launch_receipt is not None else None
            ),
            "dispatch_identity": (
                launch_receipt.dispatch_identity
                if launch_receipt is not None
                else None
            ),
            "authority_created": False,
            "execution_triggered": False,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
