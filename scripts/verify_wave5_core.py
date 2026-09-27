#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import os
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from general_execution import (
    CoreVerificationManifest,
    VercelSandboxConformanceSpec,
    admit_vercel_core_verification,
    canonical_json,
    run_vercel_sandbox_conformance,
)

# The original 8f6494e target failed full regression; see the repair evidence.
WAVE5_REVISION = "04a47cd7031b608368de15ec2c99ccc715eb6cbf"
WAVE5_SUITE_REF = "tests://durable-execution/wave5-asp/full-repository"
WAVE5_FOCUSED_TEST_PATH = "tests/test_asp_transition.py"
WAVE5_FOCUSED_TEST_COUNT = 18


def execute_verification() -> tuple[int, dict]:
    manifest = CoreVerificationManifest(
        target_revision=WAVE5_REVISION,
        suite_ref=WAVE5_SUITE_REF,
        focused_test_path=WAVE5_FOCUSED_TEST_PATH,
        focused_test_count=WAVE5_FOCUSED_TEST_COUNT,
    )
    spec = VercelSandboxConformanceSpec(WAVE5_REVISION)

    payload = {
        "schema_version": "ge.wave5-core-verification-output.v2",
        "manifest": json.loads(canonical_json(manifest)),
        "manifest_digest": manifest.digest,
        "spec": json.loads(canonical_json(spec)),
        "spec_digest": spec.digest,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "status": "ERROR",
        "run": None,
        "run_digest": None,
        "receipt": None,
        "receipt_digest": None,
    }
    try:
        run = run_vercel_sandbox_conformance(
            spec,
            team_id=os.environ.get("VERCEL_TEAM_ID"),
            project_id=os.environ.get("VERCEL_PROJECT_ID"),
            token=os.environ.get("VERCEL_TOKEN"),
        )
    except Exception as exc:
        # Preserve the failure without serializing provider exception text,
        # chained tracebacks, credentials, or a fabricated receipt.
        payload["error_type"] = type(exc).__name__
        return 2, payload
    payload.update(
        status="FAIL",
        run=json.loads(canonical_json(run)),
        run_digest=run.digest,
    )
    try:
        receipt = admit_vercel_core_verification(
            manifest, spec, run, executed_at=payload["executed_at"],
        )
    except Exception as exc:
        payload["error_type"] = type(exc).__name__
        return 1, payload
    payload.update(
        status="PASS",
        receipt=json.loads(canonical_json(receipt)),
        receipt_digest=receipt.digest,
    )
    return 0, payload


def preflight() -> tuple[int, dict]:
    """Check local SDK compatibility without creating or invoking a Sandbox."""
    payload = {
        "schema_version": "ge.wave5-preflight.v1",
        "target_revision": WAVE5_REVISION,
        "provider_invoked": False,
        "receipt": None,
    }
    try:
        from vercel.sandbox import Sandbox

        compatible = (
            version("vercel") == "0.5.9"
            and callable(getattr(Sandbox, "create", None))
            and not inspect.iscoroutinefunction(Sandbox.create)
            and callable(getattr(Sandbox, "run_command", None))
            and "blocking" in inspect.signature(Sandbox.stop).parameters
        )
        payload.update(sdk_version=version("vercel"), sdk_compatible=compatible)
    except (ImportError, AttributeError, ValueError) as exc:
        payload.update(sdk_compatible=False, error_type=type(exc).__name__)
        compatible = False
    payload["authentication_configured"] = bool(
        os.environ.get("VERCEL_OIDC_TOKEN")
        or (
            os.environ.get("VERCEL_TOKEN")
            and os.environ.get("VERCEL_TEAM_ID")
            and os.environ.get("VERCEL_PROJECT_ID")
        )
    )
    return (0 if compatible and payload["authentication_configured"] else 2), payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    # Reserve an exclusive artifact before a paid/external operation; an
    # existing receipt can never be overwritten by a failed rerun.
    output = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output = args.output.open("x", encoding="utf-8")
    try:
        code, payload = preflight() if args.preflight else execute_verification()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if output:
            output.write(encoded + "\n")
            output.flush()
            os.fsync(output.fileno())
        print(encoded)
        return code
    finally:
        if output:
            output.close()


if __name__ == "__main__":
    raise SystemExit(main())
