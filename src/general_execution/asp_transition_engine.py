from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .canonical import sha256_digest
from .execution_checkpoint import CheckpointEvidence, ExecutionCheckpoint
from .portfolio_state import (
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
    WakeCondition,
)
from .transition_policy import (
    TransitionPolicy,
    TransitionPolicyError,
    TransitionRule,
    match_transition_rule,
)

ASP_APPLICATION_SCHEMA = "ge.asp-transition-application.v1"
WAKE_SIGNAL_SCHEMA = "ge.passive-wake-signal.v1"
WAKE_ADMISSION_SCHEMA = "ge.passive-wake-admission.v1"

AspEffect = Literal[
    "none",
    "promote_secondary",
    "park_active",
    "request_di",
    "stop_human_gate",
]


class AspTransitionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AspTransitionError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise AspTransitionError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise AspTransitionError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _required_evidence(
    rule: TransitionRule,
    evidence: tuple[CheckpointEvidence, ...],
) -> None:
    available = {item.kind for item in evidence}
    missing = tuple(kind for kind in rule.required_evidence if kind not in available)
    if missing:
        raise AspTransitionError(
            f"transition evidence requirements not satisfied: {missing}"
        )


def _evidence_refs(evidence: tuple[CheckpointEvidence, ...]) -> tuple[str, ...]:
    return tuple(sorted({item.locator for item in evidence}))


