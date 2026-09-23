#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from general_execution import (
    CoreVerificationManifest,
    VercelSandboxConformanceSpec,
    admit_vercel_core_verification,
    canonical_json,
    run_vercel_sandbox_conformance,
)

WAVE5_REVISION = "8f6494eca2c730de49b2e6ebfeb085cad1f33744"
WAVE5_SUITE_REF = "tests://durable-execution/wave5-asp/full-repository"
WAVE5_FOCUSED_TEST_PATH = "tests/test_asp_transition.py"
WAVE5_FOCUSED_TEST_COUNT = 18


def main() -> int:
    manifest = CoreVerificationManifest(
        target_revision=WAVE5_REVISION,
        suite_ref=WAVE5_SUITE_REF,
        focused_test_path=WAVE5_FOCUSED_TEST_PATH,
        focused_test_count=WAVE5_FOCUSED_TEST_COUNT,
    )
    spec = VercelSandboxConformanceSpec(WAVE5_REVISION)

    run = run_vercel_sandbox_conformance(
        spec,
        team_id=os.environ.get("VERCEL_TEAM_ID"),
        project_id=os.environ.get("VERCEL_PROJECT_ID"),
        token=os.environ.get("VERCEL_TOKEN"),
    )
    receipt = admit_vercel_core_verification(
        manifest,
        spec,
        run,
        executed_at=datetime.now(timezone.utc).isoformat(),
    )

    payload = {
        "schema_version": "ge.wave5-core-verification-output.v1",
        "manifest": json.loads(canonical_json(manifest)),
        "manifest_digest": manifest.digest,
        "spec": json.loads(canonical_json(spec)),
        "spec_digest": spec.digest,
        "run": json.loads(canonical_json(run)),
        "run_digest": run.digest,
        "receipt": json.loads(canonical_json(receipt)),
        "receipt_digest": receipt.digest,
    }
    print(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
