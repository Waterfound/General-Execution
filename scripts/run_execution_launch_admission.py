#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.execution_launch_admission import (
    admit_or_replay_execution_launch,
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
        description="Deterministic ELG-01 execution launch admission"
    )
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--authenticated-actor", required=True)
    parser.add_argument("--authenticated-order-digest")
    parser.add_argument("--existing-receipt", type=Path)
    parser.add_argument("--receipt-out", type=Path)
    parser.add_argument("--result-out", type=Path)
    parser.add_argument("--print-order-digest", action="store_true")
    args = parser.parse_args(argv)

    order = execution_launch_order_from_dict(load(args.order))
    if args.print_order_digest:
        print(order.digest)
        return 0

    if args.authenticated_order_digest is None:
        parser.error("--authenticated-order-digest is required for admission")
    if args.receipt_out is None or args.result_out is None:
        parser.error("--receipt-out and --result-out are required for admission")

    existing = (
        execution_launch_receipt_from_dict(load(args.existing_receipt))
        if args.existing_receipt
        else None
    )
    result = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=args.authenticated_order_digest,
        authenticated_actor=args.authenticated_actor,
        existing_receipt=existing,
    )
    receipt = launch_receipt_to_dict(result.receipt)
    write(args.receipt_out, receipt)
    write(
        args.result_out,
        {
            "schema_version": "ge.execution-launch-admission-result.v1",
            "replay_status": result.replay_status,
            "order_id": order.order_id,
            "order_digest": order.digest,
            "receipt_id": result.receipt.receipt_id,
            "receipt_digest": result.receipt.digest,
            "disposition": result.receipt.disposition,
            "launch_id": result.receipt.launch_id,
            "dispatch_identity": result.receipt.dispatch_identity,
            "authority_created": False,
            "execution_triggered": False,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
