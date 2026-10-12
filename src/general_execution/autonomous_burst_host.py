"""Native host adapter for Autonomous Burst over the existing atomic runtime boundary.

This module deliberately owns no scheduler, provider, credential, spend, or authority.
It composes:
  fresh evidence resolver -> Autonomous Burst -> exact one-transition executor
and requires every atomic receipt to be durably persisted before the next observation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .autonomous_burst import (
    AutonomousBurstObservation,
    AutonomousBurstPolicy,
    AutonomousBurstResult,
    AutonomousBurstTransitionReceipt,
    AutonomousBurstTrigger,
    run_autonomous_burst,
)

ObservationResolver = Callable[[], AutonomousBurstObservation]
AtomicExecutor = Callable[[AutonomousBurstObservation], AutonomousBurstTransitionReceipt]
ReceiptPersister = Callable[[AutonomousBurstTransitionReceipt], str]


class NativeBurstHostError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NativeBurstHostPolicy:
    """Host-level guardrails; cannot weaken the underlying burst policy."""

    max_transitions: int = 8
    max_wall_seconds: int = 900

    def __post_init__(self) -> None:
        if type(self.max_transitions) is not int or not 1 <= self.max_transitions <= 8:
            raise NativeBurstHostError("native host max_transitions must be in [1, 8]")
        if type(self.max_wall_seconds) is not int or not 1 <= self.max_wall_seconds <= 900:
            raise NativeBurstHostError("native host max_wall_seconds must be in [1, 900]")


def run_native_autonomous_burst_host(
    *,
    trigger: AutonomousBurstTrigger,
    observe_fresh: ObservationResolver,
    execute_atomic: AtomicExecutor,
    persist_receipt: ReceiptPersister,
    host_policy: NativeBurstHostPolicy = NativeBurstHostPolicy(),
    heartbeat_fallback_seconds: int = 900,
) -> AutonomousBurstResult:
    """Run a bounded burst without changing the existing atomic execution contract.

    The wrapped executor persists each independently validated receipt before
    run_autonomous_burst is allowed to request the next fresh observation.
    Persistence returns a digest/ref only; the host cannot manufacture authority.
    """

    policy = AutonomousBurstPolicy(
        max_transitions=host_policy.max_transitions,
        max_wall_seconds=host_policy.max_wall_seconds,
        heartbeat_fallback_seconds=heartbeat_fallback_seconds,
    )

    def execute_and_persist(
        observation: AutonomousBurstObservation,
    ) -> AutonomousBurstTransitionReceipt:
        receipt = execute_atomic(observation)
        persisted = persist_receipt(receipt)
        if not isinstance(persisted, str) or not persisted.strip():
            raise NativeBurstHostError(
                "atomic transition receipt must be durably persisted before continuation"
            )
        return receipt

    return run_autonomous_burst(
        trigger,
        policy,
        observe_fresh,
        execute_and_persist,
    )
