from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest

TRANSITION_POLICY_SCHEMA = "ge.transition-policy.v1"
TRANSITION_RULE_SCHEMA = "ge.transition-rule.v1"

TransitionState = Literal[
    "ready",
    "running",
    "verifying",
    "complete",
    "waiting_external",
    "rework",
    "di_required",
    "human_gate",
    "failed",
    "passive",
]
TransitionEvent = Literal[
    "execution_started",
    "execution_completed",
    "verification_passed",
    "verification_failed",
    "external_blocker",
    "diagnosis_required",
    "authority_required",
    "wake_satisfied",
    "fatal_failure",
]
TransitionEffect = Literal[
    "none",
    "promote_secondary",
    "park_active",
    "wake_passive",
    "request_di",
    "stop_human_gate",
]
AuthorityMode = Literal["none", "preauthorized_required", "human_required"]

VALID_STATES = {
    "ready",
    "running",
    "verifying",
    "complete",
    "waiting_external",
    "rework",
    "di_required",
    "human_gate",
    "failed",
    "passive",
}
VALID_EVENTS = {
    "execution_started",
    "execution_completed",
    "verification_passed",
    "verification_failed",
    "external_blocker",
    "diagnosis_required",
    "authority_required",
    "wake_satisfied",
    "fatal_failure",
}
VALID_EFFECTS = {
    "none",
    "promote_secondary",
    "park_active",
    "wake_passive",
    "request_di",
    "stop_human_gate",
}
VALID_AUTHORITY_MODES = {"none", "preauthorized_required", "human_required"}


