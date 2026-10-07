"""Bounded event-driven continuation above atomic Durable Execution ticks.

Autonomous Burst does not execute a batch transition. It repeatedly asks an
external evidence resolver for fresh state and consumes at most one exact
transition per loop iteration through an injected atomic executor.

The module is intentionally provider-neutral and authority-neutral:
- Continuity Check may inform an observation, but remains read-only.
- the injected executor must preserve the existing one-transition runtime gate;
- no authority, spend, provider resource, credential or scheduler is created;
- every successor is re-observed against fresh state before execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable, Literal

from .canonical import sha256_digest

BURST_TRIGGER_SCHEMA = "ge.autonomous-burst-trigger.v1"
BURST_POLICY_SCHEMA = "ge.autonomous-burst-policy.v1"
BURST_OBSERVATION_SCHEMA = "ge.autonomous-burst-observation.v1"
BURST_TRANSITION_RECEIPT_SCHEMA = "ge.autonomous-burst-transition-receipt.v1"
BURST_RESULT_SCHEMA = "ge.autonomous-burst-result.v1"
BURST_FOLLOWUP_SCHEMA = "ge.autonomous-burst-followup.v1"

TriggerKind = Literal["hourly_watchdog", "provider_event", "heartbeat", "manual"]
ObservationStatus = Literal[
    "admissible",
    "progressing",
    "human_gate",
    "external_evidence_gate",
    "condition_wait",
    "scheduled_wait",
    "done",
    "failed",
    "stalled",
    "insufficient_evidence",
]
BurstDisposition = Literal["stopped", "lease_exhausted", "transition_budget_exhausted"]
FollowupKind = Literal["provider_event", "heartbeat", "none"]

_CONTINUITY_TO_STATUS = {
    "CHECKPOINTED_RESUMABLE": "admissible",
    "DEVELOPMENT_PROGRESSING": "progressing",
    "CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED": "progressing",
    "HUMAN_GATE": "human_gate",
    "EXTERNAL_EVIDENCE_GATE": "external_evidence_gate",
    "CONDITION_WAIT": "condition_wait",
    "SCHEDULED_WAIT": "scheduled_wait",
    "DONE_TECHNICAL": "done",
    "DONE_CANONICAL": "done",
    "FAILED": "failed",
    "DEVELOPMENT_STALLED": "stalled",
    "INSUFFICIENT_EVIDENCE": "insufficient_evidence",
}

_STOP_REASON = {
    "progressing": "ACTIVE_EXECUTION_OBSERVED",
    "human_gate": "HUMAN_GATE",
    "external_evidence_gate": "EXTERNAL_EVIDENCE_GATE",
    "condition_wait": "CONDITION_WAIT",
    "scheduled_wait": "SCHEDULED_WAIT",
    "done": "CEILING_REACHED",
    "failed": "FAILED",
    "stalled": "DEVELOPMENT_STALLED",
    "insufficient_evidence": "INSUFFICIENT_EVIDENCE",
}


class AutonomousBurstError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AutonomousBurstError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise AutonomousBurstError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise AutonomousBurstError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class AutonomousBurstTrigger:
    kind: TriggerKind
    source_ref: str
    observed_at: str
    schema_version: str = BURST_TRIGGER_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_TRIGGER_SCHEMA:
            raise AutonomousBurstError("unsupported burst trigger schema")
        if self.kind not in {"hourly_watchdog", "provider_event", "heartbeat", "manual"}:
            raise AutonomousBurstError("unsupported burst trigger kind")
        _nonempty("source_ref", self.source_ref)
        _nonempty("observed_at", self.observed_at)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AutonomousBurstPolicy:
    max_transitions: int = 32
    max_wall_seconds: int = 900
    heartbeat_fallback_seconds: int = 900
    schema_version: str = BURST_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_POLICY_SCHEMA:
            raise AutonomousBurstError("unsupported burst policy schema")
        if type(self.max_transitions) is not int or self.max_transitions < 1:
            raise AutonomousBurstError("max_transitions must be a positive integer")
        if type(self.max_wall_seconds) is not int or self.max_wall_seconds < 1:
            raise AutonomousBurstError("max_wall_seconds must be a positive integer")
        if type(self.heartbeat_fallback_seconds) is not int or self.heartbeat_fallback_seconds < 900:
            raise AutonomousBurstError(
                "heartbeat_fallback_seconds must be >= 900 seconds; heartbeat is fallback, not primary cadence"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AutonomousBurstObservation:
    portfolio_id: str
    generation: int
    state_digest: str
    status: ObservationStatus
    next_action_ref: str | None
    evidence_digest: str
    observed_at: str
    continuity_verdict: str | None = None
    authority_satisfied: bool = True
    constitutional_gate_passed: bool = True
    paid_spend_required: bool = False
    credential_gate_satisfied: bool = True
    schema_version: str = BURST_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_OBSERVATION_SCHEMA:
            raise AutonomousBurstError("unsupported burst observation schema")
        _nonempty("portfolio_id", self.portfolio_id)
        if type(self.generation) is not int or self.generation < 0:
            raise AutonomousBurstError("generation must be a non-negative integer")
        _digest("state_digest", self.state_digest)
        _digest("evidence_digest", self.evidence_digest)
        _nonempty("observed_at", self.observed_at)
        if self.status not in {
            "admissible",
            "progressing",
            "human_gate",
            "external_evidence_gate",
            "condition_wait",
            "scheduled_wait",
            "done",
            "failed",
            "stalled",
            "insufficient_evidence",
        }:
            raise AutonomousBurstError("unsupported observation status")
        if self.status == "admissible":
            _nonempty("next_action_ref", self.next_action_ref)
        if self.continuity_verdict is not None:
            expected = _CONTINUITY_TO_STATUS.get(self.continuity_verdict)
            if expected is None:
                raise AutonomousBurstError("unsupported Continuity Check verdict")
            if expected != self.status:
                raise AutonomousBurstError(
                    "Continuity Check verdict disagrees with normalized burst status"
                )
        for name in (
            "authority_satisfied",
            "constitutional_gate_passed",
            "paid_spend_required",
            "credential_gate_satisfied",
        ):
            if not isinstance(getattr(self, name), bool):
                raise AutonomousBurstError(f"{name} must be boolean")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @classmethod
    def from_continuity(
        cls,
        *,
        portfolio_id: str,
        generation: int,
        state_digest: str,
        continuity_verdict: str,
        next_action_ref: str | None,
        evidence_digest: str,
        observed_at: str,
        authority_satisfied: bool = True,
        constitutional_gate_passed: bool = True,
        paid_spend_required: bool = False,
        credential_gate_satisfied: bool = True,
    ) -> "AutonomousBurstObservation":
        status = _CONTINUITY_TO_STATUS.get(continuity_verdict)
        if status is None:
            raise AutonomousBurstError("unsupported Continuity Check verdict")
        return cls(
            portfolio_id=portfolio_id,
            generation=generation,
            state_digest=state_digest,
            status=status,  # type: ignore[arg-type]
            next_action_ref=next_action_ref,
            evidence_digest=evidence_digest,
            observed_at=observed_at,
            continuity_verdict=continuity_verdict,
            authority_satisfied=authority_satisfied,
            constitutional_gate_passed=constitutional_gate_passed,
            paid_spend_required=paid_spend_required,
            credential_gate_satisfied=credential_gate_satisfied,
        )


@dataclass(frozen=True, slots=True)
class AutonomousBurstTransitionReceipt:
    portfolio_id: str
    action_ref: str
    pre_generation: int
    post_generation: int
    pre_state_digest: str
    post_state_digest: str
    transition_digest: str
    checkpoint_digest: str
    authority_created: bool = False
    paid_spend_created: bool = False
    schema_version: str = BURST_TRANSITION_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_TRANSITION_RECEIPT_SCHEMA:
            raise AutonomousBurstError("unsupported burst transition receipt schema")
        _nonempty("portfolio_id", self.portfolio_id)
        _nonempty("action_ref", self.action_ref)
        for name in (
            "pre_state_digest",
            "post_state_digest",
            "transition_digest",
            "checkpoint_digest",
        ):
            _digest(name, getattr(self, name))
        if type(self.pre_generation) is not int or type(self.post_generation) is not int:
            raise AutonomousBurstError("receipt generations must be integers")
        if self.post_generation != self.pre_generation + 1:
            raise AutonomousBurstError("atomic receipt must advance exactly one generation")
        if self.pre_state_digest == self.post_state_digest:
            raise AutonomousBurstError("atomic receipt must change state digest")
        if self.authority_created:
            raise AutonomousBurstError("Autonomous Burst cannot create authority")
        if self.paid_spend_created:
            raise AutonomousBurstError("Autonomous Burst cannot create paid spend")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AutonomousBurstFollowup:
    kind: FollowupKind
    delay_seconds: int | None
    reason: str
    authority_created: bool = False
    schema_version: str = BURST_FOLLOWUP_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_FOLLOWUP_SCHEMA:
            raise AutonomousBurstError("unsupported burst followup schema")
        if self.kind not in {"provider_event", "heartbeat", "none"}:
            raise AutonomousBurstError("unsupported followup kind")
        _nonempty("reason", self.reason)
        if self.kind == "heartbeat":
            if type(self.delay_seconds) is not int or self.delay_seconds < 900:
                raise AutonomousBurstError("heartbeat delay must be >= 900 seconds")
        elif self.delay_seconds is not None:
            raise AutonomousBurstError("only heartbeat may specify delay_seconds")
        if self.authority_created:
            raise AutonomousBurstError("followup planning cannot create authority")


@dataclass(frozen=True, slots=True)
class AutonomousBurstResult:
    trigger_digest: str
    policy_digest: str
    portfolio_id: str
    initial_generation: int
    final_generation: int
    initial_state_digest: str
    final_state_digest: str
    transition_receipts: tuple[AutonomousBurstTransitionReceipt, ...]
    disposition: BurstDisposition
    stop_reason: str
    authority_created: bool = False
    schema_version: str = BURST_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BURST_RESULT_SCHEMA:
            raise AutonomousBurstError("unsupported burst result schema")
        _digest("trigger_digest", self.trigger_digest)
        _digest("policy_digest", self.policy_digest)
        _nonempty("portfolio_id", self.portfolio_id)
        _digest("initial_state_digest", self.initial_state_digest)
        _digest("final_state_digest", self.final_state_digest)
        _nonempty("stop_reason", self.stop_reason)
        if self.disposition not in {
            "stopped",
            "lease_exhausted",
            "transition_budget_exhausted",
        }:
            raise AutonomousBurstError("unsupported burst disposition")
        if self.final_generation < self.initial_generation:
            raise AutonomousBurstError("burst cannot move generation backwards")
        if self.final_generation - self.initial_generation != len(self.transition_receipts):
            raise AutonomousBurstError(
                "burst generation delta must equal independently evidenced atomic transitions"
            )
        if self.authority_created:
            raise AutonomousBurstError("Autonomous Burst cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def plan_async_followup(
    observation: AutonomousBurstObservation,
    *,
    provider_completion_event_available: bool,
    expected_long_running: bool,
    policy: AutonomousBurstPolicy,
) -> AutonomousBurstFollowup:
    """Choose an observation mechanism without turning polling into the primary cadence."""
    if observation.status != "progressing":
        return AutonomousBurstFollowup(
            kind="none",
            delay_seconds=None,
            reason="work is not currently executing asynchronously",
        )
    if provider_completion_event_available:
        return AutonomousBurstFollowup(
            kind="provider_event",
            delay_seconds=None,
            reason="provider-native completion event is available and preferred",
        )
    if expected_long_running:
        return AutonomousBurstFollowup(
            kind="heartbeat",
            delay_seconds=policy.heartbeat_fallback_seconds,
            reason="no reliable completion event; bounded heartbeat is fallback",
        )
    return AutonomousBurstFollowup(
        kind="none",
        delay_seconds=None,
        reason="short-running work should be re-observed by its owning executor rather than polled",
    )


def _admissibility_stop(observation: AutonomousBurstObservation) -> str | None:
    if observation.status != "admissible":
        return _STOP_REASON[observation.status]
    if not observation.constitutional_gate_passed:
        return "CONSTITUTIONAL_GATE_CLOSED"
    if not observation.authority_satisfied:
        return "AUTHORITY_REQUIRED"
    if observation.paid_spend_required:
        return "PAID_SPEND_GATE"
    if not observation.credential_gate_satisfied:
        return "CREDENTIAL_GATE"
    return None


def run_autonomous_burst(
    trigger: AutonomousBurstTrigger,
    policy: AutonomousBurstPolicy,
    observe: Callable[[], AutonomousBurstObservation],
    execute_one: Callable[[AutonomousBurstObservation], AutonomousBurstTransitionReceipt],
    *,
    clock: Callable[[], float] = monotonic,
) -> AutonomousBurstResult:
    """Chain fresh atomic transitions until a real wait/gate/ceiling or bounded lease.

    execute_one is deliberately injected. In production it must be the existing
    authenticated one-transition runtime path; this function never dispatches a
    provider or creates authority itself.
    """
    started = clock()
    first = observe()
    portfolio_id = first.portfolio_id
    initial_generation = first.generation
    initial_digest = first.state_digest
    current = first
    receipts: list[AutonomousBurstTransitionReceipt] = []

    while True:
        if current.portfolio_id != portfolio_id:
            raise AutonomousBurstError("portfolio identity changed during burst")

        stop = _admissibility_stop(current)
        if stop is not None:
            return AutonomousBurstResult(
                trigger_digest=trigger.digest,
                policy_digest=policy.digest,
                portfolio_id=portfolio_id,
                initial_generation=initial_generation,
                final_generation=current.generation,
                initial_state_digest=initial_digest,
                final_state_digest=current.state_digest,
                transition_receipts=tuple(receipts),
                disposition="stopped",
                stop_reason=stop,
            )

        if len(receipts) >= policy.max_transitions:
            return AutonomousBurstResult(
                trigger_digest=trigger.digest,
                policy_digest=policy.digest,
                portfolio_id=portfolio_id,
                initial_generation=initial_generation,
                final_generation=current.generation,
                initial_state_digest=initial_digest,
                final_state_digest=current.state_digest,
                transition_receipts=tuple(receipts),
                disposition="transition_budget_exhausted",
                stop_reason="MAX_TRANSITIONS_REACHED",
            )

        if clock() - started >= policy.max_wall_seconds:
            return AutonomousBurstResult(
                trigger_digest=trigger.digest,
                policy_digest=policy.digest,
                portfolio_id=portfolio_id,
                initial_generation=initial_generation,
                final_generation=current.generation,
                initial_state_digest=initial_digest,
                final_state_digest=current.state_digest,
                transition_receipts=tuple(receipts),
                disposition="lease_exhausted",
                stop_reason="BURST_WALL_CLOCK_LEASE_EXHAUSTED",
            )

        receipt = execute_one(current)
        if receipt.portfolio_id != current.portfolio_id:
            raise AutonomousBurstError("transition receipt portfolio mismatch")
        if receipt.action_ref != current.next_action_ref:
            raise AutonomousBurstError("transition receipt action_ref mismatch")
        if receipt.pre_generation != current.generation:
            raise AutonomousBurstError("transition receipt generation mismatch")
        if receipt.pre_state_digest != current.state_digest:
            raise AutonomousBurstError("transition receipt pre-state mismatch")

        receipts.append(receipt)
        current = observe()

        if current.generation != receipt.post_generation:
            raise AutonomousBurstError(
                "fresh observation does not bind the exact post-transition generation"
            )
        if current.state_digest != receipt.post_state_digest:
            raise AutonomousBurstError(
                "fresh observation does not bind the exact post-transition state"
            )
