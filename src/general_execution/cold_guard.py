from __future__ import annotations

import sqlite3

from .coordinator_context import (
    ColdCoordinatorBinding,
    CoordinatorContextIntegrityError,
    SqliteCoordinatorContextStore,
    verify_coordinator_context,
)
from .dispatch import DispatchIntentError, SqliteDispatchIntentStore
from .durable import DurableCapacityError, SqliteCapacityHeadStore


def _capacity_head_exists(store: SqliteCapacityHeadStore, runner_id: str) -> bool:
    """Distinguish a truly absent head from a corrupt head without parsing errors."""
    try:
        with sqlite3.connect(str(store.path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM capacity_heads WHERE runner_id = ?",
                (runner_id,),
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise CoordinatorContextIntegrityError(
            "durable capacity store is unreadable during cold bootstrap"
        ) from exc
    return row is not None


def bootstrap_cold_coordinator_strict(
    context_store: SqliteCoordinatorContextStore,
    capacity_store: SqliteCapacityHeadStore,
    dispatch_store: SqliteDispatchIntentStore,
) -> tuple[ColdCoordinatorBinding, ...]:
    """Fail-closed cold bootstrap over canonical capacity + dispatch stores.

    Only a truly absent capacity-head row is treated as a harmless pre-commit
    orphan. Corrupt metadata, capability drift, malformed snapshots, or any
    other durable capacity error are integrity failures rather than absence.
    """
    bindings: list[ColdCoordinatorBinding] = []
    for context in context_store.candidates():
        matches = [runner for runner in context.registry.runners if runner.runner_id == context.runner_id]
        if len(matches) != 1:
            raise CoordinatorContextIntegrityError(
                "cold context must contain exactly one selected runner"
            )
        runner = matches[0]
        head_exists = _capacity_head_exists(capacity_store, runner.runner_id)
        try:
            current_state, head = capacity_store.load(runner)
        except DurableCapacityError as exc:
            if not head_exists:
                continue
            raise CoordinatorContextIntegrityError(
                "durable capacity head failed integrity verification during cold bootstrap"
            ) from exc

        active = [
            lease
            for lease in current_state.active_leases
            if lease.lease_id == context.lease_id and lease.digest == context.lease_digest
        ]
        if not active:
            # Either reservation never committed or it was later released.
            continue
        if not verify_coordinator_context(current_state, context):
            raise CoordinatorContextIntegrityError(
                "active lease has invalid durable coordinator context"
            )
        try:
            dispatch_state = dispatch_store.load(context.dispatch_intent.intent_id)
        except DispatchIntentError as exc:
            raise CoordinatorContextIntegrityError(
                "active lease is missing its durable dispatch intent"
            ) from exc
        if dispatch_state.intent != context.dispatch_intent:
            raise CoordinatorContextIntegrityError(
                "durable dispatch state does not match coordinator context"
            )
        action = {
            "prepared": "begin_submission",
            "submission_unknown": "reconcile_provider",
            "observed": "none",
        }[dispatch_state.status]
        bindings.append(
            ColdCoordinatorBinding(
                context=context,
                runner=runner,
                capacity_state=current_state,
                capacity_head=head,
                dispatch_state=dispatch_state,
                recovery_action=action,
            )
        )
    return tuple(bindings)
