from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest, stable_id

RETRY_POLICY_SCHEMA = "ge.retry-policy.v1"
FAILURE_OBSERVATION_SCHEMA = "ge.failure-observation.v1"
RETRY_DECISION_SCHEMA = "ge.retry-decision.v1"

FailureClass = Literal[
    "network_timeout",
    "provider_throttled",
    "deterministic_assertion",
    "unknown_failure",
    "cost_boundary",
    "security_boundary",
    "authority_boundary",
]
RetryDisposition = Literal[
    "retry",
    "independent_reproduction",
    "diagnose",
    "human_gate",
    "stop",
]

VALID_FAILURE_CLASSES = {
    "network_timeout",
    "provider_throttled",
    "deterministic_assertion",
    "unknown_failure",
    "cost_boundary",
    "security_boundary",
    "authority_boundary",
}
HUMAN_BOUNDARY_FAILURE_CLASSES = {"security_boundary", "authority_boundary"}
VALID_DISPOSITIONS = {
    "retry",
    "independent_reproduction",
    "diagnose",
    "human_gate",
    "stop",
}


class RetryAuthorityError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RetryAuthorityError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise RetryAuthorityError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise RetryAuthorityError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _nonnegative_int(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RetryAuthorityError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    policy_id: str
    revision: str
    authority_ref: str
    authority_digest: str
    network_retry_limit: int = 2
    throttle_retry_limit: int = 3
    throttle_initial_backoff_seconds: int = 5
    throttle_max_backoff_seconds: int = 60
    unknown_reproduction_limit: int = 1
    schema_version: str = RETRY_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RETRY_POLICY_SCHEMA:
            raise RetryAuthorityError("unsupported retry policy schema")
        _nonempty("policy_id", self.policy_id)
        _nonempty("revision", self.revision)
        _nonempty("authority_ref", self.authority_ref)
        _digest("authority_digest", self.authority_digest)
        for name in (
            "network_retry_limit",
            "throttle_retry_limit",
            "throttle_initial_backoff_seconds",
            "throttle_max_backoff_seconds",
            "unknown_reproduction_limit",
        ):
            _nonnegative_int(name, getattr(self, name))
        if self.throttle_initial_backoff_seconds < 1:
            raise RetryAuthorityError(
                "throttle_initial_backoff_seconds must be >= 1"
            )
        if self.throttle_max_backoff_seconds < self.throttle_initial_backoff_seconds:
            raise RetryAuthorityError(
                "throttle_max_backoff_seconds must be >= initial backoff"
            )
        if self.unknown_reproduction_limit != 1:
            raise RetryAuthorityError(
                "unknown_reproduction_limit is frozen to exactly 1"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class FailureObservation:
    failure_class: FailureClass
    failure_code: str
    evidence_digest: str
    automatic_retry_count: int = 0
    independent_reproduction_count: int = 0
    boundary_detail: str | None = None
    schema_version: str = FAILURE_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != FAILURE_OBSERVATION_SCHEMA:
            raise RetryAuthorityError("unsupported failure observation schema")
        if self.failure_class not in VALID_FAILURE_CLASSES:
            raise RetryAuthorityError("unsupported failure class")
        _nonempty("failure_code", self.failure_code)
        _digest("evidence_digest", self.evidence_digest)
        _nonnegative_int("automatic_retry_count", self.automatic_retry_count)
        _nonnegative_int(
            "independent_reproduction_count",
            self.independent_reproduction_count,
        )
        _optional_nonempty("boundary_detail", self.boundary_detail)

        if self.failure_class in HUMAN_BOUNDARY_FAILURE_CLASSES:
            if self.boundary_detail is None:
                raise RetryAuthorityError(
                    "human boundary failure requires boundary_detail"
                )
        elif self.failure_class == "cost_boundary":
            if self.boundary_detail is None:
                raise RetryAuthorityError(
                    "cost boundary requires boundary_detail"
                )
        elif self.boundary_detail is not None:
            raise RetryAuthorityError(
                "boundary_detail is valid only for boundary failures"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RetryDecision:
    policy_digest: str
    observation_digest: str
    disposition: RetryDisposition
    next_action_ref: str
    delay_seconds: int = 0
    automatic_retry_authorized: bool = False
    independent_reproduction_authorized: bool = False
    human_required: bool = False
    authority_ref: str | None = None
    authority_digest: str | None = None
    authority_boundary: str | None = None
    transport_authority: bool = False
    schema_version: str = RETRY_DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RETRY_DECISION_SCHEMA:
            raise RetryAuthorityError("unsupported retry decision schema")
        _digest("policy_digest", self.policy_digest)
        _digest("observation_digest", self.observation_digest)
        if self.disposition not in VALID_DISPOSITIONS:
            raise RetryAuthorityError("unsupported retry disposition")
        _nonempty("next_action_ref", self.next_action_ref)
        _nonnegative_int("delay_seconds", self.delay_seconds)
        _optional_nonempty("authority_ref", self.authority_ref)
        if self.authority_digest is not None:
            _digest("authority_digest", self.authority_digest)
        _optional_nonempty("authority_boundary", self.authority_boundary)

        if self.transport_authority:
            raise RetryAuthorityError(
                "retry decision cannot grant transport authority"
            )

        if self.disposition == "retry":
            if not self.automatic_retry_authorized:
                raise RetryAuthorityError(
                    "retry disposition requires automatic_retry_authorized"
                )
            if self.independent_reproduction_authorized or self.human_required:
                raise RetryAuthorityError("retry disposition flags are inconsistent")
            if (
                self.authority_ref is None
                or self.authority_digest is None
                or self.authority_boundary is not None
            ):
                raise RetryAuthorityError(
                    "retry disposition requires bounded authority artifact only"
                )

        elif self.disposition == "independent_reproduction":
            if not self.independent_reproduction_authorized:
                raise RetryAuthorityError(
                    "independent reproduction requires explicit authorization"
                )
            if self.automatic_retry_authorized or self.human_required:
                raise RetryAuthorityError(
                    "independent reproduction flags are inconsistent"
                )
            if (
                self.delay_seconds != 0
                or self.authority_ref is None
                or self.authority_digest is None
                or self.authority_boundary is not None
            ):
                raise RetryAuthorityError(
                    "independent reproduction requires bounded authority artifact"
                )

        elif self.disposition in {"diagnose", "stop"}:
            if (
                self.automatic_retry_authorized
                or self.independent_reproduction_authorized
                or self.human_required
            ):
                raise RetryAuthorityError(
                    f"{self.disposition} disposition cannot grant authority"
                )
            if (
                self.delay_seconds != 0
                or self.authority_ref is not None
                or self.authority_digest is not None
                or self.authority_boundary is not None
            ):
                raise RetryAuthorityError(
                    f"{self.disposition} disposition cannot carry authority or delay"
                )

        elif self.disposition == "human_gate":
            if not self.human_required or self.authority_boundary is None:
                raise RetryAuthorityError(
                    "human_gate disposition requires human authority boundary"
                )
            if (
                self.automatic_retry_authorized
                or self.independent_reproduction_authorized
                or self.delay_seconds != 0
                or self.authority_ref is not None
                or self.authority_digest is not None
            ):
                raise RetryAuthorityError(
                    "human_gate disposition flags are inconsistent"
                )

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def decision_id(self) -> str:
        return stable_id("gerd", self)


def _decision(
    policy: RetryPolicy,
    observation: FailureObservation,
    *,
    disposition: RetryDisposition,
    next_action_ref: str,
    delay_seconds: int = 0,
    automatic_retry_authorized: bool = False,
    independent_reproduction_authorized: bool = False,
    human_required: bool = False,
    authority_boundary: str | None = None,
) -> RetryDecision:
    mechanical = automatic_retry_authorized or independent_reproduction_authorized
    return RetryDecision(
        policy_digest=policy.digest,
        observation_digest=observation.digest,
        disposition=disposition,
        next_action_ref=next_action_ref,
        delay_seconds=delay_seconds,
        automatic_retry_authorized=automatic_retry_authorized,
        independent_reproduction_authorized=independent_reproduction_authorized,
        human_required=human_required,
        authority_ref=policy.authority_ref if mechanical else None,
        authority_digest=policy.authority_digest if mechanical else None,
        authority_boundary=authority_boundary,
    )


def decide_retry(
    policy: RetryPolicy,
    observation: FailureObservation,
) -> RetryDecision:
    failure_class = observation.failure_class

    if failure_class == "network_timeout":
        if observation.automatic_retry_count < policy.network_retry_limit:
            return _decision(
                policy,
                observation,
                disposition="retry",
                next_action_ref="retry://network-timeout",
                automatic_retry_authorized=True,
            )
        return _decision(
            policy,
            observation,
            disposition="diagnose",
            next_action_ref="diagnose://network-retry-budget-exhausted",
        )

    if failure_class == "provider_throttled":
        if observation.automatic_retry_count < policy.throttle_retry_limit:
            delay = min(
                policy.throttle_initial_backoff_seconds
                * (2 ** observation.automatic_retry_count),
                policy.throttle_max_backoff_seconds,
            )
            return _decision(
                policy,
                observation,
                disposition="retry",
                next_action_ref="retry://provider-throttled",
                delay_seconds=delay,
                automatic_retry_authorized=True,
            )
        return _decision(
            policy,
            observation,
            disposition="diagnose",
            next_action_ref="diagnose://throttle-retry-budget-exhausted",
        )

    if failure_class == "deterministic_assertion":
        return _decision(
            policy,
            observation,
            disposition="diagnose",
            next_action_ref="diagnose://deterministic-assertion",
        )

    if failure_class == "unknown_failure":
        if (
            observation.independent_reproduction_count
            < policy.unknown_reproduction_limit
        ):
            return _decision(
                policy,
                observation,
                disposition="independent_reproduction",
                next_action_ref="reproduce://unknown-failure",
                independent_reproduction_authorized=True,
            )
        return _decision(
            policy,
            observation,
            disposition="diagnose",
            next_action_ref="diagnose://unknown-failure",
        )

    if failure_class == "cost_boundary":
        return _decision(
            policy,
            observation,
            disposition="stop",
            next_action_ref="stop://cost-boundary",
        )

    if failure_class in HUMAN_BOUNDARY_FAILURE_CLASSES:
        return _decision(
            policy,
            observation,
            disposition="human_gate",
            next_action_ref="authority://human-decision",
            human_required=True,
            authority_boundary=observation.boundary_detail,
        )

    raise RetryAuthorityError("failure class has no fail-closed disposition")
