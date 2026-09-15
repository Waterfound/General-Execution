from __future__ import annotations

import argparse
import os
import uuid

from .canonical import canonical_json, sha256_digest
from .canonical_cold import _preparation_candidate
from .cold_guard import bootstrap_cold_coordinator_strict
from .coordinator_context import SqliteCoordinatorContextStore
from .dispatch import SqliteDispatchIntentStore
from .durable import SqliteCapacityHeadStore

CRASH_EXIT_CODE = 91
CUT_POINTS = (
    "context_only",
    "prepared",
    "capacity_committed",
    "submission_unknown",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="general_execution.canonical_crash_worker")
    subparsers = parser.add_subparsers(dest="phase", required=True)

    cut = subparsers.add_parser("cut")
    cut.add_argument("--capacity", required=True)
    cut.add_argument("--context", required=True)
    cut.add_argument("--dispatch", required=True)
    cut.add_argument("--cut-point", choices=CUT_POINTS, required=True)
    cut.add_argument("--suffix", default="1")

    recover = subparsers.add_parser("recover")
    recover.add_argument("--capacity", required=True)
    recover.add_argument("--context", required=True)
    recover.add_argument("--dispatch", required=True)
    return parser


def _emit(phase: str, payload: dict) -> None:
    body = {
        "schema_version": "ge.canonical-crash-worker.v1",
        "phase": phase,
        "process_token": uuid.uuid4().hex,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "payload": payload,
        "payload_digest": sha256_digest(payload),
    }
    print(canonical_json(body), flush=True)


def _crash_after(cut_point: str, context, extra: dict | None = None) -> None:
    payload = {
        "cut_point": cut_point,
        "context_id": context.context_id,
        "invocation_id": context.authorization.request.invocation_id,
    }
    if extra:
        payload.update(extra)
    _emit("cut", payload)
    os._exit(CRASH_EXIT_CODE)


def _run_cut(args: argparse.Namespace) -> None:
    runner, genesis, reserved_state, context, _ = _preparation_candidate(args.suffix)
    capacity_store = SqliteCapacityHeadStore(args.capacity)
    context_store = SqliteCoordinatorContextStore(args.context)
    dispatch_store = SqliteDispatchIntentStore(args.dispatch)

    context_store.save(context)
    if args.cut_point == "context_only":
        _crash_after("context_only", context)

    prepared = dispatch_store.initialize(context.dispatch_intent)
    if args.cut_point == "prepared":
        _crash_after("prepared", context, {"dispatch_state_digest": prepared.digest})

    capacity_store.initialize(runner, genesis)
    head = capacity_store.commit(runner, genesis.digest, reserved_state)
    if args.cut_point == "capacity_committed":
        _crash_after(
            "capacity_committed",
            context,
            {
                "capacity_head_digest": head.digest,
                "dispatch_state_digest": prepared.digest,
            },
        )

    unknown, permit = dispatch_store.begin_submission(
        context.dispatch_intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    _crash_after(
        "submission_unknown",
        context,
        {
            "capacity_head_digest": head.digest,
            "dispatch_state_digest": unknown.digest,
            "dispatch_permit_digest": permit.digest,
        },
    )


def _run_recover(args: argparse.Namespace) -> int:
    bindings = bootstrap_cold_coordinator_strict(
        SqliteCoordinatorContextStore(args.context),
        SqliteCapacityHeadStore(args.capacity),
        SqliteDispatchIntentStore(args.dispatch),
    )
    if not bindings:
        payload = {
            "disposition": "inert_orphan",
            "active_binding_count": 0,
            "recovery_action": None,
            "context_id": None,
            "invocation_id": None,
        }
    elif len(bindings) == 1:
        binding = bindings[0]
        payload = {
            "disposition": binding.recovery_action,
            "active_binding_count": 1,
            "recovery_action": binding.recovery_action,
            "context_id": binding.context.context_id,
            "invocation_id": binding.context.authorization.request.invocation_id,
            "capacity_state_digest": binding.capacity_state.digest,
            "dispatch_state_digest": binding.dispatch_state.digest,
        }
    else:
        raise RuntimeError("crash-cut recovery expected at most one active binding")
    _emit("recover", payload)
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.phase == "cut":
        _run_cut(args)
        raise AssertionError("cut worker must terminate via os._exit")
    return _run_recover(args)


if __name__ == "__main__":
    raise SystemExit(main())
