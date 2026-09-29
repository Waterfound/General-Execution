from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from .canonical import canonical_json, stable_id
from .portfolio_state import PortfolioState
from .provider_host import (
    ProviderHostResult,
    ProviderInput,
    ProviderWatchContract,
    build_provider_runtime_event,
)

WATCH_SCHEMA = "ge.workstream-result-watch.v1"
HANDOFF_REPORT_SCHEMA = "ge.workstream-result-handoff.v1"
PROVIDER = "github-workstream-result"

TransitionClass = Literal[
    "NEXT_FRONTIER_DISPATCHED",
    "CONDITION_WAIT",
    "SCHEDULED_WAIT",
    "HUMAN_GATE",
    "EXTERNAL_EVIDENCE_GATE",
    "DI_REQUIRED",
    "FAILED",
    "DONE_TECHNICAL",
    "DONE_CANONICAL",
]
AuthorityRequirement = Literal["none", "existing"]

VALID_TRANSITION_CLASSES = {
    "NEXT_FRONTIER_DISPATCHED",
    "CONDITION_WAIT",
    "SCHEDULED_WAIT",
    "HUMAN_GATE",
    "EXTERNAL_EVIDENCE_GATE",
    "DI_REQUIRED",
    "FAILED",
    "DONE_TECHNICAL",
    "DONE_CANONICAL",
}
VALID_AUTHORITY_REQUIREMENTS = {"none", "existing"}


class WorkstreamResultHandoffError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise WorkstreamResultHandoffError(f"{name} must be a non-empty string")


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise WorkstreamResultHandoffError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise WorkstreamResultHandoffError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


def _lookup(payload: dict[str, Any], field: str) -> Any:
    value: Any = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise WorkstreamResultHandoffError(f"missing result field: {field}")
        value = value[part]
    return value


@dataclass(frozen=True, slots=True)
class ResultOutcome:
    observed_state: str
    transition_class: TransitionClass
    provider_contract_path: str
    authority_requirement: AuthorityRequirement

    def __post_init__(self) -> None:
        _nonempty("outcome.observed_state", self.observed_state)
        _nonempty("outcome.provider_contract_path", self.provider_contract_path)
        if self.transition_class not in VALID_TRANSITION_CLASSES:
            raise WorkstreamResultHandoffError("unsupported transition class")
        if self.authority_requirement not in VALID_AUTHORITY_REQUIREMENTS:
            raise WorkstreamResultHandoffError("unsupported authority requirement")


@dataclass(frozen=True, slots=True)
class WorkstreamResultWatch:
    watch_id: str
    source_repository: str
    source_ref: str
    result_path: str
    result_schema_field: str
    expected_result_schema: str
    observed_state_field: str
    outcomes: tuple[ResultOutcome, ...]
    enabled: bool
    schema_version: str = WATCH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WATCH_SCHEMA:
            raise WorkstreamResultHandoffError("unsupported workstream result watch schema")
        for name in (
            "watch_id",
            "source_repository",
            "source_ref",
            "result_path",
            "result_schema_field",
            "expected_result_schema",
            "observed_state_field",
        ):
            _nonempty(name, getattr(self, name))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.source_repository):
            raise WorkstreamResultHandoffError("source_repository must be owner/repository")
        if self.result_path.startswith("/") or ".." in self.result_path.split("/"):
            raise WorkstreamResultHandoffError("result_path must be repository-relative")
        if type(self.enabled) is not bool:
            raise WorkstreamResultHandoffError("enabled must be boolean")
        if not self.outcomes:
            raise WorkstreamResultHandoffError("at least one result outcome is required")
        states = tuple(item.observed_state for item in self.outcomes)
        if states != tuple(sorted(states)):
            raise WorkstreamResultHandoffError("outcomes must be sorted by observed_state")
        if len(states) != len(set(states)):
            raise WorkstreamResultHandoffError("outcomes must be unique by observed_state")


@dataclass(frozen=True, slots=True)
class ObservedWorkstreamResult:
    source_commit: str
    observed_at: str
    content_digest: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.source_commit):
            raise WorkstreamResultHandoffError("source_commit must be exact 40-hex SHA")
        _nonempty("observed_at", self.observed_at)
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.content_digest):
            raise WorkstreamResultHandoffError("content_digest must be sha256:<64-hex>")
        if not isinstance(self.payload, dict):
            raise WorkstreamResultHandoffError("payload must be an object")