class TransitionPolicyError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TransitionPolicyError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _unique_nonempty(name: str, values: tuple[str, ...]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise TransitionPolicyError(f"{name} must contain only non-empty strings")
    if len(values) != len(set(values)):
        raise TransitionPolicyError(f"{name} must not contain duplicates")


def _require_exact_fields(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TransitionPolicyError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise TransitionPolicyError(
            f"{label} fields mismatch: missing={sorted(expected - actual)} "
            f"unknown={sorted(actual - expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class TransitionRule:
    rule_id: str
    from_state: TransitionState
    event: TransitionEvent
    to_state: TransitionState
    next_action_ref: str
    effect: TransitionEffect = "none"
    required_evidence: tuple[str, ...] = ()
    authority_mode: AuthorityMode = "none"
    authority_boundary: str | None = None
    schema_version: str = TRANSITION_RULE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TRANSITION_RULE_SCHEMA:
            raise TransitionPolicyError("unsupported transition rule schema")
        _nonempty("rule_id", self.rule_id)
        _nonempty("next_action_ref", self.next_action_ref)
        if self.from_state not in VALID_STATES or self.to_state not in VALID_STATES:
            raise TransitionPolicyError("unsupported transition state")
        if self.event not in VALID_EVENTS:
            raise TransitionPolicyError("unsupported transition event")
        if self.effect not in VALID_EFFECTS:
            raise TransitionPolicyError("unsupported transition effect")
        if self.authority_mode not in VALID_AUTHORITY_MODES:
            raise TransitionPolicyError("unsupported authority mode")
        _unique_nonempty("required_evidence", self.required_evidence)
        _optional_nonempty("authority_boundary", self.authority_boundary)

        if self.authority_mode == "none" and self.authority_boundary is not None:
            raise TransitionPolicyError(
                "authority_boundary requires an authority mode"
            )
        if self.authority_mode in {"preauthorized_required", "human_required"}:
            if self.authority_boundary is None:
                raise TransitionPolicyError(
                    "authority mode requires authority_boundary"
                )

        if self.authority_mode == "human_required":
            if self.to_state != "human_gate":
                raise TransitionPolicyError(
                    "human_required rule must transition to human_gate"
                )
            if self.effect != "stop_human_gate":
                raise TransitionPolicyError(
                    "human_required rule must use stop_human_gate effect"
                )

        if self.effect == "promote_secondary":
            if self.event != "verification_passed" or self.to_state != "complete":
                raise TransitionPolicyError(
                    "promote_secondary requires verification_passed -> complete"
                )

        if self.effect == "park_active":
            if self.event != "external_blocker" or self.to_state != "passive":
                raise TransitionPolicyError(
                    "park_active requires external_blocker -> passive"
                )

        if self.effect == "wake_passive":
            if self.from_state != "passive" or self.event != "wake_satisfied":
                raise TransitionPolicyError(
                    "wake_passive requires passive + wake_satisfied"
                )
            if self.to_state != "ready":
                raise TransitionPolicyError(
                    "wake_passive must transition to ready"
                )

        if self.effect == "request_di":
            if self.to_state != "di_required":
                raise TransitionPolicyError(
                    "request_di must transition to di_required"
                )

        if self.effect == "stop_human_gate" and self.authority_mode != "human_required":
            raise TransitionPolicyError(
                "stop_human_gate requires human_required authority mode"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def match_key(self) -> tuple[str, str]:
        return (self.from_state, self.event)


@dataclass(frozen=True, slots=True)
class TransitionPolicy:
    policy_id: str
    revision: str
    rules: tuple[TransitionRule, ...]
    default_disposition: Literal["stop"] = "stop"
    schema_version: str = TRANSITION_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TRANSITION_POLICY_SCHEMA:
            raise TransitionPolicyError("unsupported transition policy schema")
        _nonempty("policy_id", self.policy_id)
        _nonempty("revision", self.revision)
        if self.default_disposition != "stop":
            raise TransitionPolicyError("transition policy must fail closed with stop")
        if not self.rules:
            raise TransitionPolicyError("transition policy requires at least one rule")

        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise TransitionPolicyError("transition rule_id values must be unique")
        if rule_ids != tuple(sorted(rule_ids)):
            raise TransitionPolicyError(
                "transition rules must be sorted by rule_id for canonical policy"
            )

        match_keys = tuple(rule.match_key for rule in self.rules)
        if len(match_keys) != len(set(match_keys)):
            raise TransitionPolicyError(
                "transition policy cannot contain ambiguous state/event matches"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def transition_policy_to_dict(policy: TransitionPolicy) -> dict[str, Any]:
    return json.loads(canonical_json(policy))


def serialize_transition_policy(policy: TransitionPolicy) -> str:
    return canonical_json(policy)


def _rule_from_dict(data: Any) -> TransitionRule:
    obj = _require_exact_fields(
        data,
        {
            "rule_id",
            "from_state",
            "event",
            "to_state",
            "next_action_ref",
            "effect",
            "required_evidence",
            "authority_mode",
            "authority_boundary",
            "schema_version",
        },
        "transition rule",
    )
    if not isinstance(obj["required_evidence"], list):
        raise TransitionPolicyError("required_evidence must be a list")
    try:
        return TransitionRule(
            rule_id=obj["rule_id"],
            from_state=obj["from_state"],
            event=obj["event"],
            to_state=obj["to_state"],
            next_action_ref=obj["next_action_ref"],
            effect=obj["effect"],
            required_evidence=tuple(obj["required_evidence"]),
            authority_mode=obj["authority_mode"],
            authority_boundary=obj["authority_boundary"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise TransitionPolicyError("invalid transition rule") from exc


def transition_policy_from_dict(data: Any) -> TransitionPolicy:
    obj = _require_exact_fields(
        data,
        {
            "policy_id",
            "revision",
            "rules",
            "default_disposition",
            "schema_version",
        },
        "transition policy",
    )
    if not isinstance(obj["rules"], list):
        raise TransitionPolicyError("rules must be a list")
    try:
        return TransitionPolicy(
            policy_id=obj["policy_id"],
            revision=obj["revision"],
            rules=tuple(_rule_from_dict(item) for item in obj["rules"]),
            default_disposition=obj["default_disposition"],
            schema_version=obj["schema_version"],
        )
    except (TypeError, KeyError) as exc:
        raise TransitionPolicyError("invalid transition policy") from exc


def deserialize_transition_policy(payload: str) -> TransitionPolicy:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise TransitionPolicyError("transition policy is not valid JSON") from exc
    return transition_policy_from_dict(data)


def match_transition_rule(
    policy: TransitionPolicy,
    current_state: str,
    event: str,
) -> TransitionRule:
    if current_state not in VALID_STATES:
        raise TransitionPolicyError("unsupported current state")
    if event not in VALID_EVENTS:
        raise TransitionPolicyError("unsupported transition event")
    matches = tuple(
        rule
        for rule in policy.rules
        if rule.from_state == current_state and rule.event == event
    )
    if len(matches) != 1:
        raise TransitionPolicyError(
            "no unique admissible transition; default disposition is stop"
        )
    return matches[0]
