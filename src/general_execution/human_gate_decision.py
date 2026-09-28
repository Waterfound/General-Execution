from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .canonical import sha256_digest
from .execution_checkpoint import CheckpointEvidence, ExecutionCheckpoint
from .portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from .portfolio_state import PortfolioState

HUMAN_GATE_DECISION_SCHEMA = "ge.human-gate-decision.v1"
HUMAN_GATE_DECISION_RECEIPT_SCHEMA = "ge.human-gate-decision-receipt.v1"

HumanGateDecisionKind = Literal["reject", "supersede"]
HumanGateDecisionTarget = Literal["rework", "failed"]


class HumanGateDecisionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HumanGateDecisionError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise HumanGateDecisionError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise HumanGateDecisionError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


@dataclass(frozen=True, slots=True)
class HumanGateDecision:
    event_id: str
    portfolio_id: str
    expected_generation: int
    expected_state_digest: str
    pending_action_ref: str
    decision: HumanGateDecisionKind
    reason: str
    target_state: HumanGateDecisionTarget
    next_action_ref: str
    observed_at: str
    evidence: tuple[CheckpointEvidence, ...]
    canonical_refs: tuple[str, ...]
    schema_version: str = HUMAN_GATE_DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_GATE_DECISION_SCHEMA:
            raise HumanGateDecisionError("unsupported human gate decision schema")
        for name in (
            "event_id",
            "portfolio_id",
            "pending_action_ref",
            "reason",
            "next_action_ref",
            "observed_at",
        ):
            _nonempty(name, getattr(self, name))
        if type(self.expected_generation) is not int or self.expected_generation < 1:
            raise HumanGateDecisionError("expected_generation must be an integer >= 1")
        _digest("expected_state_digest", self.expected_state_digest)
        if self.decision not in {"reject", "supersede"}:
            raise HumanGateDecisionError("unsupported human gate decision")
        if self.target_state not in {"rework", "failed"}:
            raise HumanGateDecisionError("human gate decision target must be rework or failed")
        if self.target_state == "failed" and self.next_action_ref != "action://none":
            raise HumanGateDecisionError("failed decision must use action://none")
        if self.target_state == "rework" and not self.next_action_ref.startswith("action://"):
            raise HumanGateDecisionError("rework decision next action must use action://")
        if not self.evidence:
            raise HumanGateDecisionError("human gate decision requires evidence")
        identities = tuple(item.identity for item in self.evidence)
        if len(identities) != len(set(identities)):
            raise HumanGateDecisionError("human gate decision evidence must be unique")
        kinds = {item.kind for item in self.evidence}
        if self.decision == "supersede" and "superseding_evidence" not in kinds:
            raise HumanGateDecisionError(
                "supersede decision requires superseding_evidence"
            )
        if not self.canonical_refs:
            raise HumanGateDecisionError("human gate decision requires canonical refs")
        if len(self.canonical_refs) != len(set(self.canonical_refs)):
            raise HumanGateDecisionError("canonical refs must be unique")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.canonical_refs):
            raise HumanGateDecisionError("canonical refs must be non-empty strings")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class HumanGateDecisionReceipt:
    event_id: str
    portfolio_id: str
    expected_generation: int
    expected_state_digest: str
    pending_action_ref: str
    authority_boundary: str
    decision: HumanGateDecisionKind
    decision_digest: str
    target_state: HumanGateDecisionTarget
    next_action_ref: str
    provider_actor: str
    decision_ref: str
    schema_version: str = HUMAN_GATE_DECISION_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_GATE_DECISION_RECEIPT_SCHEMA:
            raise HumanGateDecisionError("unsupported human gate decision receipt schema")
        for name in (
            "event_id",
            "portfolio_id",
            "pending_action_ref",
            "authority_boundary",
            "next_action_ref",
            "provider_actor",
            "decision_ref",
        ):
            _nonempty(name, getattr(self, name))
        if type(self.expected_generation) is not int or self.expected_generation < 1:
            raise HumanGateDecisionError("expected_generation must be an integer >= 1")
        _digest("expected_state_digest", self.expected_state_digest)
        _digest("decision_digest", self.decision_digest)
        if self.decision not in {"reject", "supersede"}:
            raise HumanGateDecisionError("unsupported receipt decision")
        if self.target_state not in {"rework", "failed"}:
            raise HumanGateDecisionError("unsupported receipt target state")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class HumanGateDecisionResult:
    receipt: HumanGateDecisionReceipt
    state: PortfolioState
    checkpoint: ExecutionCheckpoint
    recovery_digest: str

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def consume_human_gate_decision(
    store: SqlitePortfolioHeadStore,
    decision: HumanGateDecision,
    *,
    provider_actor: str,
    decision_ref: str,
) -> HumanGateDecisionResult:
    """Consume an explicit human reject/supersede without creating authority.

    This channel can only move a durable human gate to rework or failed. It can
    never resume running work, grant a TransitionAuthorityGrant, or cross a
    release/deploy/spend boundary.
    """
    if provider_actor != "Waterfound":
        raise HumanGateDecisionError("human gate decision actor is not trusted")
    _nonempty("decision_ref", decision_ref)

    state, checkpoint, _ = recover_portfolio_after_restart(
        store, decision.portfolio_id
    )
    if state.active.state != "human_gate":
        raise HumanGateDecisionError("decision can be consumed only from human_gate")
    if checkpoint is None or not checkpoint.authority_stop:
        raise HumanGateDecisionError("human_gate has no durable authority-stop checkpoint")
    if (
        decision.expected_generation != state.generation
        or decision.expected_state_digest != state.digest
    ):
        raise HumanGateDecisionError("human gate decision is stale")
    if decision.pending_action_ref != state.active.next_action_ref:
        raise HumanGateDecisionError("pending action does not match current human gate")
    if not state.active.authority_boundary:
        raise HumanGateDecisionError("current human gate has no authority boundary")
    if checkpoint.authority_boundary != state.active.authority_boundary:
        raise HumanGateDecisionError("authority boundary checkpoint mismatch")
    if decision_ref in decision.canonical_refs:
        refs = decision.canonical_refs
    else:
        refs = tuple((*decision.canonical_refs, decision_ref))

    receipt = HumanGateDecisionReceipt(
        event_id=decision.event_id,
        portfolio_id=decision.portfolio_id,
        expected_generation=decision.expected_generation,
        expected_state_digest=decision.expected_state_digest,
        pending_action_ref=decision.pending_action_ref,
        authority_boundary=state.active.authority_boundary,
        decision=decision.decision,
        decision_digest=decision.digest,
        target_state=decision.target_state,
        next_action_ref=decision.next_action_ref,
        provider_actor=provider_actor,
        decision_ref=decision_ref,
    )
    receipt_evidence = CheckpointEvidence(
        kind="human_gate_decision",
        locator=decision_ref,
        digest=receipt.digest,
    )
    all_evidence = tuple((*decision.evidence, receipt_evidence))

    new_active = replace(
        state.active,
        state=decision.target_state,
        next_action_ref=decision.next_action_ref,
        authority_boundary=None,
        authority_ref=None,
        blockers=(),
        wake_condition=None,
    )
    new_state = PortfolioState(
        portfolio_id=state.portfolio_id,
        generation=state.generation + 1,
        active=new_active,
        secondary=state.secondary,
        passive=state.passive,
        previous_state_digest=state.digest,
    )
    next_refs = () if decision.target_state == "failed" else (decision.next_action_ref,)
    new_checkpoint = ExecutionCheckpoint(
        portfolio_id=new_state.portfolio_id,
        portfolio_generation=new_state.generation,
        portfolio_state_digest=new_state.digest,
        work_id=new_active.work_id,
        role="active",
        state_before="human_gate",
        state_after=decision.target_state,
        action_ref=f"human-decision://{decision.event_id}",
        source_revision=new_active.source_revision,
        observed_at=decision.observed_at,
        summary=(
            f"Waterfound {decision.decision} decision for {decision.pending_action_ref}: "
            f"{decision.reason}"
        ),
        evidence=all_evidence,
        canonical_refs=refs,
        uncertainties=(),
        next_transition_refs=next_refs,
        authority_stop=False,
        authority_boundary=None,
    )
    store.commit(
        state.portfolio_id,
        state.digest,
        new_state,
        new_checkpoint,
    )
    recovered, recovered_checkpoint, recovery = recover_portfolio_after_restart(
        store, state.portfolio_id
    )
    if recovered != new_state or recovered_checkpoint != new_checkpoint:
        raise HumanGateDecisionError("human gate decision cold recovery mismatch")
    return HumanGateDecisionResult(
        receipt=receipt,
        state=recovered,
        checkpoint=recovered_checkpoint,
        recovery_digest=recovery.digest,
    )
