from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest
from .portfolio_state import VALID_ROLES, VALID_STATES

EVIDENCE_SCHEMA = "ge.admitted-evidence.v1"
RULE_SCHEMA = "ge.transition-rule.v1"
POLICY_SCHEMA = "ge.transition-policy.v1"
REQUEST_SCHEMA = "ge.transition-request.v1"
DECISION_SCHEMA = "ge.transition-decision.v1"

TransitionSignal = Literal[
    "start_authorized",
    "execution_completed",
    "verification_passed",
    "verification_rejected",
    "external_blocker_confirmed",
    "failure_confirmed",
    "wake_confirmed",
    "authority_boundary_reached",
    "authority_presented",
]

VALID_SIGNALS = {
    "start_authorized",
    "execution_completed",
    "verification_passed",
    "verification_rejected",
    "external_blocker_confirmed",
    "failure_confirmed",
    "wake_confirmed",
    "authority_boundary_reached",
    "authority_presented",
}

EVIDENCE_REQUIRED_SIGNALS = {
    "execution_completed",
    "verification_passed",
    "verification_rejected",
    "external_blocker_confirmed",
    "failure_confirmed",
    "wake_confirmed",
    "authority_boundary_reached",
}


class TransitionPolicyError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TransitionPolicyError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise TransitionPolicyError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise TransitionPolicyError(f"{name} must contain 64 hexadecimal characters") from exc


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
            f"{label} fields mismatch: "
            f"missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )
    return data


def _role_state_valid(role: str, state: str) -> bool:
    if role == "active":
        return state in VALID_STATES - {"passive"}
    if role == "secondary":
        return state == "ready"
    if role == "passive":
        return state == "passive"
    return False


