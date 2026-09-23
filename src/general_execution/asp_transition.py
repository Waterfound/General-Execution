from __future__ import annotations

from dataclasses import dataclass, replace

from .canonical import sha256_digest, stable_id
from .execution_checkpoint import CheckpointEvidence, ExecutionCheckpoint
from .portfolio_state import (
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
)
from .transition_policy import (
    TransitionPolicy,
    TransitionPolicyError,
    TransitionRule,
    match_transition_rule,
)

TRANSITION_AUTHORITY_SCHEMA = "ge.transition-authority-grant.v1"
WAKE_ADMISSION_SCHEMA = "ge.passive-wake-admission.v1"
TRANSITION_RESULT_SCHEMA = "ge.portfolio-transition-result.v1"

ROTATING_EFFECTS = {"promote_secondary", "park_active"}
MANDATORY_EFFECT_EVIDENCE = {
    "promote_secondary": {"verifier_pass"},
    "park_active": {"external_blocker", "no_internal_work"},
    "wake_passive": {"wake_condition_satisfied"},
}


class AspTransitionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AspTransitionError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise AspTransitionError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise AspTransitionError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _evidence_kinds(evidence: tuple[CheckpointEvidence, ...]) -> set[str]:
    if not evidence:
        raise AspTransitionError("transition requires admitted evidence")
    identities = tuple(item.identity for item in evidence)
    if len(identities) != len(set(identities)):
        raise AspTransitionError("transition evidence must not contain duplicates")
    return {item.kind for item in evidence}


def _verify_evidence(
    rule: TransitionRule,
    evidence: tuple[CheckpointEvidence, ...],
) -> None:
    kinds = _evidence_kinds(evidence)
    required = set(rule.required_evidence)
    missing = sorted(required - kinds)
    if missing:
        raise AspTransitionError(
            f"transition is missing policy-required evidence: {missing}"
        )
    mandatory = MANDATORY_EFFECT_EVIDENCE.get(rule.effect, set())
    missing_mandatory = sorted(mandatory - kinds)
    if missing_mandatory:
        raise AspTransitionError(
            f"transition is missing effect-required evidence: {missing_mandatory}"
        )


