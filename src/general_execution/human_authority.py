from __future__ import annotations

from dataclasses import dataclass, replace

from .asp_transition import TransitionAuthorityGrant
from .canonical import sha256_digest
from .portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from .resume_tick import (
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    ResumeTickObservation,
    ResumeTickResult,
    resume_tick,
)
from .transition_policy import (
    TransitionPolicy,
    match_transition_rule,
)

HUMAN_AUTHORITY_RECEIPT_SCHEMA = "ge.human-authority-receipt.v1"


class HumanAuthorityError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HumanAuthorityError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise HumanAuthorityError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise HumanAuthorityError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class HumanAuthorityReceipt:
    event_id: str
    portfolio_id: str
    expected_generation: int
    expected_state_digest: str
    policy_digest: str
    rule_digest: str
    authority_boundary: str
    approved_action_ref: str
    approved_at: str
    provider_actor: str
    authority_ref: str
    schema_version: str = HUMAN_AUTHORITY_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_AUTHORITY_RECEIPT_SCHEMA:
            raise HumanAuthorityError("unsupported human authority receipt schema")
        for name in (
            "event_id",
            "portfolio_id",
            "authority_boundary",
            "approved_action_ref",
            "approved_at",
            "provider_actor",
            "authority_ref",
        ):
            _nonempty(name, getattr(self, name))
        if not isinstance(self.expected_generation, int) or isinstance(
            self.expected_generation, bool
        ):
            raise HumanAuthorityError("expected_generation must be an integer")
        if self.expected_generation < 0:
            raise HumanAuthorityError("expected_generation cannot be negative")
        for name in ("expected_state_digest", "policy_digest", "rule_digest"):
            _digest(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def admit_human_authority(
    store: SqlitePortfolioHeadStore,
    policy: TransitionPolicy,
    observation: ResumeTickObservation,
    *,
    event_id: str,
    approved_action_ref: str,
    approved_at: str,
    provider_actor: str,
    authority_ref: str,
) -> tuple[HumanAuthorityReceipt, ResumeTickObservation]:
    """Bind explicit human approval to one exact post-gate transition.

    The ordinary persistent transport remains unable to carry authority.  This
    function is for the separate, host-authenticated human-authority channel.
    """
    if provider_actor != "Waterfound":
        raise HumanAuthorityError("human authority provider actor is not trusted")
    if observation.authority_grant is not None:
        raise HumanAuthorityError("authority input observation must not self-carry a grant")

    state, checkpoint, _ = recover_portfolio_after_restart(
        store,
        observation.portfolio_id,
    )
    if state.active.state != "human_gate":
        raise HumanAuthorityError("human authority can be consumed only from human_gate")
    if checkpoint is None or not checkpoint.authority_stop:
        raise HumanAuthorityError("human_gate has no durable authority-stop checkpoint")
    if (
        observation.expected_generation != state.generation
        or observation.expected_state_digest != state.digest
    ):
        raise HumanAuthorityError("human authority observation is stale")
    if observation.policy_digest != policy.digest:
        raise HumanAuthorityError("human authority policy digest mismatch")
    if approved_action_ref != state.active.next_action_ref:
        raise HumanAuthorityError("approved action does not match the pending human gate")

    try:
        rule = match_transition_rule(
            policy,
            state.active.state,
            observation.event,
        )
    except ValueError as exc:
        raise HumanAuthorityError(str(exc)) from exc

    if rule.authority_mode != "preauthorized_required":
        raise HumanAuthorityError(
            "human authority bridge requires preauthorized_required transition"
        )
    if not rule.authority_boundary:
        raise HumanAuthorityError("authorized transition has no authority boundary")
    if state.active.authority_boundary != rule.authority_boundary:
        raise HumanAuthorityError(
            "authorized transition boundary does not match the pending human gate"
        )

    receipt = HumanAuthorityReceipt(
        event_id=event_id,
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        authority_boundary=rule.authority_boundary,
        approved_action_ref=approved_action_ref,
        approved_at=approved_at,
        provider_actor=provider_actor,
        authority_ref=authority_ref,
    )
    grant = TransitionAuthorityGrant(
        policy_digest=policy.digest,
        rule_digest=rule.digest,
        authority_boundary=rule.authority_boundary,
        authority_ref=authority_ref,
        authority_digest=receipt.digest,
    )
    refs = tuple(dict.fromkeys((*observation.canonical_refs, authority_ref)))
    bound = replace(
        observation,
        canonical_refs=refs,
        authority_grant=grant,
    )
    return receipt, bound


def consume_human_authority(
    store: SqlitePortfolioHeadStore,
    policy: TransitionPolicy,
    observation: ResumeTickObservation,
    *,
    event_id: str,
    approved_action_ref: str,
    approved_at: str,
    provider_actor: str,
    authority_ref: str,
    core_requirement: CoreVerificationRequirement,
    core_verification: CoreVerificationReceipt,
) -> tuple[HumanAuthorityReceipt, ResumeTickObservation, ResumeTickResult]:
    receipt, bound = admit_human_authority(
        store,
        policy,
        observation,
        event_id=event_id,
        approved_action_ref=approved_action_ref,
        approved_at=approved_at,
        provider_actor=provider_actor,
        authority_ref=authority_ref,
    )
    result = resume_tick(
        store,
        observation.portfolio_id,
        policy,
        bound,
        core_requirement=core_requirement,
        core_verification=core_verification,
    )
    return receipt, bound, result
