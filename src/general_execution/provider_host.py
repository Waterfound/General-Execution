"""Fail-closed provider wake host for Durable Execution.

This module closes the transport gap between an external provider observer and
the existing persistent runtime. A provider snapshot carries facts only. It
cannot choose a transition policy, grant authority, or resume a human gate.

Trusted ProviderWatch configuration is source-controlled separately from the
snapshot. The host recovers the current durable portfolio, binds the snapshot
to that exact generation/state digest, and emits one deterministic persistent
runtime event for the existing runtime workflow.

No provider credentials, network clients, command execution, or repository
writes live in this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import re

from .canonical import canonical_json, sha256_digest, stable_id
from .execution_checkpoint import CheckpointEvidence
from .external_trigger import ExternalTriggerEvidence, TriggerContract
from .portfolio_persistence import SqlitePortfolioHeadStore, recover_portfolio_after_restart
from .resume_tick import ResumeTickObservation
from .transition_policy import (
    TransitionPolicy,
    match_transition_rule,
    transition_policy_from_dict,
    transition_policy_to_dict,
)

PROVIDER_SNAPSHOT_SCHEMA = "ge.provider-snapshot.v1"
PROVIDER_WATCH_SCHEMA = "ge.provider-watch.v1"
PERSISTENT_EVENT_SCHEMA = "ge.persistent-runtime-event.v1"


class ProviderHostError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProviderHostError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ProviderHostError(f"{name} must be sha256:<64-hex>")


def _unique_nonempty(name: str, values: tuple[str, ...]) -> None:
    if not values:
        raise ProviderHostError(f"{name} must not be empty")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ProviderHostError(f"{name} must contain only non-empty strings")
    if len(values) != len(set(values)):
        raise ProviderHostError(f"{name} must not contain duplicates")


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


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    watch_id: str
    provider: str
    resource_id: str
    provider_event_id: str
    observed_state: str
    observed_at: str
    evidence_locator: str
    metadata_digest: str
    canonical_refs: tuple[str, ...]
    schema_version: str = PROVIDER_SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_SNAPSHOT_SCHEMA:
            raise ProviderHostError("unsupported provider snapshot schema")
        for name in (
            "watch_id",
            "provider",
            "resource_id",
            "provider_event_id",
            "observed_state",
            "observed_at",
            "evidence_locator",
        ):
            _nonempty(name, getattr(self, name))
        _digest("metadata_digest", self.metadata_digest)
        _unique_nonempty("canonical_refs", self.canonical_refs)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def event_identity(self) -> str:
        return stable_id(
            "provider",
            {
                "watch_id": self.watch_id,
                "provider": self.provider,
                "resource_id": self.resource_id,
                "provider_event_id": self.provider_event_id,
                "observed_state": self.observed_state,
                "snapshot_digest": self.digest,
            },
        )


@dataclass(frozen=True, slots=True)
class ProviderWatch:
    watch_id: str
    provider: str
    resource_id: str
    matched_state: str
    portfolio_id: str
    transition_event: str
    evidence_kind: str
    action_ref: str
    summary: str
    canonical_refs: tuple[str, ...]
    uncertainties: tuple[str, ...]
    policy: TransitionPolicy
    schema_version: str = PROVIDER_WATCH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_WATCH_SCHEMA:
            raise ProviderHostError("unsupported provider watch schema")
        for name in (
            "watch_id",
            "provider",
            "resource_id",
            "matched_state",
            "portfolio_id",
            "transition_event",
            "evidence_kind",
            "action_ref",
            "summary",
        ):
            _nonempty(name, getattr(self, name))
        _unique_nonempty("canonical_refs", self.canonical_refs)
        if any(not isinstance(value, str) or not value.strip() for value in self.uncertainties):
            raise ProviderHostError("uncertainties must contain only non-empty strings")
        if len(self.uncertainties) != len(set(self.uncertainties)):
            raise ProviderHostError("uncertainties must not contain duplicates")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderHostResult:
    matched: bool
    snapshot_digest: str
    watch_digest: str
    event_id: str | None
    event_digest: str | None
    reason: str
    event: dict[str, Any] | None
    schema_version: str = "ge.provider-host-result.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def provider_snapshot_from_dict(data: Any) -> ProviderSnapshot:
    obj = _exact(
        data,
        {
            "watch_id",
            "provider",
            "resource_id",
            "provider_event_id",
            "observed_state",
            "observed_at",
            "evidence_locator",
            "metadata_digest",
            "canonical_refs",
            "schema_version",
        },
        "provider snapshot",
    )
    if not isinstance(obj["canonical_refs"], list):
        raise ProviderHostError("provider snapshot canonical_refs must be a list")
    return ProviderSnapshot(
        watch_id=obj["watch_id"],
        provider=obj["provider"],
        resource_id=obj["resource_id"],
        provider_event_id=obj["provider_event_id"],
        observed_state=obj["observed_state"],
        observed_at=obj["observed_at"],
        evidence_locator=obj["evidence_locator"],
        metadata_digest=obj["metadata_digest"],
        canonical_refs=tuple(obj["canonical_refs"]),
        schema_version=obj["schema_version"],
    )


def provider_watch_from_dict(data: Any) -> ProviderWatch:
    obj = _exact(
        data,
        {
            "watch_id",
            "provider",
            "resource_id",
            "matched_state",
            "portfolio_id",
            "transition_event",
            "evidence_kind",
            "action_ref",
            "summary",
            "canonical_refs",
            "uncertainties",
            "policy",
            "schema_version",
        },
        "provider watch",
    )
    if not isinstance(obj["canonical_refs"], list):
        raise ProviderHostError("provider watch canonical_refs must be a list")
    if not isinstance(obj["uncertainties"], list):
        raise ProviderHostError("provider watch uncertainties must be a list")
    return ProviderWatch(
        watch_id=obj["watch_id"],
        provider=obj["provider"],
        resource_id=obj["resource_id"],
        matched_state=obj["matched_state"],
        portfolio_id=obj["portfolio_id"],
        transition_event=obj["transition_event"],
        evidence_kind=obj["evidence_kind"],
        action_ref=obj["action_ref"],
        summary=obj["summary"],
        canonical_refs=tuple(obj["canonical_refs"]),
        uncertainties=tuple(obj["uncertainties"]),
        policy=transition_policy_from_dict(obj["policy"]),
        schema_version=obj["schema_version"],
    )


def load_provider_snapshot(path: str | Path) -> ProviderSnapshot:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderHostError(f"could not load provider snapshot: {exc}") from exc
    return provider_snapshot_from_dict(data)


def load_provider_watch(path: str | Path) -> ProviderWatch:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderHostError(f"could not load provider watch: {exc}") from exc
    return provider_watch_from_dict(data)


def build_provider_runtime_event(
    database: str | Path,
    watch: ProviderWatch,
    snapshot: ProviderSnapshot,
) -> ProviderHostResult:
    if snapshot.watch_id != watch.watch_id:
        raise ProviderHostError("snapshot watch_id does not match trusted watch")
    if snapshot.provider != watch.provider:
        raise ProviderHostError("snapshot provider does not match trusted watch")
    if snapshot.resource_id != watch.resource_id:
        raise ProviderHostError("snapshot resource_id does not match trusted watch")

    if snapshot.observed_state != watch.matched_state:
        return ProviderHostResult(
            matched=False,
            snapshot_digest=snapshot.digest,
            watch_digest=watch.digest,
            event_id=None,
            event_digest=None,
            reason="provider state has not reached the trusted matched_state",
            event=None,
        )

    store = SqlitePortfolioHeadStore(database)
    state, _, _ = recover_portfolio_after_restart(store, watch.portfolio_id)
    if state.active.state == "human_gate":
        raise ProviderHostError("provider snapshot cannot resume a human gate")

    rule = match_transition_rule(watch.policy, state.active.state, watch.transition_event)
    if rule.authority_mode == "preauthorized_required" or rule.from_state == "human_gate":
        raise ProviderHostError("provider watch cannot carry or substitute human authority")
    if watch.evidence_kind not in rule.required_evidence:
        raise ProviderHostError("trusted watch evidence_kind is not required by matched rule")

    evidence = CheckpointEvidence(
        kind=watch.evidence_kind,
        locator=snapshot.evidence_locator,
        digest=snapshot.digest,
    )
    canonical_refs = tuple(sorted(set(watch.canonical_refs + snapshot.canonical_refs)))
    observation = ResumeTickObservation(
        portfolio_id=watch.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=watch.policy.digest,
        event=watch.transition_event,
        evidence=(evidence,),
        action_ref=watch.action_ref,
        observed_at=snapshot.observed_at,
        summary=watch.summary,
        canonical_refs=canonical_refs,
        uncertainties=watch.uncertainties,
    )
    event_id = snapshot.event_identity
    trigger = ExternalTriggerEvidence(
        source=watch.provider,
        event_id=event_id,
        event_kind=watch.watch_id,
        payload_digest=snapshot.digest,
        observation_digest=observation.digest,
        admission_ref=snapshot.evidence_locator,
    )
    contract = TriggerContract(
        source=watch.provider,
        event_kind=watch.watch_id,
        portfolio_id=watch.portfolio_id,
        policy_digest=watch.policy.digest,
        transition_event=watch.transition_event,
    )
    event = {
        "schema_version": PERSISTENT_EVENT_SCHEMA,
        "event_id": event_id,
        "operation": "transition",
        "body": {
            "policy": transition_policy_to_dict(watch.policy),
            "contract": asdict(contract),
            "trigger": asdict(trigger),
            "observation": json.loads(canonical_json(observation)),
        },
    }
    return ProviderHostResult(
        matched=True,
        snapshot_digest=snapshot.digest,
        watch_digest=watch.digest,
        event_id=event_id,
        event_digest=sha256_digest(event),
        reason="trusted provider state matched; deterministic runtime event emitted",
        event=event,
    )
