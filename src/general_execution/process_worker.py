from __future__ import annotations

import argparse
import dataclasses
import json
import os
import uuid

from .canonical import canonical_json, sha256_digest
from .cold_rehearsal import prepare_reference_cold_restart, resume_reference_cold_restart

WORKER_PROTOCOL = "ge.process-recovery-worker.v1"


def _emit(phase: str, payload: dict) -> None:
    body = {
        "schema_version": WORKER_PROTOCOL,
        "phase": phase,
        "process_token": uuid.uuid4().hex,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "payload": payload,
        "payload_digest": sha256_digest(payload),
    }
    print(canonical_json(body), flush=True)


def _prepare(args: argparse.Namespace) -> None:
    receipt = prepare_reference_cold_restart(
        args.capacity,
        args.context,
        args.provider,
        suffix=args.suffix,
    )
    payload = dataclasses.asdict(receipt)
    payload["receipt_digest"] = receipt.digest
    _emit("prepare", payload)


def _resume(args: argparse.Namespace) -> None:
    rehearsal = resume_reference_cold_restart(
        args.capacity,
        args.context,
        args.provider,
        terminal_kind=args.terminal_kind,
    )
    payload = {
        "report": dataclasses.asdict(rehearsal.report),
        "report_digest": rehearsal.report.digest,
        "rehearsal_digest": rehearsal.digest,
        "reconstructed_session_id": rehearsal.reconstructed_session.session_id,
        "reconstructed_session_state": rehearsal.reconstructed_session.state,
        "context_id": rehearsal.context.context_id,
        "context_digest": rehearsal.context.digest,
        "outcome_digest": rehearsal.outcome.digest,
        "result_digest": rehearsal.result.digest if rehearsal.result is not None else None,
        "reconciliation_receipt_digest": rehearsal.reconciliation_receipt.digest,
    }
    _emit("resume", payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="general-execution-process-worker")
    sub = parser.add_subparsers(dest="phase", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--capacity", required=True)
    prepare.add_argument("--context", required=True)
    prepare.add_argument("--provider", required=True)
    prepare.add_argument("--suffix", default="1")

    resume = sub.add_parser("resume")
    resume.add_argument("--capacity", required=True)
    resume.add_argument("--context", required=True)
    resume.add_argument("--provider", required=True)
    resume.add_argument("--terminal-kind", choices=("timed_out", "completed"), default="timed_out")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.phase == "prepare":
        _prepare(args)
    else:
        _resume(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
