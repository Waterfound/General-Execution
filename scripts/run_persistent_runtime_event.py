#!/usr/bin/env python3
"""Short-lived entrypoint for the persistent Durable Execution runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from general_execution import canonical_json
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    CoreRehearsalReport,
)
from general_execution.persistent_runtime import (
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from run_core1_rehearsal import admit as admit_core_verification

ROOT = Path(__file__).resolve().parents[1]
WAVE5 = ROOT / "evidence/durable-execution/2026-09-27/wave5-verification.json"
CORE1 = ROOT / "evidence/durable-execution/2026-09-27/core1-run-002/core1-receipt.json"


def load_gate():
    requirement, receipt = admit_core_verification(WAVE5)
    data = json.loads(CORE1.read_text(encoding="utf-8"))
    data["assertions"] = tuple(
        CoreRehearsalAssertion(
            **dict(
                item,
                evidence_refs=tuple(item["evidence_refs"]),
                evidence_digests=tuple(item["evidence_digests"]),
            )
        )
        for item in data["assertions"]
    )
    report = CoreRehearsalReport(**data)
    if not report.all_passed:
        raise RuntimeError("CORE-1 gate is not PASS")
    if report.core_verification_receipt_digest != receipt.digest:
        raise RuntimeError("CORE-1 receipt binding mismatch")
    return requirement, receipt, report


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--authenticated-trigger-digest")
    parser.add_argument("--print-trigger-digest", action="store_true")
    args = parser.parse_args(argv)

    payload = json.loads(args.event.read_text(encoding="utf-8"))

    if args.print_trigger_digest:
        digest = trigger_digest_from_event(payload)
        print(digest or "NONE")
        return 0

    if args.database is None or args.report is None:
        parser.error("--database and --report are required for execution")

    operation = payload.get("operation")
    kwargs = {}
    if operation == "transition":
        requirement, receipt, core_report = load_gate()
        kwargs = {
            "authenticated_trigger_digest": args.authenticated_trigger_digest,
            "core_requirement": requirement,
            "core_verification": receipt,
            "core_report": core_report,
        }

    result = process_persistent_runtime_event(
        args.database,
        payload,
        **kwargs,
    )

    envelope = {
        "schema_version": "ge.persistent-runtime-execution.v1",
        "event_report": json.loads(canonical_json(result)),
        "event_report_digest": result.digest,
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
