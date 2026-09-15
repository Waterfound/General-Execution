from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict

from .canonical import canonical_json, sha256_digest
from .canonical_cold import prepare_canonical_cold_ambiguity, recover_canonical_cold_ambiguity


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="general_execution.canonical_process_worker")
    subparsers = parser.add_subparsers(dest="phase", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--capacity", required=True)
    prepare.add_argument("--context", required=True)
    prepare.add_argument("--dispatch", required=True)
    prepare.add_argument("--suffix", default="1")

    resume = subparsers.add_parser("resume")
    resume.add_argument("--capacity", required=True)
    resume.add_argument("--context", required=True)
    resume.add_argument("--dispatch", required=True)
    return parser


def _payload(args: argparse.Namespace) -> dict:
    if args.phase == "prepare":
        receipt = prepare_canonical_cold_ambiguity(
            args.capacity,
            args.context,
            args.dispatch,
            suffix=args.suffix,
        )
        return {
            "receipt": asdict(receipt),
            "receipt_digest": receipt.digest,
        }

    report = recover_canonical_cold_ambiguity(
        args.capacity,
        args.context,
        args.dispatch,
    )
    return {
        "report": asdict(report),
        "report_digest": report.digest,
    }


def main() -> int:
    args = _parser().parse_args()
    payload = _payload(args)
    body = {
        "schema_version": "ge.canonical-process-worker.v1",
        "phase": args.phase,
        "process_token": uuid.uuid4().hex,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "payload": payload,
        "payload_digest": sha256_digest(payload),
    }
    print(canonical_json(body), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