@dataclass(frozen=True, slots=True)
class TransitionAuthorityGrant:
    policy_digest: str
    rule_digest: str
    authority_boundary: str
    authority_ref: str
    authority_digest: str
    schema_version: str = TRANSITION_AUTHORITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TRANSITION_AUTHORITY_SCHEMA:
            raise AspTransitionError("unsupported transition authority schema")
        _digest("policy_digest", self.policy_digest)
        _digest("rule_digest", self.rule_digest)
        _nonempty("authority_boundary", self.authority_boundary)
        _nonempty("authority_ref", self.authority_ref)
        _digest("authority_digest", self.authority_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PassiveWakeAdmission:
    portfolio_id: str
    portfolio_generation: int
    portfolio_state_digest: str
    work_id: str
    wake_condition_digest: str
    policy_digest: str
    rule_digest: str
    evidence_digests: tuple[str, ...]
    next_action_ref: str
    authority_grant_digest: str | None = None
    schema_version: str = WAKE_ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WAKE_ADMISSION_SCHEMA:
            raise AspTransitionError("unsupported passive wake admission schema")
        _nonempty("portfolio_id", self.portfolio_id)
        _nonempty("work_id", self.work_id)
        _nonempty("next_action_ref", self.next_action_ref)
        if not isinstance(self.portfolio_generation, int) or isinstance(
            self.portfolio_generation, bool
        ):
            raise AspTransitionError("portfolio_generation must be an integer")
        if self.portfolio_generation < 0:
            raise AspTransitionError("portfolio_generation cannot be negative")
        for name in (
            "portfolio_state_digest",
            "wake_condition_digest",
            "policy_digest",
            "rule_digest",
        ):
            _digest(name, getattr(self, name))
        if not self.evidence_digests:
            raise AspTransitionError("wake admission requires evidence digests")
        if tuple(sorted(self.evidence_digests)) != self.evidence_digests:
            raise AspTransitionError(
                "wake admission evidence digests must be canonical-sorted"
            )
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise AspTransitionError(
                "wake admission evidence digests must be unique"
            )
        for value in self.evidence_digests:
            _digest("evidence_digest", value)
        if self.authority_grant_digest is not None:
            _digest("authority_grant_digest", self.authority_grant_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def admission_id(self) -> str:
        return stable_id("gew", self)


@dataclass(frozen=True, slots=True)
class PortfolioTransitionResult:
    previous_state_digest: str
    policy_digest: str
    rule_digest: str
    effect: str
    new_state: PortfolioState
    checkpoint: ExecutionCheckpoint
    replacement_secondary_work_id: str | None = None
    authority_grant_digest: str | None = None
    wake_admission_digest: str | None = None
    schema_version: str = TRANSITION_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TRANSITION_RESULT_SCHEMA:
            raise AspTransitionError("unsupported portfolio transition result schema")
        for name in ("previous_state_digest", "policy_digest", "rule_digest"):
            _digest(name, getattr(self, name))
        _optional_nonempty(
            "replacement_secondary_work_id",
            self.replacement_secondary_work_id,
        )
        if self.authority_grant_digest is not None:
            _digest("authority_grant_digest", self.authority_grant_digest)
        if self.wake_admission_digest is not None:
            _digest("wake_admission_digest", self.wake_admission_digest)

        if self.new_state.previous_state_digest != self.previous_state_digest:
            raise AspTransitionError(
                "transition result state predecessor does not match previous state"
            )
        if (
            self.checkpoint.portfolio_id != self.new_state.portfolio_id
            or self.checkpoint.portfolio_generation != self.new_state.generation
            or self.checkpoint.portfolio_state_digest != self.new_state.digest
        ):
            raise AspTransitionError(
                "transition result checkpoint does not bind new state"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _verify_authority(
    policy: TransitionPolicy,
    rule: TransitionRule,
    grant: TransitionAuthorityGrant | None,
) -> str | None:
    if rule.authority_mode == "none":
        if grant is not None:
            raise AspTransitionError(
                "ordinary transition cannot consume an authority grant"
            )
        return None

    if rule.authority_mode == "human_required":
        if grant is not None:
            raise AspTransitionError(
                "human-required transition stops before authority is granted"
            )
        return None

    if rule.authority_mode != "preauthorized_required":
        raise AspTransitionError("unsupported transition authority mode")
    if grant is None:
        raise AspTransitionError(
            "preauthorized transition requires bounded authority grant"
        )
    if (
        grant.policy_digest != policy.digest
        or grant.rule_digest != rule.digest
        or grant.authority_boundary != rule.authority_boundary
    ):
        raise AspTransitionError(
            "transition authority grant does not bind policy/rule boundary"
        )
    return grant.digest


def _find_passive(state: PortfolioState, work_id: str) -> PortfolioEntry:
    matches = tuple(item for item in state.passive if item.work_id == work_id)
    if len(matches) != 1:
        raise AspTransitionError("passive work item is not uniquely present")
    return matches[0]


def admit_passive_wake(
    state: PortfolioState,
    policy: TransitionPolicy,
    work_id: str,
    evidence: tuple[CheckpointEvidence, ...],
    *,
    authority_grant: TransitionAuthorityGrant | None = None,
) -> PassiveWakeAdmission:
    item = _find_passive(state, work_id)
    if item.wake_condition is None:
        raise AspTransitionError("passive work item has no explicit wake condition")

    try:
        rule = match_transition_rule(policy, "passive", "wake_satisfied")
    except TransitionPolicyError as exc:
        raise AspTransitionError(str(exc)) from exc
    if rule.effect != "wake_passive":
        raise AspTransitionError(
            "passive wake requires a wake_passive transition rule"
        )

    _verify_evidence(rule, evidence)
    grant_digest = _verify_authority(policy, rule, authority_grant)
    evidence_digests = tuple(sorted(item.digest for item in evidence))

    return PassiveWakeAdmission(
        portfolio_id=state.portfolio_id,
        portfolio_generation=state.generation,
        portfolio_state_digest=state.digest,
        work_id=item.work_id,
        wake_condition_digest=item.wake_condition.digest,
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        evidence_digests=evidence_digests,
        next_action_ref=rule.next_action_ref,
        authority_grant_digest=grant_digest,
    )


def _secondary_from_wake(
    state: PortfolioState,
    policy: TransitionPolicy,
    admission: PassiveWakeAdmission,
) -> tuple[PortfolioEntry, tuple[PortfolioEntry, ...]]:
    if (
        admission.portfolio_id != state.portfolio_id
        or admission.portfolio_generation != state.generation
        or admission.portfolio_state_digest != state.digest
        or admission.policy_digest != policy.digest
    ):
        raise AspTransitionError("wake admission is stale or belongs to another portfolio")

    item = _find_passive(state, admission.work_id)
    if item.wake_condition is None:
        raise AspTransitionError("wake admission target has no wake condition")
    if item.wake_condition.digest != admission.wake_condition_digest:
        raise AspTransitionError("wake admission does not bind current wake condition")

    try:
        wake_rule = match_transition_rule(policy, "passive", "wake_satisfied")
    except TransitionPolicyError as exc:
        raise AspTransitionError(str(exc)) from exc
    if (
        wake_rule.effect != "wake_passive"
        or wake_rule.digest != admission.rule_digest
        or wake_rule.next_action_ref != admission.next_action_ref
    ):
        raise AspTransitionError("wake admission does not bind current wake rule")

    replacement = replace(
        item,
        role="secondary",
        state="ready",
        next_action_ref=wake_rule.next_action_ref,
        blockers=(),
        wake_condition=None,
        authority_boundary=None,
        authority_ref=None,
    )
    remaining = tuple(
        sorted(
            (entry for entry in state.passive if entry.work_id != item.work_id),
            key=lambda entry: entry.work_id,
        )
    )
    return replacement, remaining


def _external_secondary(
    state: PortfolioState,
    replacement: PortfolioEntry,
) -> tuple[PortfolioEntry, tuple[PortfolioEntry, ...]]:
    if replacement.role != "secondary" or replacement.state != "ready":
        raise AspTransitionError(
            "replacement secondary must be role=secondary and state=ready"
        )
    current_ids = {
        state.active.work_id,
        state.secondary.work_id,
        *(entry.work_id for entry in state.passive),
    }
    if replacement.work_id in current_ids:
        raise AspTransitionError(
            "external replacement secondary must have a new work_id"
        )
    return replacement, state.passive


def _replacement_secondary(
    state: PortfolioState,
    policy: TransitionPolicy,
    replacement: PortfolioEntry | None,
    wake_admission: PassiveWakeAdmission | None,
) -> tuple[PortfolioEntry, tuple[PortfolioEntry, ...], str | None]:
    if (replacement is None) == (wake_admission is None):
        raise AspTransitionError(
            "rotating transition requires exactly one replacement-secondary source"
        )
    if wake_admission is not None:
        item, remaining = _secondary_from_wake(state, policy, wake_admission)
        return item, remaining, wake_admission.digest
    assert replacement is not None
    item, remaining = _external_secondary(state, replacement)
    return item, remaining, None


def _promoted_active(entry: PortfolioEntry) -> PortfolioEntry:
    return replace(
        entry,
        role="active",
        state="ready",
        blockers=(),
        wake_condition=None,
        authority_boundary=None,
        authority_ref=None,
    )


def _parked_active(entry: PortfolioEntry, rule: TransitionRule) -> PortfolioEntry:
    if entry.state != "waiting_external":
        raise AspTransitionError(
            "park_active requires current Active state=waiting_external"
        )
    if not entry.blockers or entry.wake_condition is None:
        raise AspTransitionError(
            "park_active requires blocker and explicit wake condition"
        )
    return replace(
        entry,
        role="passive",
        state="passive",
        next_action_ref=rule.next_action_ref,
        authority_boundary=None,
        authority_ref=None,
    )


def _authority_stopped_active(
    entry: PortfolioEntry,
    rule: TransitionRule,
    evidence: tuple[CheckpointEvidence, ...],
) -> PortfolioEntry:
    if rule.authority_boundary is None:
        raise AspTransitionError("human-gate rule has no authority boundary")
    evidence_refs = tuple(sorted({item.locator for item in evidence}))
    blocker = PortfolioBlocker(
        kind="authority",
        detail=rule.authority_boundary,
        evidence_refs=evidence_refs,
    )
    return replace(
        entry,
        state="human_gate",
        next_action_ref=rule.next_action_ref,
        authority_boundary=rule.authority_boundary,
        authority_ref=None,
        blockers=(blocker,),
        wake_condition=None,
    )


def apply_active_transition(
    state: PortfolioState,
    policy: TransitionPolicy,
    event: str,
    evidence: tuple[CheckpointEvidence, ...],
    *,
    action_ref: str,
    observed_at: str,
    summary: str,
    canonical_refs: tuple[str, ...],
    uncertainties: tuple[str, ...] = (),
    replacement_secondary: PortfolioEntry | None = None,
    wake_admission: PassiveWakeAdmission | None = None,
    authority_grant: TransitionAuthorityGrant | None = None,
) -> PortfolioTransitionResult:
    _nonempty("action_ref", action_ref)
    _nonempty("observed_at", observed_at)
    _nonempty("summary", summary)
    if not canonical_refs:
        raise AspTransitionError("transition requires canonical_refs")

    try:
        rule = match_transition_rule(policy, state.active.state, event)
    except TransitionPolicyError as exc:
        raise AspTransitionError(str(exc)) from exc
    if rule.effect == "wake_passive":
        raise AspTransitionError(
            "wake_passive is admitted separately and cannot target Active"
        )

    _verify_evidence(rule, evidence)
    authority_grant_digest = _verify_authority(
        policy,
        rule,
        authority_grant,
    )

    passive_entries = state.passive
    replacement_work_id: str | None = None
    wake_admission_digest: str | None = None

    if rule.effect in ROTATING_EFFECTS:
        replacement, passive_entries, wake_admission_digest = _replacement_secondary(
            state,
            policy,
            replacement_secondary,
            wake_admission,
        )
        replacement_work_id = replacement.work_id
        new_active = _promoted_active(state.secondary)

        if rule.effect == "promote_secondary":
            pass
        else:
            parked = _parked_active(state.active, rule)
            passive_entries = tuple(
                sorted((*passive_entries, parked), key=lambda entry: entry.work_id)
            )
        new_secondary = replacement

    else:
        if replacement_secondary is not None or wake_admission is not None:
            raise AspTransitionError(
                "non-rotating transition cannot consume a replacement secondary"
            )
        new_secondary = state.secondary

        if rule.effect == "stop_human_gate":
            new_active = _authority_stopped_active(state.active, rule, evidence)
        else:
            try:
                new_active = replace(
                    state.active,
                    state=rule.to_state,
                    next_action_ref=rule.next_action_ref,
                )
            except ValueError as exc:
                raise AspTransitionError(
                    "transition target is incompatible with current Active metadata"
                ) from exc

    new_state = PortfolioState(
        portfolio_id=state.portfolio_id,
        generation=state.generation + 1,
        active=new_active,
        secondary=new_secondary,
        passive=tuple(sorted(passive_entries, key=lambda entry: entry.work_id)),
        previous_state_digest=state.digest,
    )

    authority_stop = rule.authority_mode == "human_required"
    next_transition_refs: tuple[str, ...]
    if authority_stop or rule.to_state in {"complete", "failed"}:
        next_transition_refs = ()
    else:
        next_transition_refs = (rule.next_action_ref,)

    refs = tuple(
        dict.fromkeys(
            (
                *canonical_refs,
                f"policy:{policy.digest}",
                f"rule:{rule.digest}",
                *(
                    (authority_grant.authority_ref,)
                    if authority_grant is not None
                    else ()
                ),
            )
        )
    )

    checkpoint = ExecutionCheckpoint(
        portfolio_id=new_state.portfolio_id,
        portfolio_generation=new_state.generation,
        portfolio_state_digest=new_state.digest,
        work_id=state.active.work_id,
        role="active",
        state_before=state.active.state,
        state_after=rule.to_state,
        action_ref=action_ref,
        source_revision=state.active.source_revision,
        observed_at=observed_at,
        summary=summary,
        evidence=evidence,
        canonical_refs=refs,
        uncertainties=uncertainties,
        next_transition_refs=next_transition_refs,
        authority_stop=authority_stop,
        authority_boundary=rule.authority_boundary if authority_stop else None,
    )

    return PortfolioTransitionResult(
        previous_state_digest=state.digest,
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        effect=rule.effect,
        new_state=new_state,
        checkpoint=checkpoint,
        replacement_secondary_work_id=replacement_work_id,
        authority_grant_digest=authority_grant_digest,
        wake_admission_digest=wake_admission_digest,
    )
