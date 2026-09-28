from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id
from .execution_checkpoint import CheckpointEvidence
from .external_trigger import ExternalTriggerEvidence, TriggerContract
from .portfolio_state import PortfolioState
from .resume_tick import ResumeTickObservation
from .transition_policy import (
    TransitionPolicy,
    transition_policy_from_dict,
    transition_policy_to_dict,
)

PROVIDER_INPUT_SCHEMA = "ge.provider-input.v1"
PROVIDER_WATCH_CONTRACT_SCHEMA = "ge.provider-watch-contract.v1"
PROVIDER_HOST_RESULT_SCHEMA = "ge.provider-host-result.v1"

ProviderHostStatus = Literal["event_ready", "condition_not_satisfied"]


class ProviderHostError(ValueError):
    pass


class ProviderConditionNotSatisfied(ProviderHostError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProviderHostError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ProviderHostError(f"{name} must be sha256:<64-hex>")


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ProviderHostError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise ProviderHostError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


def _string_map(name: str, value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise ProviderHostError(f"{name} must be an object")
    pairs: list[tuple[str, str]] = []
    for key, item in value.items():
        _nonempty(f"{name}.key", key)
        _nonempty(f"{name}.{key}", item)
        pairs.append((key, item))
    return tuple(sorted(pairs))


def _string_list(name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ProviderHostError(f"{name} must be a list")
    result = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise ProviderHostError(f"{name} must contain non-empty strings")
    if len(result) != len(set(result)):
        raise ProviderHostError(f"{name} must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class ProviderInput:
    watch_id: str
    provider: str
    provider_event_id: str
    subject_ref: str
    observed_state: str
    observed_at: str
    evidence_locator: str
    evidence_digest: str
    bindings: tuple[tuple[str, str], ...]
    canonical_refs: tuple[str, ...]
    schema_version: str = PROVIDER_INPUT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_INPUT_SCHEMA:
            raise ProviderHostError("unsupported provider input schema")
        for name in (
            "watch_id",
            "provider",
            "provider_event_id",
            "subject_ref",
            "observed_state",
            "observed_at",
            "evidence_locator",
        ):
            _nonempty(name, getattr(self, name))
        _digest("evidence_digest", self.evidence_digest)
        if self.bindings != tuple(sorted(self.bindings)):
            raise ProviderHostError("bindings must be sorted")
        if len(self.bindings) != len({key for key, _ in self.bindings}):
            raise ProviderHostError("bindings keys must be unique")
        for key, value in self.bindings:
            _nonempty("binding key", key)
            _nonempty(f"binding {key}", value)
        if not self.canonical_refs:
            raise ProviderHostError("canonical_refs cannot be empty")
        if tuple(sorted(self.canonical_refs)) != self.canonical_refs:
            raise ProviderHostError("canonical_refs must be sorted")
        if len(self.canonical_refs) != len(set(self.canonical_refs)):
            raise ProviderHostError("canonical_refs must be unique")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderWatchContract:
    watch_id: str
    provider: str
    subject_ref: str
    satisfied_state: str
    portfolio_id: str
    transition_event: str
    evidence_kind: str
    contract_ref: str
    required_bindings: tuple[tuple[str, str], ...]
    policy: TransitionPolicy
    schema_version: str = PROVIDER_WATCH_CONTRACT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_WATCH_CONTRACT_SCHEMA:
            raise ProviderHostError("unsupported provider watch contract schema")
        for name in (
            "watch_id",
            "provider",
            "subject_ref",
            "satisfied_state",
            "portfolio_id",
            "transition_event",
            "evidence_kind",
            "contract_ref",
        ):
            _nonempty(name, getattr(self, name))
        if self.required_bindings != tuple(sorted(self.required_bindings)):
            raise ProviderHostError("required_bindings must be sorted")
        if len(self.required_bindings) != len({key for key, _ in self.required_bindings}):
            raise ProviderHostError("required_bindings keys must be unique")

        matches = [
            rule for rule in self.policy.rules
            if rule.event == self.transition_event
        ]
        if not matches:
            raise ProviderHostError("contract transition_event is absent from policy")
        for rule in self.policy.rules:
            if rule.from_state == "human_gate" or rule.authority_mode == "preauthorized_required":
                raise ProviderHostError(
                    "provider host contracts cannot resume human-gated work"
                )
            if rule.authority_mode not in {"none", "human_required"}:
                raise ProviderHostError("unsupported provider-host authority mode")
            if rule.authority_mode == "human_required" and rule.effect != "stop_human_gate":
                raise ProviderHostError("human-required provider rule must stop at human gate")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderHostResult:
    status: ProviderHostStatus
    provider_input_digest: str
    contract_digest: str
    portfolio_id: str
    portfolio_generation: int
    portfolio_state_digest: str
    event_id: str | None
    event_digest: str | None
    schema_version: str = PROVIDER_HOST_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_HOST_RESULT_SCHEMA:
            raise ProviderHostError("unsupported provider host result schema")
        if self.status not in {"event_ready", "condition_not_satisfied"}:
            raise ProviderHostError("unsupported provider host status")
        for name in (
            "provider_input_digest",
            "contract_digest",
            "portfolio_state_digest",
        ):
            _digest(name, getattr(self, name))
        _nonempty("portfolio_id", self.portfolio_id)
        if type(self.portfolio_generation) is not int or self.portfolio_generation < 0:
            raise ProviderHostError("portfolio_generation must be a non-negative integer")
        if self.status == "event_ready":
            _nonempty("event_id", self.event_id)
            _digest("event_digest", self.event_digest)
        elif self.event_id is not None or self.event_digest is not None:
            raise ProviderHostError("condition_not_satisfied cannot carry event identity")


def provider_input_from_dict(data: Any) -> ProviderInput:
    obj = _exact(
        data,
        {
            "watch_id",
            "provider",
            "provider_event_id",
            "subject_ref",
            "observed_state",
            "observed_at",
            "evidence_locator",
            "evidence_digest",
            "bindings",
            "canonical_refs",
            "schema_version",
        },
        "provider input",
    )
    return ProviderInput(
        watch_id=obj["watch_id"],
        provider=obj["provider"],
        provider_event_id=obj["provider_event_id"],
        subject_ref=obj["subject_ref"],
        observed_state=obj["observed_state"],
        observed_at=obj["observed_at"],
        evidence_locator=obj["evidence_locator"],
        evidence_digest=obj["evidence_digest"],
        bindings=_string_map("bindings", obj["bindings"]),
        canonical_refs=tuple(sorted(_string_list("canonical_refs", obj["canonical_refs"]))),
        schema_version=obj["schema_version"],
    )


def provider_watch_contract_from_dict(data: Any) -> ProviderWatchContract:
    obj = _exact(
        data,
        {
            "watch_id",
            "provider",
            "subject_ref",
            "satisfied_state",
            "portfolio_id",
            "transition_event",
            "evidence_kind",
            "contract_ref",
            "required_bindings",
            "policy",
            "schema_version",
        },
        "provider watch contract",
    )
    return ProviderWatchContract(
        watch_id=obj["watch_id"],
        provider=obj["provider"],
        subject_ref=obj["subject_ref"],
        satisfied_state=obj["satisfied_state"],
        portfolio_id=obj["portfolio_id"],
        transition_event=obj["transition_event"],
        evidence_kind=obj["evidence_kind"],
        contract_ref=obj["contract_ref"],
        required_bindings=_string_map("required_bindings", obj["required_bindings"]),
        policy=transition_policy_from_dict(obj["policy"]),
        schema_version=obj["schema_version"],
    )


def provider_input_to_dict(value: ProviderInput) -> dict[str, Any]:
    return {
        "watch_id": value.watch_id,
        "provider": value.provider,
        "provider_event_id": value.provider_event_id,
        "subject_ref": value.subject_ref,
        "observed_state": value.observed_state,
        "observed_at": value.observed_at,
        "evidence_locator": value.evidence_locator,
        "evidence_digest": value.evidence_digest,
        "bindings": dict(value.bindings),
        "canonical_refs": list(value.canonical_refs),
        "schema_version": value.schema_version,
    }


def provider_watch_contract_to_dict(value: ProviderWatchContract) -> dict[str, Any]:
    return {
        "watch_id": value.watch_id,
        "provider": value.provider,
        "subject_ref": value.subject_ref,
        "satisfied_state": value.satisfied_state,
        "portfolio_id": value.portfolio_id,
        "transition_event": value.transition_event,
        "evidence_kind": value.evidence_kind,
        "contract_ref": value.contract_ref,
        "required_bindings": dict(value.required_bindings),
        "policy": transition_policy_to_dict(value.policy),
        "schema_version": value.schema_version,
    }


def build_provider_runtime_event(
    state: PortfolioState,
    contract: ProviderWatchContract,
    provider_input: ProviderInput,
) -> tuple[dict[str, Any] | None, ProviderHostResult]:
    if state.portfolio_id != contract.portfolio_id:
        raise ProviderHostError("portfolio id does not match provider contract")
    if provider_input.watch_id != contract.watch_id:
        raise ProviderHostError("watch_id mismatch")
    if provider_input.provider != contract.provider:
        raise ProviderHostError("provider mismatch")
    if provider_input.subject_ref != contract.subject_ref:
        raise ProviderHostError("subject_ref mismatch")
    if provider_input.bindings != contract.required_bindings:
        raise ProviderHostError("provider binding mismatch")

    if provider_input.observed_state != contract.satisfied_state:
        return None, ProviderHostResult(
            status="condition_not_satisfied",
            provider_input_digest=provider_input.digest,
            contract_digest=contract.digest,
            portfolio_id=state.portfolio_id,
            portfolio_generation=state.generation,
            portfolio_state_digest=state.digest,
            event_id=None,
            event_digest=None,
        )

    matching = [
        rule
        for rule in contract.policy.rules
        if rule.from_state == state.active.state and rule.event == contract.transition_event
    ]
    if len(matching) != 1:
        raise ProviderHostError(
            "provider contract has no unique rule for the current active state"
        )
    rule = matching[0]
    if rule.from_state == "human_gate" or rule.authority_mode == "preauthorized_required":
        raise ProviderHostError("provider host cannot cross a human authority gate")
    if contract.evidence_kind not in rule.required_evidence:
        raise ProviderHostError("provider evidence kind is not required by matched rule")

    evidence = CheckpointEvidence(
        kind=contract.evidence_kind,
        locator=provider_input.evidence_locator,
        digest=provider_input.evidence_digest,
    )
    canonical_refs = tuple(
        sorted(
            set(
                provider_input.canonical_refs
                + (contract.contract_ref, provider_input.subject_ref)
            )
        )
    )
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=contract.policy.digest,
        event=contract.transition_event,
        evidence=(evidence,),
        action_ref=provider_input.subject_ref,
        observed_at=provider_input.observed_at,
        summary=(
            f"Provider watch {contract.watch_id} observed "
            f"{provider_input.subject_ref} state={provider_input.observed_state}."
        ),
        canonical_refs=canonical_refs,
        uncertainties=(),
    )
    source = f"provider-host:{contract.provider}"
    event_kind = f"{contract.watch_id}:{contract.satisfied_state}"
    event_id = stable_id(
        "geph",
        {
            "provider_input_digest": provider_input.digest,
            "contract_digest": contract.digest,
            "generation": state.generation,
            "state_digest": state.digest,
        },
    )
    trigger = ExternalTriggerEvidence(
        source=source,
        event_id=event_id,
        event_kind=event_kind,
        payload_digest=provider_input.digest,
        observation_digest=observation.digest,
        admission_ref=provider_input.evidence_locator,
    )
    trigger_contract = TriggerContract(
        source=source,
        event_kind=event_kind,
        portfolio_id=state.portfolio_id,
        policy_digest=contract.policy.digest,
        transition_event=contract.transition_event,
    )
    event = {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": event_id,
        "operation": "transition",
        "body": {
            "policy": transition_policy_to_dict(contract.policy),
            "contract": {
                "source": trigger_contract.source,
                "event_kind": trigger_contract.event_kind,
                "portfolio_id": trigger_contract.portfolio_id,
                "policy_digest": trigger_contract.policy_digest,
                "transition_event": trigger_contract.transition_event,
            },
            "trigger": {
                "source": trigger.source,
                "event_id": trigger.event_id,
                "event_kind": trigger.event_kind,
                "payload_digest": trigger.payload_digest,
                "observation_digest": trigger.observation_digest,
                "admission_ref": trigger.admission_ref,
            },
            "observation": json.loads(canonical_json(observation)),
        },
    }
    event = json.loads(canonical_json(event))
    return event, ProviderHostResult(
        status="event_ready",
        provider_input_digest=provider_input.digest,
        contract_digest=contract.digest,
        portfolio_id=state.portfolio_id,
        portfolio_generation=state.generation,
        portfolio_state_digest=state.digest,
        event_id=event_id,
        event_digest=sha256_digest(event),
    )