@dataclass(frozen=True, slots=True)
class WorkstreamResultHandoff:
    handoff_id: str
    transition_class: TransitionClass
    observed_state: str
    source_repository: str
    source_ref: str
    source_commit: str
    result_path: str
    content_digest: str
    provider_input: ProviderInput
    provider_result: ProviderHostResult
    runtime_event: dict[str, Any]
    authority_created: bool = False
    schema_version: str = HANDOFF_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != HANDOFF_REPORT_SCHEMA:
            raise WorkstreamResultHandoffError("unsupported handoff report schema")
        if self.authority_created:
            raise WorkstreamResultHandoffError("handoff must never create authority")


def workstream_result_watch_from_dict(data: Any) -> WorkstreamResultWatch:
    obj = _exact(
        data,
        {
            "watch_id",
            "source_repository",
            "source_ref",
            "result_path",
            "result_schema_field",
            "expected_result_schema",
            "observed_state_field",
            "outcomes",
            "enabled",
            "schema_version",
        },
        "workstream result watch",
    )
    if not isinstance(obj["outcomes"], list):
        raise WorkstreamResultHandoffError("outcomes must be a list")
    outcomes: list[ResultOutcome] = []
    for raw in obj["outcomes"]:
        item = _exact(
            raw,
            {
                "observed_state",
                "transition_class",
                "provider_contract_path",
                "authority_requirement",
            },
            "workstream result outcome",
        )
        outcomes.append(ResultOutcome(**item))
    return WorkstreamResultWatch(
        watch_id=obj["watch_id"],
        source_repository=obj["source_repository"],
        source_ref=obj["source_ref"],
        result_path=obj["result_path"],
        result_schema_field=obj["result_schema_field"],
        expected_result_schema=obj["expected_result_schema"],
        observed_state_field=obj["observed_state_field"],
        outcomes=tuple(outcomes),
        enabled=obj["enabled"],
        schema_version=obj["schema_version"],
    )


def select_result_outcome(
    watch: WorkstreamResultWatch, payload: dict[str, Any]
) -> ResultOutcome:
    schema = _lookup(payload, watch.result_schema_field)
    if schema != watch.expected_result_schema:
        raise WorkstreamResultHandoffError(
            f"result schema mismatch: expected={watch.expected_result_schema!r} "
            f"observed={schema!r}"
        )
    observed_state = _lookup(payload, watch.observed_state_field)
    if not isinstance(observed_state, str) or not observed_state:
        raise WorkstreamResultHandoffError("observed result state must be non-empty")
    matches = tuple(x for x in watch.outcomes if x.observed_state == observed_state)
    if len(matches) != 1:
        raise WorkstreamResultHandoffError(
            f"no explicit outcome contract for observed state: {observed_state}"
        )
    return matches[0]


def stable_handoff_id(
    watch: WorkstreamResultWatch, observed: ObservedWorkstreamResult
) -> str:
    return stable_id(
        "gewrh",
        {
            "watch_id": watch.watch_id,
            "repository": watch.source_repository,
            "ref": watch.source_ref,
            "path": watch.result_path,
            "source_commit": observed.source_commit,
            "content_digest": observed.content_digest,
        },
    )


def _expected_bindings(watch: WorkstreamResultWatch) -> tuple[tuple[str, str], ...]:
    return tuple(sorted({
        "repository": watch.source_repository,
        "ref": watch.source_ref,
        "result_path": watch.result_path,
        "result_schema": watch.expected_result_schema,
    }.items()))


