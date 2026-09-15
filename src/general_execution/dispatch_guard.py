from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_digest, stable_id
from .capacity import RunnerCapacityState, verify_capacity_state
from .dispatch import DispatchIntentError, DispatchIntentState, DispatchPermit, verify_dispatch_permit
from .models import RunnerCapabilities

LIVE_PERMIT_SCHEMA = "ge.live-dispatch-permit.v1"


@dataclass(frozen=True, slots=True)
class LiveDispatchPermit:
    intent_id: str
    intent_digest: str
    dispatch_state_digest: str
    dispatch_permit_digest: str
    runner_id: str
    runner_capability_digest: str
    capacity_state_digest: str
    capacity_generation: int
    lease_id: str
    lease_digest: str
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    schema_version: str = LIVE_PERMIT_SCHEMA

    def __post_init__(self) -> None:
        if self.capacity_generation < 1:
            raise ValueError("live dispatch requires a committed capacity generation")
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        for name in (
            "intent_id",
            "intent_digest",
            "dispatch_state_digest",
            "dispatch_permit_digest",
            "runner_id",
            "runner_capability_digest",
            "capacity_state_digest",
            "lease_id",
            "lease_digest",
            "authorization_id",
            "authorization_digest",
            "invocation_id",
            "request_digest",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")

    @property
    def permit_id(self) -> str:
        return stable_id("geldp", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _active_bound_lease(
    state: DispatchIntentState,
    permit: DispatchPermit,
    capacity_state: RunnerCapacityState,
    runner: RunnerCapabilities,
):
    if state.status != "submission_unknown":
        raise DispatchIntentError("live dispatch requires submission_unknown durable state")
    if not verify_dispatch_permit(state, permit):
        raise DispatchIntentError("durable dispatch permit does not reproduce")
    if not verify_capacity_state(capacity_state, runner):
        raise DispatchIntentError("capacity state does not replay for runner")

    intent = state.intent
    if intent.runner_id != runner.runner_id or intent.runner_capability_digest != runner.digest:
        raise DispatchIntentError("dispatch intent runner capabilities changed")

    matches = tuple(
        lease
        for lease in capacity_state.active_leases
        if lease.lease_id == intent.lease_id and lease.digest == intent.lease_digest
    )
    if len(matches) != 1:
        raise DispatchIntentError("dispatch lease is no longer active")
    lease = matches[0]
    if (
        lease.runner_id != intent.runner_id
        or lease.runner_capability_digest != intent.runner_capability_digest
        or lease.authorization_id != intent.authorization_id
        or lease.authorization_digest != intent.authorization_digest
        or lease.invocation_id != intent.invocation_id
        or lease.physical_attempt != intent.physical_attempt
        or lease.session_id != intent.session_id
        or lease.logical_attempt != intent.logical_attempt
    ):
        raise DispatchIntentError("active capacity lease no longer reproduces dispatch intent")
    return lease


def authorize_live_dispatch(
    state: DispatchIntentState,
    permit: DispatchPermit,
    capacity_state: RunnerCapacityState,
    runner: RunnerCapabilities,
) -> LiveDispatchPermit:
    lease = _active_bound_lease(state, permit, capacity_state, runner)
    intent = state.intent
    return LiveDispatchPermit(
        intent_id=intent.intent_id,
        intent_digest=intent.digest,
        dispatch_state_digest=state.digest,
        dispatch_permit_digest=permit.digest,
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        capacity_state_digest=capacity_state.digest,
        capacity_generation=capacity_state.generation,
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        authorization_id=intent.authorization_id,
        authorization_digest=intent.authorization_digest,
        invocation_id=intent.invocation_id,
        request_digest=intent.request_digest,
        physical_attempt=intent.physical_attempt,
    )


def verify_live_dispatch_permit(
    state: DispatchIntentState,
    permit: DispatchPermit,
    live_permit: LiveDispatchPermit,
    capacity_state: RunnerCapacityState,
    runner: RunnerCapabilities,
) -> bool:
    try:
        expected = authorize_live_dispatch(state, permit, capacity_state, runner)
    except (DispatchIntentError, ValueError):
        return False
    return live_permit == expected