@dataclass(frozen=True, slots=True)
class PassiveWakeSignal:
    work_id: str
    condition_digest: str
    evidence_digest: str
    schema_version: str = WAKE_SIGNAL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WAKE_SIGNAL_SCHEMA:
            raise AspTransitionError("unsupported passive wake signal schema")
        _nonempty("work_id", self.work_id)
        _digest("condition_digest", self.condition_digest)
        _digest("evidence_digest", self.evidence_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PassiveWakeAdmission:
    work_id: str
    policy_digest: str
    rule_digest: str
    condition_digest: str
    evidence_digest: str
    candidate_secondary: PortfolioEntry
    schema_version: str = WAKE_ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WAKE_ADMISSION_SCHEMA:
            raise AspTransitionError("unsupported passive wake admission schema")
        _nonempty("work_id", self.work_id)
        for name in (
            "policy_digest",
            "rule_digest",
            "condition_digest",
            "evidence_digest",
        ):
            _digest(name, getattr(self, name))
        if self.candidate_secondary.work_id != self.work_id:
            raise AspTransitionError("wake admission candidate identity mismatch")
        if (
            self.candidate_secondary.role != "secondary"
            or self.candidate_secondary.state != "ready"
        ):
            raise AspTransitionError(
                "wake admission candidate must be secondary/ready"
            )
        if self.candidate_secondary.blockers:
            raise AspTransitionError(
                "wake admission candidate cannot retain blockers"
            )
        if self.candidate_secondary.wake_condition is not None:
            raise AspTransitionError(
                "wake admission candidate cannot retain wake condition"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AspTransitionApplication:
    previous_state_digest: str
    next_state: PortfolioState
    checkpoint: ExecutionCheckpoint
    policy_digest: str
    rule_digest: str
    event: str
    effect: AspEffect
    wake_admission_digest: str | None = None
    schema_version: str = ASP_APPLICATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ASP_APPLICATION_SCHEMA:
            raise AspTransitionError("unsupported ASP transition application schema")
        _digest("previous_state_digest", self.previous_state_digest)
        _digest("policy_digest", self.policy_digest)
        _digest("rule_digest", self.rule_digest)
        _nonempty("event", self.event)
        if self.effect not in {
            "none",
            "promote_secondary",
            "park_active",
            "request_di",
            "stop_human_gate",
        }:
            raise AspTransitionError("unsupported ASP application effect")
        if self.wake_admission_digest is not None:
            _digest("wake_admission_digest", self.wake_admission_digest)
        if self.next_state.previous_state_digest != self.previous_state_digest:
            raise AspTransitionError("application predecessor does not bind next state")
        if self.checkpoint.portfolio_id != self.next_state.portfolio_id:
            raise AspTransitionError("application checkpoint portfolio mismatch")
        if self.checkpoint.portfolio_generation != self.next_state.generation:
            raise AspTransitionError("application checkpoint generation mismatch")
        if self.checkpoint.portfolio_state_digest != self.next_state.digest:
            raise AspTransitionError("application checkpoint state digest mismatch")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _wake_candidate(entry: PortfolioEntry) -> PortfolioEntry:
    return replace(
        entry,
        role="secondary",
        state="ready",
        blockers=(),
        wake_condition=None,
        authority_boundary=None,
        authority_ref=None,
    )


def admit_passive_wake(
    policy: TransitionPolicy,
    entry: PortfolioEntry,
    signal: PassiveWakeSignal,
    evidence: tuple[CheckpointEvidence, ...],
) -> PassiveWakeAdmission:
    if entry.role != "passive" or entry.state != "passive":
        raise AspTransitionError("wake admission requires a passive entry")
    if entry.wake_condition is None:
        raise AspTransitionError("passive entry has no wake condition")
    if signal.work_id != entry.work_id:
        raise AspTransitionError("wake signal work identity mismatch")
    if signal.condition_digest != entry.wake_condition.digest:
        raise AspTransitionError("wake signal condition does not match passive entry")
    if signal.evidence_digest not in {item.evidence_digest for item in evidence}:
        raise AspTransitionError("wake signal evidence is not admitted")

    try:
        rule = match_transition_rule(policy, "passive", "wake_satisfied")
    except TransitionPolicyError as exc:
        raise AspTransitionError("wake transition is not policy-admissible") from exc
    if rule.effect != "wake_passive" or rule.to_state != "ready":
        raise AspTransitionError("wake policy rule has invalid effect")
    _required_evidence(rule, evidence)

    candidate = _wake_candidate(entry)
    return PassiveWakeAdmission(
        work_id=entry.work_id,
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        condition_digest=signal.condition_digest,
        evidence_digest=signal.evidence_digest,
        candidate_secondary=candidate,
    )


def _find_passive(
    state: PortfolioState,
    work_id: str,
) -> PortfolioEntry:
    matches = tuple(item for item in state.passive if item.work_id == work_id)
    if len(matches) != 1:
        raise AspTransitionError(
            "wake admission work item is not uniquely present in passive portfolio"
        )
    return matches[0]


def _verify_wake_admission(
    state: PortfolioState,
    policy: TransitionPolicy,
    admission: PassiveWakeAdmission,
    evidence: tuple[CheckpointEvidence, ...],
) -> PortfolioEntry:
    if admission.policy_digest != policy.digest:
        raise AspTransitionError("wake admission policy digest mismatch")
    entry = _find_passive(state, admission.work_id)
    if entry.wake_condition is None:
        raise AspTransitionError("wake admission source has no wake condition")
    if admission.condition_digest != entry.wake_condition.digest:
        raise AspTransitionError("wake admission condition digest mismatch")
    if admission.evidence_digest not in {item.evidence_digest for item in evidence}:
        raise AspTransitionError("wake admission evidence is not present")
    try:
        wake_rule = match_transition_rule(policy, "passive", "wake_satisfied")
    except TransitionPolicyError as exc:
        raise AspTransitionError("wake transition is not policy-admissible") from exc
    if admission.rule_digest != wake_rule.digest:
        raise AspTransitionError("wake admission rule digest mismatch")
    expected = _wake_candidate(entry)
    if admission.candidate_secondary != expected:
        raise AspTransitionError("wake admission candidate does not reproduce")
    _required_evidence(wake_rule, evidence)
    return entry


def _promoted_active(entry: PortfolioEntry) -> PortfolioEntry:
    if entry.role != "secondary" or entry.state != "ready":
        raise AspTransitionError("promotion requires the current secondary/ready entry")
    return replace(
        entry,
        role="active",
        state="ready",
        blockers=(),
        wake_condition=None,
        authority_boundary=None,
        authority_ref=None,
    )


def _next_state(
    current: PortfolioState,
    *,
    active: PortfolioEntry,
    secondary: PortfolioEntry,
    passive: tuple[PortfolioEntry, ...],
) -> PortfolioState:
    return PortfolioState(
        portfolio_id=current.portfolio_id,
        generation=current.generation + 1,
        active=active,
        secondary=secondary,
        passive=tuple(sorted(passive, key=lambda item: item.work_id)),
        previous_state_digest=current.digest,
    )


def apply_asp_transition(
    current: PortfolioState,
    policy: TransitionPolicy,
    event: str,
    evidence: tuple[CheckpointEvidence, ...],
    *,
    observed_at: str,
    summary: str,
    canonical_refs: tuple[str, ...],
    uncertainties: tuple[str, ...] = (),
    wake_admission: PassiveWakeAdmission | None = None,
    park_blockers: tuple[PortfolioBlocker, ...] = (),
    park_wake_condition: WakeCondition | None = None,
    preauthorized_authority_ref: str | None = None,
) -> AspTransitionApplication:
    if not evidence:
        raise AspTransitionError("ASP transition requires admitted evidence")
    _nonempty("observed_at", observed_at)
    _nonempty("summary", summary)
    if not canonical_refs:
        raise AspTransitionError("ASP transition requires canonical_refs")

    try:
        rule = match_transition_rule(policy, current.active.state, event)
    except TransitionPolicyError as exc:
        raise AspTransitionError("active transition is not policy-admissible") from exc
    if rule.effect == "wake_passive":
        raise AspTransitionError(
            "wake_passive must be admitted as a replacement candidate, not applied to active"
        )
    _required_evidence(rule, evidence)

    if rule.authority_mode == "preauthorized_required":
        if not preauthorized_authority_ref:
            raise AspTransitionError(
                "preauthorized transition requires authority reference"
            )
        if not any(
            item.kind == "authority" and item.locator == preauthorized_authority_ref
            for item in evidence
        ):
            raise AspTransitionError(
                "preauthorized authority reference is not evidence-bound"
            )
    elif preauthorized_authority_ref is not None:
        raise AspTransitionError(
            "authority reference supplied to transition that does not require it"
        )

    checkpoint_work = current.active
    checkpoint_after = rule.to_state
    authority_stop = False
    authority_boundary = None
    wake_digest = None

    if rule.effect in {"promote_secondary", "park_active"}:
        if wake_admission is None:
            raise AspTransitionError(
                "lane transition requires an explicitly admitted replacement secondary"
            )
        replacement_source = _verify_wake_admission(
            current,
            policy,
            wake_admission,
            evidence,
        )
        wake_digest = wake_admission.digest
        new_active = _promoted_active(current.secondary)
        new_secondary = wake_admission.candidate_secondary
        remaining = tuple(
            item
            for item in current.passive
            if item.work_id != replacement_source.work_id
        )

        if rule.effect == "promote_secondary":
            if current.active.state != "verifying":
                raise AspTransitionError(
                    "secondary promotion requires active state verifying"
                )
            new_passive = remaining
        else:
            if not park_blockers:
                raise AspTransitionError("parking active requires explicit blockers")
            if park_wake_condition is None:
                raise AspTransitionError(
                    "parking active requires explicit wake condition"
                )
            parked = replace(
                current.active,
                role="passive",
                state="passive",
                blockers=park_blockers,
                wake_condition=park_wake_condition,
                authority_boundary=None,
                authority_ref=None,
            )
            new_passive = (*remaining, parked)

        next_state = _next_state(
            current,
            active=new_active,
            secondary=new_secondary,
            passive=new_passive,
        )
        next_transition_refs = (new_active.next_action_ref,)

    elif rule.effect == "stop_human_gate":
        if rule.authority_mode != "human_required" or not rule.authority_boundary:
            raise AspTransitionError("human gate rule is missing authority boundary")
        blocker = PortfolioBlocker(
            kind="authority",
            detail=rule.authority_boundary,
            evidence_refs=_evidence_refs(evidence),
        )
        new_active = replace(
            current.active,
            state="human_gate",
            next_action_ref=rule.next_action_ref,
            blockers=(blocker,),
            wake_condition=None,
            authority_boundary=rule.authority_boundary,
            authority_ref=None,
        )
        next_state = _next_state(
            current,
            active=new_active,
            secondary=current.secondary,
            passive=current.passive,
        )
        authority_stop = True
        authority_boundary = rule.authority_boundary
        next_transition_refs = ()

    else:
        if park_blockers or park_wake_condition is not None or wake_admission is not None:
            raise AspTransitionError(
                "lane-management inputs supplied to non-lane transition"
            )
        new_active = replace(
            current.active,
            state=rule.to_state,
            next_action_ref=rule.next_action_ref,
            wake_condition=None,
            authority_boundary=(
                rule.authority_boundary
                if rule.authority_mode == "preauthorized_required"
                else None
            ),
            authority_ref=(
                preauthorized_authority_ref
                if rule.authority_mode == "preauthorized_required"
                else None
            ),
        )
        next_state = _next_state(
            current,
            active=new_active,
            secondary=current.secondary,
            passive=current.passive,
        )
        next_transition_refs = (
            ()
            if rule.to_state in {"complete", "failed"}
            else (rule.next_action_ref,)
        )

    checkpoint = ExecutionCheckpoint(
        portfolio_id=next_state.portfolio_id,
        portfolio_generation=next_state.generation,
        portfolio_state_digest=next_state.digest,
        work_id=checkpoint_work.work_id,
        role="active",
        state_before=checkpoint_work.state,
        state_after=checkpoint_after,
        action_ref=checkpoint_work.next_action_ref,
        source_revision=checkpoint_work.source_revision,
        observed_at=observed_at,
        summary=summary,
        evidence=evidence,
        canonical_refs=canonical_refs,
        uncertainties=uncertainties,
        next_transition_refs=next_transition_refs,
        authority_stop=authority_stop,
        authority_boundary=authority_boundary,
    )

    effect: AspEffect = rule.effect  # type: ignore[assignment]
    return AspTransitionApplication(
        previous_state_digest=current.digest,
        next_state=next_state,
        checkpoint=checkpoint,
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        event=event,
        effect=effect,
        wake_admission_digest=wake_digest,
    )