def _validate_transition_class(
    transition_class: str, to_state: str, authority_mode: str
) -> None:
    if transition_class == "HUMAN_GATE":
        if to_state != "human_gate" or authority_mode != "human_required":
            raise WorkstreamResultHandoffError("HUMAN_GATE outcome must stop at human gate")
    elif transition_class == "DI_REQUIRED":
        if to_state != "di_required":
            raise WorkstreamResultHandoffError("DI_REQUIRED outcome must enter di_required")
    elif transition_class == "FAILED":
        if to_state != "failed":
            raise WorkstreamResultHandoffError("FAILED outcome must enter failed")
    elif transition_class in {"CONDITION_WAIT", "SCHEDULED_WAIT", "EXTERNAL_EVIDENCE_GATE"}:
        if to_state != "waiting_external":
            raise WorkstreamResultHandoffError("wait/gate outcome must enter waiting_external")
    elif transition_class in {"DONE_TECHNICAL", "DONE_CANONICAL"}:
        if to_state != "complete":
            raise WorkstreamResultHandoffError("done outcome must enter complete")
    elif transition_class == "NEXT_FRONTIER_DISPATCHED":
        if to_state in {"human_gate", "waiting_external", "di_required", "failed", "complete"}:
            raise WorkstreamResultHandoffError(
                "NEXT_FRONTIER_DISPATCHED must remain in an executable lifecycle state"
            )


def reconcile_workstream_result(
    state: PortfolioState,
    watch: WorkstreamResultWatch,
    contract: ProviderWatchContract,
    observed: ObservedWorkstreamResult,
) -> WorkstreamResultHandoff:
    outcome = select_result_outcome(watch, observed.payload)
    expected_subject = f"github://{watch.source_repository}/{watch.result_path}"
    if contract.watch_id != watch.watch_id:
        raise WorkstreamResultHandoffError("provider contract watch_id mismatch")
    if contract.provider != PROVIDER:
        raise WorkstreamResultHandoffError("provider contract must use github-workstream-result")
    if contract.subject_ref != expected_subject:
        raise WorkstreamResultHandoffError("provider contract subject_ref mismatch")
    if contract.satisfied_state != outcome.observed_state:
        raise WorkstreamResultHandoffError("provider contract satisfied_state mismatch")
    if contract.required_bindings != _expected_bindings(watch):
        raise WorkstreamResultHandoffError("provider contract source bindings mismatch")
    if state.portfolio_id != contract.portfolio_id:
        raise WorkstreamResultHandoffError("portfolio id mismatch")

    rules = tuple(
        rule for rule in contract.policy.rules
        if rule.from_state == state.active.state
        and rule.event == contract.transition_event
    )
    if len(rules) != 1:
        raise WorkstreamResultHandoffError(
            "no unique provider transition for current durable state"
        )
    rule = rules[0]
    _validate_transition_class(outcome.transition_class, rule.to_state, rule.authority_mode)

    if outcome.authority_requirement == "existing":
        if not state.active.authority_ref or not state.active.authority_boundary:
            raise WorkstreamResultHandoffError(
                "existing authority evidence is required for this result"
            )
        if rule.authority_mode != "none":
            raise WorkstreamResultHandoffError(
                "existing-authority continuation must not request or create new authority"
            )

    evidence_locator = (
        f"github://{watch.source_repository}/commit/{observed.source_commit}/"
        f"{watch.result_path}"
    )
    handoff_id = stable_handoff_id(watch, observed)
    provider_input = ProviderInput(
        watch_id=watch.watch_id,
        provider=PROVIDER,
        provider_event_id=handoff_id,
        subject_ref=expected_subject,
        observed_state=outcome.observed_state,
        observed_at=observed.observed_at,
        evidence_locator=evidence_locator,
        evidence_digest=observed.content_digest,
        bindings=_expected_bindings(watch),
        canonical_refs=tuple(sorted({
            f"github://{watch.source_repository}/commit/{observed.source_commit}",
            evidence_locator,
        })),
    )
    event, provider_result = build_provider_runtime_event(state, contract, provider_input)
    if event is None or provider_result.status != "event_ready":
        raise WorkstreamResultHandoffError(
            "valid completion result did not materialize a runtime event"
        )
    return WorkstreamResultHandoff(
        handoff_id=handoff_id,
        transition_class=outcome.transition_class,
        observed_state=outcome.observed_state,
        source_repository=watch.source_repository,
        source_ref=watch.source_ref,
        source_commit=observed.source_commit,
        result_path=watch.result_path,
        content_digest=observed.content_digest,
        provider_input=provider_input,
        provider_result=provider_result,
        runtime_event=event,
    )


def handoff_to_dict(value: WorkstreamResultHandoff) -> dict[str, Any]:
    return json.loads(canonical_json(value))
