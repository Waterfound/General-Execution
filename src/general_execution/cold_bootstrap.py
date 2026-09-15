from __future__ import annotations

from dataclasses import dataclass

from .durable import DurableCapacitySnapshot, RecoveredInFlightLease, recover_after_restart
from .models import RunnerCapabilities
from .persistence import SQLiteDurableHeadStore
from .recovery_context import (
    DurableRecoveryContext,
    RecoveryContextIntegrityError,
    SQLiteRecoveryContextStore,
    verify_recovery_context,
)


@dataclass(frozen=True, slots=True)
class ColdRecoveryBinding:
    context: DurableRecoveryContext
    runner: RunnerCapabilities
    current_snapshot: DurableCapacitySnapshot
    recovered_lease: RecoveredInFlightLease
    schema_version: str = "ge.cold-recovery-binding.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.cold-recovery-binding.v1":
            raise ValueError("unsupported cold recovery binding schema")
        if not verify_recovery_context(self.current_snapshot, self.context):
            raise ValueError("cold recovery binding contains an invalid recovery context")
        if self.runner.runner_id != self.context.runner_id:
            raise ValueError("cold recovery binding runner does not match context")
        if (
            self.recovered_lease.lease_id != self.context.recovered_lease_id
            or self.recovered_lease.lease_digest != self.context.recovered_lease_digest
            or self.recovered_lease.authorization_id != self.context.authorization.authorization_id
        ):
            raise ValueError("cold recovery binding lease does not match context")


def bootstrap_active_recovery_contexts(
    context_store: SQLiteRecoveryContextStore,
    capacity_store: SQLiteDurableHeadStore,
) -> tuple[ColdRecoveryBinding, ...]:
    """Reconstruct active recovery bindings using only durable stores.

    Orphan contexts that never reached a capacity-head commit and contexts whose lease
    has already been canonically released are ignored. Any context that still points
    at an active lease must verify against the current capacity state.
    """
    bindings: list[ColdRecoveryBinding] = []
    for candidate, runner in context_store.bootstrap_candidates():
        current = capacity_store.load_current(runner)
        if current is None:
            continue
        _, report = recover_after_restart(current, runner)
        active = [
            lease
            for lease in report.active_leases
            if lease.authorization_id == candidate.authorization.authorization_id
        ]
        if not active:
            continue
        exact = [
            lease
            for lease in active
            if lease.lease_id == candidate.recovered_lease_id
            and lease.lease_digest == candidate.recovered_lease_digest
        ]
        if len(exact) != 1:
            raise RecoveryContextIntegrityError(
                "active authorization does not match its durable recovery context lease"
            )
        loaded, loaded_runner = context_store.load_for_recovered(current, exact[0])
        if loaded != candidate or loaded_runner != runner:
            raise RecoveryContextIntegrityError(
                "durable recovery context changed during cold bootstrap"
            )
        bindings.append(
            ColdRecoveryBinding(
                context=loaded,
                runner=runner,
                current_snapshot=current,
                recovered_lease=exact[0],
            )
        )
    return tuple(bindings)
