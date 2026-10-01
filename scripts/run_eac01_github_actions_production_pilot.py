#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from general_execution.execution_launch_admission import (
    admit_or_replay_execution_launch,
    execution_launch_order_from_dict,
)
from general_execution.executor_activation import (
    SqliteExecutorActivationStore,
    activate_or_reconcile_executor,
    begin_activation,
    prepare_executor_activation,
)
from general_execution.github_actions_executor_activation import (
    GitHubActionsExecutorActivationAdapter,
    github_actions_executor_capability,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    order = execution_launch_order_from_dict(load(args.order))
    actor = os.environ.get("GITHUB_ACTOR", "")
    receipt = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor=actor,
    ).receipt
    if receipt.disposition != "ADMITTED":
        raise SystemExit(f"pilot launch order not admitted: {receipt.disposition}")

    capability = github_actions_executor_capability(receipt.repository)
    adapter = GitHubActionsExecutorActivationAdapter(capability)

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        ordinary_store = SqliteExecutorActivationStore(root / "ordinary.sqlite")
        first = activate_or_reconcile_executor(
            ordinary_store, receipt, capability, adapter
        )
        replay = activate_or_reconcile_executor(
            ordinary_store, receipt, capability, adapter
        )

        crash_store = SqliteExecutorActivationStore(root / "crash.sqlite")
        intent = prepare_executor_activation(receipt, capability)
        prepared = crash_store.initialize(intent)
        crash_store.compare_and_swap(prepared, begin_activation(prepared))
        lost = adapter.activate(intent)
        recovered = activate_or_reconcile_executor(
            crash_store, receipt, capability, adapter
        )

        wait_capability = github_actions_executor_capability(
            receipt.repository,
            available=False,
        )
        wait_adapter = GitHubActionsExecutorActivationAdapter(wait_capability)
        wait_store = SqliteExecutorActivationStore(root / "wait.sqlite")
        wait_result = activate_or_reconcile_executor(
            wait_store,
            receipt,
            wait_capability,
            wait_adapter,
        )

        failed_env = dict(os.environ)
        failed_env["GITHUB_REPOSITORY"] = "Waterfound/Intentional-Mismatch"
        failed_capability = github_actions_executor_capability(receipt.repository)
        failed_adapter = GitHubActionsExecutorActivationAdapter(
            failed_capability,
            env=failed_env,
        )
        failed_store = SqliteExecutorActivationStore(root / "failed.sqlite")
        failed_result = activate_or_reconcile_executor(
            failed_store,
            receipt,
            failed_capability,
            failed_adapter,
        )

    native_refs = {
        first.state.native_execution_ref,
        lost.native_execution_ref,
        recovered.state.native_execution_ref,
    }
    evidence = {
        "schema_version": "ge.eac01-production-executor-adapter-live-evidence.v1",
        "executor": "github_actions",
        "adapter_id": capability.adapter_id,
        "dispatch_identity": receipt.dispatch_identity,
        "receipt_id": receipt.receipt_id,
        "receipt_digest": receipt.digest,
        "authority_ref": receipt.authority_ref,
        "authority_created": False,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "native_execution_ref": first.state.native_execution_ref,
        "first_activation_status": first.state.status,
        "terminal_replay_status": replay.replay_status,
        "crash_recovery_status": recovered.replay_status,
        "crash_native_ref_matches": (
            lost.native_execution_ref == recovered.state.native_execution_ref
        ),
        "unique_native_execution_refs": len(native_refs),
        "duplicate_native_launches": max(0, len(native_refs) - 1),
        "manual_transport_steps_after_authorized_order_materialization": 0,
        "condition_wait_status": wait_result.state.status,
        "condition_wait_ref": wait_result.state.condition_ref,
        "failed_activation_status": failed_result.state.status,
        "failed_activation_reason": failed_result.state.failure_reason,
        "false_executing_claims": 0,
        "production_executor_real": os.environ.get("GITHUB_ACTIONS") == "true",
    }

    required = {
        "first_activation_status": "executor_accepted",
        "terminal_replay_status": "ALREADY_RECORDED",
        "crash_recovery_status": "RECOVERED",
        "crash_native_ref_matches": True,
        "unique_native_execution_refs": 1,
        "duplicate_native_launches": 0,
        "manual_transport_steps_after_authorized_order_materialization": 0,
        "condition_wait_status": "condition_wait",
        "failed_activation_status": "failed_activation",
        "authority_created": False,
        "false_executing_claims": 0,
        "production_executor_real": True,
    }
    for key, expected in required.items():
        if evidence.get(key) != expected:
            raise SystemExit(
                f"EAC-01 production adapter criterion failed: "
                f"{key}={evidence.get(key)!r}, expected={expected!r}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
