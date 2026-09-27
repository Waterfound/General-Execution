"""Persistent short-lived runtime admission for Durable Execution.

The module is deliberately provider-neutral and command-free. A host may admit:
- bootstrap: initialize exactly one generation-zero PortfolioState; or
- transition: consume exactly one already-authenticated ExternalTriggerEvidence.

It never executes arbitrary commands, grants authority, merges code, or creates
provider triggers. Persistence transport (Git, object storage, etc.) stays outside.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .asp_transition import PassiveWakeAdmission, TransitionAuthorityGrant
from .canonical import sha256_digest
from .core_rehearsal import CoreRehearsalReport
from .execution_checkpoint import CheckpointEvidence
from .external_trigger import ExternalTriggerEvidence, TriggerContract, consume_external_trigger
from .portfolio_persistence import SqlitePortfolioHeadStore, recover_portfolio_after_restart
from .portfolio_state import PortfolioState, portfolio_state_from_dict
from .resume_tick import (
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    ResumeTickObservation,
)
from .transition_policy import TransitionPolicy, transition_policy_from_dict

PERSISTENT_EVENT_SCHEMA = "ge.persistent-runtime-event.v1"
PERSISTENT_REPORT_SCHEMA = "ge.persistent-runtime-event-report.v1"

PersistentOperation = Literal["bootstrap", "transition"]


class PersistentRuntimeError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PersistentRuntimeError(f"{name} must be a non-empty string")


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PersistentRuntimeError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise PersistentRuntimeError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


def _authority_grant(data: Any) -> TransitionAuthorityGrant | None:
    if data is None:
        return None
    obj = _exact(
        data,
        {
            "policy_digest",
            "rule_digest",
            "authority_boundary",
            "authority_ref",
            "authority_digest",
            "schema_version",
        },
        "authority_grant",
    )
    return TransitionAuthorityGrant(**obj)


def _checkpoint_evidence(data: Any) -> CheckpointEvidence:
    obj = _exact(data, {"kind", "locator", "digest", "schema_version"}, "evidence")
    return CheckpointEvidence(**obj)


def _wake_admission(data: Any) -> PassiveWakeAdmission | None:
    if data is None:
        return None
    obj = _exact(
        data,
        {
            "portfolio_id",
            "portfolio_generation",
            "portfolio_state_digest",
            "work_id",
            "wake_condition_digest",
            "policy_digest",
            "rule_digest",
            "evidence",
            "next_action_ref",
            "authority_grant",
            "schema_version",
        },
        "wake_admission",
    )
    if not isinstance(obj["evidence"], list):
        raise PersistentRuntimeError("wake_admission.evidence must be a list")
    return PassiveWakeAdmission(
        portfolio_id=obj["portfolio_id"],
        portfolio_generation=obj["portfolio_generation"],
        portfolio_state_digest=obj["portfolio_state_digest"],
        work_id=obj["work_id"],
        wake_condition_digest=obj["wake_condition_digest"],
        policy_digest=obj["policy_digest"],
        rule_digest=obj["rule_digest"],
        evidence=tuple(_checkpoint_evidence(item) for item in obj["evidence"]),
        next_action_ref=obj["next_action_ref"],
        authority_grant=_authority_grant(obj["authority_grant"]),
        schema_version=obj["schema_version"],
    )


def _observation(data: Any) -> ResumeTickObservation:
    obj = _exact(
        data,
        {
            "portfolio_id",
            "expected_generation",
            "expected_state_digest",
            "policy_digest",
            "event",
            "evidence",
            "action_ref",
            "observed_at",
            "summary",
            "canonical_refs",
            "uncertainties",
            "wake_admission",
            "authority_grant",
            "schema_version",
        },
        "observation",
    )
    if not isinstance(obj["evidence"], list):
        raise PersistentRuntimeError("observation.evidence must be a list")
    if not isinstance(obj["canonical_refs"], list):
        raise PersistentRuntimeError("observation.canonical_refs must be a list")
    if not isinstance(obj["uncertainties"], list):
        raise PersistentRuntimeError("observation.uncertainties must be a list")
    return ResumeTickObservation(
        portfolio_id=obj["portfolio_id"],
        expected_generation=obj["expected_generation"],
        expected_state_digest=obj["expected_state_digest"],
        policy_digest=obj["policy_digest"],
        event=obj["event"],
        evidence=tuple(_checkpoint_evidence(item) for item in obj["evidence"]),
        action_ref=obj["action_ref"],
        observed_at=obj["observed_at"],
        summary=obj["summary"],
        canonical_refs=tuple(obj["canonical_refs"]),
        uncertainties=tuple(obj["uncertainties"]),
        wake_admission=_wake_admission(obj["wake_admission"]),
        authority_grant=_authority_grant(obj["authority_grant"]),
        schema_version=obj["schema_version"],
    )


def _trigger(data: Any) -> ExternalTriggerEvidence:
    obj = _exact(
        data,
        {
            "source",
            "event_id",
            "event_kind",
            "payload_digest",
            "observation_digest",
            "admission_ref",
        },
        "trigger",
    )
    return ExternalTriggerEvidence(**obj)


def _contract(data: Any) -> TriggerContract:
    obj = _exact(
        data,
        {
            "source",
            "event_kind",
            "portfolio_id",
            "policy_digest",
            "transition_event",
        },
        "contract",
    )
    return TriggerContract(**obj)


@dataclass(frozen=True, slots=True)
class PersistentRuntimeEventReport:
    event_id: str
    operation: PersistentOperation
    status: str
    portfolio_id: str
    pre_generation: int
    post_generation: int
    pre_state_digest: str
    post_state_digest: str
    checkpoint_digest: str | None
    human_required: bool
    requested_action_ref: str | None
    schema_version: str = PERSISTENT_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERSISTENT_REPORT_SCHEMA:
            raise PersistentRuntimeError("unsupported persistent report schema")
        _nonempty("event_id", self.event_id)
        _nonempty("portfolio_id", self.portfolio_id)
        if self.operation not in {"bootstrap", "transition"}:
            raise PersistentRuntimeError("unsupported persistent operation")
        _nonempty("status", self.status)
        for value in (self.pre_generation, self.post_generation):
            if type(value) is not int or value < 0:
                raise PersistentRuntimeError("report generations must be non-negative integers")
        for name in ("pre_state_digest", "post_state_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:"):
                raise PersistentRuntimeError(f"{name} must be a digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def trigger_digest_from_event(payload: dict[str, Any]) -> str | None:
    """Return exact trigger digest for host admission after it authenticates transport."""
    obj = _exact(
        payload,
        {"schema_version", "event_id", "operation", "body"},
        "persistent event",
    )
    if obj["schema_version"] != PERSISTENT_EVENT_SCHEMA:
        raise PersistentRuntimeError("unsupported persistent event schema")
    if obj["operation"] == "bootstrap":
        return None
    if obj["operation"] != "transition":
        raise PersistentRuntimeError("unsupported persistent operation")
    body = _exact(
        obj["body"],
        {"policy", "contract", "trigger", "observation"},
        "transition body",
    )
    trigger = _trigger(body["trigger"])
    if trigger.event_id != obj["event_id"]:
        raise PersistentRuntimeError("event_id does not bind trigger")
    return trigger.digest


def process_persistent_runtime_event(
    database: str | Path,
    payload: dict[str, Any],
    *,
    authenticated_trigger_digest: str | None = None,
    core_requirement: CoreVerificationRequirement | None = None,
    core_verification: CoreVerificationReceipt | None = None,
    core_report: CoreRehearsalReport | None = None,
) -> PersistentRuntimeEventReport:
    obj = _exact(
        payload,
        {"schema_version", "event_id", "operation", "body"},
        "persistent event",
    )
    if obj["schema_version"] != PERSISTENT_EVENT_SCHEMA:
        raise PersistentRuntimeError("unsupported persistent event schema")
    _nonempty("event_id", obj["event_id"])
    operation = obj["operation"]
    if operation not in {"bootstrap", "transition"}:
        raise PersistentRuntimeError("unsupported persistent operation")

    store = SqlitePortfolioHeadStore(database)

    if operation == "bootstrap":
        if authenticated_trigger_digest is not None:
            raise PersistentRuntimeError("bootstrap cannot carry trigger admission")
        body = _exact(obj["body"], {"portfolio"}, "bootstrap body")
        state = portfolio_state_from_dict(body["portfolio"])
        if state.generation != 0 or state.previous_state_digest is not None:
            raise PersistentRuntimeError("bootstrap requires a generation-zero portfolio")
        head = store.initialize(state)
        recovered, checkpoint, _ = recover_portfolio_after_restart(
            store, state.portfolio_id
        )
        if checkpoint is not None:
            raise PersistentRuntimeError("bootstrap cannot fabricate a checkpoint")
        return PersistentRuntimeEventReport(
            event_id=obj["event_id"],
            operation="bootstrap",
            status="bootstrapped",
            portfolio_id=recovered.portfolio_id,
            pre_generation=0,
            post_generation=head.generation,
            pre_state_digest=recovered.digest,
            post_state_digest=recovered.digest,
            checkpoint_digest=None,
            human_required=recovered.active.state == "human_gate",
            requested_action_ref=recovered.active.next_action_ref,
        )

    body = _exact(
        obj["body"],
        {"policy", "contract", "trigger", "observation"},
        "transition body",
    )
    if any(
        value is None
        for value in (
            authenticated_trigger_digest,
            core_requirement,
            core_verification,
            core_report,
        )
    ):
        raise PersistentRuntimeError(
            "transition requires authenticated trigger and canonical verification gates"
        )

    policy: TransitionPolicy = transition_policy_from_dict(body["policy"])
    contract = _contract(body["contract"])
    trigger = _trigger(body["trigger"])
    observation = _observation(body["observation"])

    if trigger.event_id != obj["event_id"]:
        raise PersistentRuntimeError("event_id does not bind trigger")
    if observation.authority_grant is not None:
        raise PersistentRuntimeError(
            "persistent transport cannot carry transition authority"
        )

    before, _, _ = recover_portfolio_after_restart(store, contract.portfolio_id)
    result = consume_external_trigger(
        database,
        contract,
        trigger,
        observation,
        policy,
        authenticated_admission_digest=authenticated_trigger_digest,
        core_requirement=core_requirement,
        core_verification=core_verification,
        core_report=core_report,
    )
    after, checkpoint, _ = recover_portfolio_after_restart(store, contract.portfolio_id)

    return PersistentRuntimeEventReport(
        event_id=obj["event_id"],
        operation="transition",
        status=result.disposition,
        portfolio_id=after.portfolio_id,
        pre_generation=before.generation,
        post_generation=after.generation,
        pre_state_digest=before.digest,
        post_state_digest=after.digest,
        checkpoint_digest=checkpoint.digest if checkpoint is not None else None,
        human_required=result.human_required,
        requested_action_ref=result.requested_action_ref,
    )