@dataclass(frozen=True, slots=True)
class AdmittedEvidence:
    kind: str
    locator: str
    content_digest: str
    schema_version: str = EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_SCHEMA:
            raise TransitionPolicyError("unsupported admitted evidence schema")
        _nonempty("evidence.kind", self.kind)
        _nonempty("evidence.locator", self.locator)
        _digest("evidence.content_digest", self.content_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class TransitionRule:
    rule_id: str
    from_role: str
    from_state: str
    signal: TransitionSignal
    target_role: str
    target_state: str
    action_ref: str
    required_evidence: tuple[str, ...] = ()
    authority_required: bool = False
    authority_boundary: str | None = None
    schema_version: str = RULE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RULE_SCHEMA:
            raise TransitionPolicyError("unsupported transition rule schema")
        _nonempty("rule_id", self.rule_id)
        _nonempty("action_ref", self.action_ref)
        if self.from_role not in VALID_ROLES or self.target_role not in VALID_ROLES:
            raise TransitionPolicyError("unsupported transition role")
        if self.from_state not in VALID_STATES or self.target_state not in VALID_STATES:
            raise TransitionPolicyError("unsupported transition state")
        if not _role_state_valid(self.from_role, self.from_state):
            raise TransitionPolicyError("invalid source role/state combination")
        if not _role_state_valid(self.target_role, self.target_state):
            raise TransitionPolicyError("invalid target role/state combination")
        if self.signal not in VALID_SIGNALS:
            raise TransitionPolicyError("unsupported transition signal")

        _unique_nonempty("required_evidence", self.required_evidence)
        if self.signal in EVIDENCE_REQUIRED_SIGNALS and not self.required_evidence:
            raise TransitionPolicyError(
                f"{self.signal} transition requires explicit evidence kinds"
            )

        if not isinstance(self.authority_required, bool):
            raise TransitionPolicyError("authority_required must be boolean")
        _optional_nonempty("authority_boundary", self.authority_boundary)
        if self.authority_required and not self.authority_boundary:
            raise TransitionPolicyError(
                "authority-required transition must name authority_boundary"
            )
        if self.target_state == "human_gate" and not self.authority_boundary:
            raise TransitionPolicyError(
                "human_gate transition must name authority_boundary"
            )

    @property
    def match_key(self) -> tuple[str, str, str]:
        return (self.from_role, self.from_state, self.signal)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class TransitionPolicy:
    policy_id: str
    policy_revision: str
    rules: tuple[TransitionRule, ...]
    schema_version: str = POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != POLICY_SCHEMA:
            raise TransitionPolicyError("unsupported transition policy schema")
        _nonempty("policy_id", self.policy_id)
        _nonempty("policy_revision", self.policy_revision)
        if not self.rules:
            raise TransitionPolicyError("transition policy must contain at least one rule")

        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise TransitionPolicyError("transition rule ids must be unique")
        if rule_ids != tuple(sorted(rule_ids)):
            raise TransitionPolicyError(
                "transition rules must be sorted by rule_id for canonical policy"
            )

        keys = tuple(rule.match_key for rule in self.rules)
        if len(keys) != len(set(keys)):
            raise TransitionPolicyError(
                "transition policy cannot contain ambiguous match keys"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    work_id: str
    entry_digest: str
    from_role: str
    from_state: str
    signal: TransitionSignal
    admitted_evidence: tuple[AdmittedEvidence, ...] = ()
    authority_ref: str | None = None
    schema_version: str = REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA:
            raise TransitionPolicyError("unsupported transition request schema")
        _nonempty("work_id", self.work_id)
        _digest("entry_digest", self.entry_digest)
        if self.from_role not in VALID_ROLES:
            raise TransitionPolicyError("unsupported request role")
        if self.from_state not in VALID_STATES:
            raise TransitionPolicyError("unsupported request state")
        if not _role_state_valid(self.from_role, self.from_state):
            raise TransitionPolicyError("invalid request role/state combination")
        if self.signal not in VALID_SIGNALS:
            raise TransitionPolicyError("unsupported transition signal")
        _optional_nonempty("authority_ref", self.authority_ref)
        if self.authority_ref is not None:
            _digest("authority_ref", self.authority_ref)

        evidence_kinds = tuple(item.kind for item in self.admitted_evidence)
        if len(evidence_kinds) != len(set(evidence_kinds)):
            raise TransitionPolicyError(
                "admitted evidence kinds must be unique per transition request"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    policy_id: str
    policy_digest: str
    rule_id: str
    rule_digest: str
    request_digest: str
    work_id: str
    entry_digest: str
    signal: str
    from_role: str
    from_state: str
    target_role: str
    target_state: str
    action_ref: str
    evidence_digests: tuple[str, ...]
    authority_ref: str | None
    authority_boundary: str | None
    schema_version: str = DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DECISION_SCHEMA:
            raise TransitionPolicyError("unsupported transition decision schema")
        for name in ("policy_id", "rule_id", "work_id", "signal", "action_ref"):
            _nonempty(name, getattr(self, name))
        for name in (
            "policy_digest",
            "rule_digest",
            "request_digest",
            "entry_digest",
        ):
            _digest(name, getattr(self, name))
        if self.from_role not in VALID_ROLES or self.target_role not in VALID_ROLES:
            raise TransitionPolicyError("unsupported decision role")
        if self.from_state not in VALID_STATES or self.target_state not in VALID_STATES:
            raise TransitionPolicyError("unsupported decision state")
        if not _role_state_valid(self.from_role, self.from_state):
            raise TransitionPolicyError("invalid decision source role/state")
        if not _role_state_valid(self.target_role, self.target_state):
            raise TransitionPolicyError("invalid decision target role/state")
        if self.signal not in VALID_SIGNALS:
            raise TransitionPolicyError("unsupported decision signal")
        for digest in self.evidence_digests:
            _digest("evidence_digest", digest)
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise TransitionPolicyError("evidence_digests must not contain duplicates")
        _optional_nonempty("authority_ref", self.authority_ref)
        if self.authority_ref is not None:
            _digest("authority_ref", self.authority_ref)
        _optional_nonempty("authority_boundary", self.authority_boundary)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def evaluate_transition(
    policy: TransitionPolicy,
    request: TransitionRequest,
) -> TransitionDecision:
    matches = [rule for rule in policy.rules if rule.match_key == (
        request.from_role,
        request.from_state,
        request.signal,
    )]
    if len(matches) != 1:
        raise TransitionPolicyError("no unique admissible transition rule")
    rule = matches[0]

    by_kind = {item.kind: item for item in request.admitted_evidence}
    missing = tuple(kind for kind in rule.required_evidence if kind not in by_kind)
    if missing:
        raise TransitionPolicyError(
            f"transition evidence requirements unsatisfied: {missing}"
        )

    if rule.authority_required and request.authority_ref is None:
        raise TransitionPolicyError(
            f"transition requires admitted authority reference for {rule.authority_boundary}"
        )

    used_evidence = tuple(by_kind[kind].digest for kind in rule.required_evidence)
    return TransitionDecision(
        policy_id=policy.policy_id,
        policy_digest=policy.digest,
        rule_id=rule.rule_id,
        rule_digest=rule.digest,
        request_digest=request.digest,
        work_id=request.work_id,
        entry_digest=request.entry_digest,
        signal=request.signal,
        from_role=request.from_role,
        from_state=request.from_state,
        target_role=rule.target_role,
        target_state=rule.target_state,
        action_ref=rule.action_ref,
        evidence_digests=used_evidence,
        authority_ref=request.authority_ref if rule.authority_required else None,
        authority_boundary=rule.authority_boundary,
    )


def transition_policy_to_dict(policy: TransitionPolicy) -> dict[str, Any]:
    return json.loads(canonical_json(policy))


def transition_request_to_dict(request: TransitionRequest) -> dict[str, Any]:
    return json.loads(canonical_json(request))


def transition_decision_to_dict(decision: TransitionDecision) -> dict[str, Any]:
    return json.loads(canonical_json(decision))


def serialize_transition_policy(policy: TransitionPolicy) -> str:
    return canonical_json(policy)


def serialize_transition_request(request: TransitionRequest) -> str:
    return canonical_json(request)


def serialize_transition_decision(decision: TransitionDecision) -> str:
    return canonical_json(decision)


def _evidence_from_dict(data: Any) -> AdmittedEvidence:
    obj = _require_exact_fields(
        data,
        {"kind", "locator", "content_digest", "schema_version"},
        "admitted evidence",
    )
    return AdmittedEvidence(
        kind=obj["kind"],
        locator=obj["locator"],
        content_digest=obj["content_digest"],
        schema_version=obj["schema_version"],
    )


def _rule_from_dict(data: Any) -> TransitionRule:
    obj = _require_exact_fields(
        data,
        {
            "rule_id",
            "from_role",
            "from_state",
            "signal",
            "target_role",
            "target_state",
            "action_ref",
            "required_evidence",
            "authority_required",
            "authority_boundary",
            "schema_version",
        },
        "transition rule",
    )
    required = obj["required_evidence"]
    if not isinstance(required, list):
        raise TransitionPolicyError("required_evidence must be a list")
    return TransitionRule(
        rule_id=obj["rule_id"],
        from_role=obj["from_role"],
        from_state=obj["from_state"],
        signal=obj["signal"],
        target_role=obj["target_role"],
        target_state=obj["target_state"],
        action_ref=obj["action_ref"],
        required_evidence=tuple(required),
        authority_required=obj["authority_required"],
        authority_boundary=obj["authority_boundary"],
        schema_version=obj["schema_version"],
    )


def transition_policy_from_dict(data: Any) -> TransitionPolicy:
    obj = _require_exact_fields(
        data,
        {"policy_id", "policy_revision", "rules", "schema_version"},
        "transition policy",
    )
    rules = obj["rules"]
    if not isinstance(rules, list):
        raise TransitionPolicyError("transition policy rules must be a list")
    return TransitionPolicy(
        policy_id=obj["policy_id"],
        policy_revision=obj["policy_revision"],
        rules=tuple(_rule_from_dict(item) for item in rules),
        schema_version=obj["schema_version"],
    )


def transition_request_from_dict(data: Any) -> TransitionRequest:
    obj = _require_exact_fields(
        data,
        {
            "work_id",
            "entry_digest",
            "from_role",
            "from_state",
            "signal",
            "admitted_evidence",
            "authority_ref",
            "schema_version",
        },
        "transition request",
    )
    evidence = obj["admitted_evidence"]
    if not isinstance(evidence, list):
        raise TransitionPolicyError("admitted_evidence must be a list")
    return TransitionRequest(
        work_id=obj["work_id"],
        entry_digest=obj["entry_digest"],
        from_role=obj["from_role"],
        from_state=obj["from_state"],
        signal=obj["signal"],
        admitted_evidence=tuple(_evidence_from_dict(item) for item in evidence),
        authority_ref=obj["authority_ref"],
        schema_version=obj["schema_version"],
    )


def transition_decision_from_dict(data: Any) -> TransitionDecision:
    obj = _require_exact_fields(
        data,
        {
            "policy_id",
            "policy_digest",
            "rule_id",
            "rule_digest",
            "request_digest",
            "work_id",
            "entry_digest",
            "signal",
            "from_role",
            "from_state",
            "target_role",
            "target_state",
            "action_ref",
            "evidence_digests",
            "authority_ref",
            "authority_boundary",
            "schema_version",
        },
        "transition decision",
    )
    evidence_digests = obj["evidence_digests"]
    if not isinstance(evidence_digests, list):
        raise TransitionPolicyError("evidence_digests must be a list")
    return TransitionDecision(
        policy_id=obj["policy_id"],
        policy_digest=obj["policy_digest"],
        rule_id=obj["rule_id"],
        rule_digest=obj["rule_digest"],
        request_digest=obj["request_digest"],
        work_id=obj["work_id"],
        entry_digest=obj["entry_digest"],
        signal=obj["signal"],
        from_role=obj["from_role"],
        from_state=obj["from_state"],
        target_role=obj["target_role"],
        target_state=obj["target_state"],
        action_ref=obj["action_ref"],
        evidence_digests=tuple(evidence_digests),
        authority_ref=obj["authority_ref"],
        authority_boundary=obj["authority_boundary"],
        schema_version=obj["schema_version"],
    )


def deserialize_transition_policy(payload: str) -> TransitionPolicy:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise TransitionPolicyError("transition policy is not valid JSON") from exc
    return transition_policy_from_dict(data)


def deserialize_transition_request(payload: str) -> TransitionRequest:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise TransitionPolicyError("transition request is not valid JSON") from exc
    return transition_request_from_dict(data)


def deserialize_transition_decision(payload: str) -> TransitionDecision:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise TransitionPolicyError("transition decision is not valid JSON") from exc
    return transition_decision_from_dict(data)
