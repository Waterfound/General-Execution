"""Native persistent-runtime host for bounded Autonomous Burst manifests.

This layer is intentionally above the existing atomic persistent runtime.
It never batches a state transition internally. Instead it loads an immutable
manifest of immutable event files and feeds each event through
process_persistent_runtime_event(), recovering durable state between steps.

The host:
- creates no authority;
- synthesizes no events or evidence;
- carries no credentials;
- stops fail-closed on stale/non-committed/gated/waiting/terminal state;
- preserves the existing one-transition runtime semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath, Path
import re
from typing import Callable, Literal

from .canonical import sha256_digest
from .core_rehearsal import CoreRehearsalReport
from .persistent_runtime import (
    PersistentRuntimeEventReport,
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from .portfolio_persistence import SqlitePortfolioHeadStore, recover_portfolio_after_restart
from .resume_tick import CoreVerificationReceipt, CoreVerificationRequirement

PERSISTENT_BURST_MANIFEST_SCHEMA = "ge.persistent-burst-manifest.v1"
PERSISTENT_BURST_EVENT_REF_SCHEMA = "ge.persistent-burst-event-ref.v1"
PERSISTENT_BURST_STEP_SCHEMA = "ge.persistent-burst-step.v1"
PERSISTENT_BURST_REPORT_SCHEMA = "ge.persistent-burst-execution.v1"

BurstSourceKind = Literal["hourly_watchdog", "provider_event", "heartbeat", "manual"]
BurstDisposition = Literal[
    "completed",
    "stopped",
    "start_state_mismatch",
    "transition_budget_exhausted",
]

_CONTINUABLE_STATES = {"ready", "running", "verifying", "rework"}
_TERMINAL_STATE_REASONS = {
    "human_gate": "HUMAN_GATE",
    "waiting_external": "WAITING_EXTERNAL",
    "passive": "PASSIVE_WAIT",
    "complete": "CEILING_REACHED",
    "failed": "FAILED",
    "di_required": "DI_REQUIRED",
}
_FORBIDDEN_KEYS = (
    "secret",
    "password",
    "token",
    "credential",
    "private_key",
    "private-key",
    "api_key",
    "api-key",
)


class PersistentBurstHostError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PersistentBurstHostError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise PersistentBurstHostError(f"{name} must be sha256:<64-hex>")


def _exact(data, fields: set[str], label: str) -> dict:
    if not isinstance(data, dict):
        raise PersistentBurstHostError(f"{label} must be an object")
    actual = set(data)
    if actual != fields:
        raise PersistentBurstHostError(
            f"{label} fields mismatch: missing={sorted(fields-actual)} "
            f"unknown={sorted(actual-fields)}"
        )
    return data


def _content_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _reject_credential_shaped(value, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            if any(term in low for term in _FORBIDDEN_KEYS):
                raise PersistentBurstHostError(
                    f"credential-shaped key forbidden: {path}.{key}"
                )
            _reject_credential_shaped(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credential_shaped(child, f"{path}[{index}]")


@dataclass(frozen=True, slots=True)
class PersistentBurstEventRef:
    path: str
    content_digest: str
    schema_version: str = PERSISTENT_BURST_EVENT_REF_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERSISTENT_BURST_EVENT_REF_SCHEMA:
            raise PersistentBurstHostError("unsupported burst event-ref schema")
        _nonempty("path", self.path)
        _digest("content_digest", self.content_digest)
        p = PurePosixPath(self.path)
        if p.is_absolute() or ".." in p.parts:
            raise PersistentBurstHostError("burst event path must be safe and relative")
        if len(p.parts) != 2 or p.parts[0] != "burst-events":
            raise PersistentBurstHostError(
                "burst event path must be burst-events/<event-id>.json"
            )
        if p.suffix != ".json":
            raise PersistentBurstHostError("burst event path must end in .json")


@dataclass(frozen=True, slots=True)
class PersistentBurstManifest:
    burst_id: str
    portfolio_id: str
    source_kind: BurstSourceKind
    expected_start_generation: int
    expected_start_state_digest: str
    max_transitions: int
    event_refs: tuple[PersistentBurstEventRef, ...]
    created_at: str
    authority_created: bool = False
    schema_version: str = PERSISTENT_BURST_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERSISTENT_BURST_MANIFEST_SCHEMA:
            raise PersistentBurstHostError("unsupported burst manifest schema")
        for name in ("burst_id", "portfolio_id", "created_at"):
            _nonempty(name, getattr(self, name))
        if self.source_kind not in {
            "hourly_watchdog",
            "provider_event",
            "heartbeat",
            "manual",
        }:
            raise PersistentBurstHostError("unsupported burst source_kind")
        if (
            type(self.expected_start_generation) is not int
            or self.expected_start_generation < 0
        ):
            raise PersistentBurstHostError(
                "expected_start_generation must be a non-negative integer"
            )
        _digest("expected_start_state_digest", self.expected_start_state_digest)
        if type(self.max_transitions) is not int or not (1 <= self.max_transitions <= 32):
            raise PersistentBurstHostError("max_transitions must be between 1 and 32")
        if not self.event_refs:
            raise PersistentBurstHostError("burst manifest requires event_refs")
        if len(self.event_refs) > self.max_transitions:
            raise PersistentBurstHostError(
                "event_refs exceed the bounded max_transitions"
            )
        paths = tuple(ref.path for ref in self.event_refs)
        if len(paths) != len(set(paths)):
            raise PersistentBurstHostError("burst event paths must be unique")
        if self.authority_created:
            raise PersistentBurstHostError("burst manifest cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PersistentBurstStep:
    index: int
    event_path: str
    event_content_digest: str
    event_id: str
    event_report_digest: str
    status: str
    pre_generation: int
    post_generation: int
    pre_state_digest: str
    post_state_digest: str
    human_required: bool
    schema_version: str = PERSISTENT_BURST_STEP_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERSISTENT_BURST_STEP_SCHEMA:
            raise PersistentBurstHostError("unsupported burst step schema")
        if type(self.index) is not int or self.index < 0:
            raise PersistentBurstHostError("step index must be non-negative")
        for name in ("event_path", "event_id", "status"):
            _nonempty(name, getattr(self, name))
        for name in (
            "event_content_digest",
            "event_report_digest",
            "pre_state_digest",
            "post_state_digest",
        ):
            _digest(name, getattr(self, name))
        if self.post_generation < self.pre_generation:
            raise PersistentBurstHostError("burst step cannot move generation backwards")


@dataclass(frozen=True, slots=True)
class PersistentBurstExecutionReport:
    burst_id: str
    manifest_digest: str
    portfolio_id: str
    source_kind: BurstSourceKind
    disposition: BurstDisposition
    stop_reason: str
    initial_generation: int
    final_generation: int
    initial_state_digest: str
    final_state_digest: str
    steps: tuple[PersistentBurstStep, ...]
    authority_created: bool = False
    schema_version: str = PERSISTENT_BURST_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERSISTENT_BURST_REPORT_SCHEMA:
            raise PersistentBurstHostError("unsupported burst execution schema")
        for name in ("burst_id", "portfolio_id", "stop_reason"):
            _nonempty(name, getattr(self, name))
        _digest("manifest_digest", self.manifest_digest)
        _digest("initial_state_digest", self.initial_state_digest)
        _digest("final_state_digest", self.final_state_digest)
        if self.disposition not in {
            "completed",
            "stopped",
            "start_state_mismatch",
            "transition_budget_exhausted",
        }:
            raise PersistentBurstHostError("unsupported burst disposition")
        if self.final_generation < self.initial_generation:
            raise PersistentBurstHostError("burst report generation moved backwards")
        if self.authority_created:
            raise PersistentBurstHostError("burst execution cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def persistent_burst_event_ref_from_dict(data) -> PersistentBurstEventRef:
    obj = _exact(
        data,
        {"path", "content_digest", "schema_version"},
        "burst event ref",
    )
    return PersistentBurstEventRef(**obj)


def persistent_burst_manifest_from_dict(data) -> PersistentBurstManifest:
    obj = _exact(
        data,
        {
            "burst_id",
            "portfolio_id",
            "source_kind",
            "expected_start_generation",
            "expected_start_state_digest",
            "max_transitions",
            "event_refs",
            "created_at",
            "authority_created",
            "schema_version",
        },
        "burst manifest",
    )
    if not isinstance(obj["event_refs"], list):
        raise PersistentBurstHostError("event_refs must be a list")
    return PersistentBurstManifest(
        burst_id=obj["burst_id"],
        portfolio_id=obj["portfolio_id"],
        source_kind=obj["source_kind"],
        expected_start_generation=obj["expected_start_generation"],
        expected_start_state_digest=obj["expected_start_state_digest"],
        max_transitions=obj["max_transitions"],
        event_refs=tuple(
            persistent_burst_event_ref_from_dict(item)
            for item in obj["event_refs"]
        ),
        created_at=obj["created_at"],
        authority_created=obj["authority_created"],
        schema_version=obj["schema_version"],
    )


def _report(
    manifest: PersistentBurstManifest,
    *,
    disposition: BurstDisposition,
    stop_reason: str,
    initial_generation: int,
    initial_state_digest: str,
    final_generation: int,
    final_state_digest: str,
    steps: list[PersistentBurstStep],
) -> PersistentBurstExecutionReport:
    return PersistentBurstExecutionReport(
        burst_id=manifest.burst_id,
        manifest_digest=manifest.digest,
        portfolio_id=manifest.portfolio_id,
        source_kind=manifest.source_kind,
        disposition=disposition,
        stop_reason=stop_reason,
        initial_generation=initial_generation,
        final_generation=final_generation,
        initial_state_digest=initial_state_digest,
        final_state_digest=final_state_digest,
        steps=tuple(steps),
    )


def execute_persistent_burst(
    database: str | Path,
    manifest: PersistentBurstManifest,
    load_event_bytes: Callable[[str], bytes],
    *,
    core_requirement: CoreVerificationRequirement,
    core_verification: CoreVerificationReceipt,
    core_report: CoreRehearsalReport,
) -> PersistentBurstExecutionReport:
    """Execute an immutable manifest as a sequence of atomic persistent events.

    The loader supplies the exact bytes bound by each event-ref. Each event is
    still processed by the existing one-transition persistent runtime.
    """
    store = SqlitePortfolioHeadStore(database)
    state, _, _ = recover_portfolio_after_restart(store, manifest.portfolio_id)
    initial_generation = state.generation
    initial_digest = state.digest
    steps: list[PersistentBurstStep] = []

    if (
        state.generation != manifest.expected_start_generation
        or state.digest != manifest.expected_start_state_digest
    ):
        return _report(
            manifest,
            disposition="start_state_mismatch",
            stop_reason="START_STATE_MISMATCH",
            initial_generation=initial_generation,
            initial_state_digest=initial_digest,
            final_generation=state.generation,
            final_state_digest=state.digest,
            steps=steps,
        )

    seen_event_ids: set[str] = set()

    for index, event_ref in enumerate(manifest.event_refs):
        if index >= manifest.max_transitions:
            return _report(
                manifest,
                disposition="transition_budget_exhausted",
                stop_reason="MAX_TRANSITIONS_REACHED",
                initial_generation=initial_generation,
                initial_state_digest=initial_digest,
                final_generation=state.generation,
                final_state_digest=state.digest,
                steps=steps,
            )

        raw = load_event_bytes(event_ref.path)
        if not isinstance(raw, (bytes, bytearray)):
            raise PersistentBurstHostError("event loader must return bytes")
        raw = bytes(raw)
        if _content_digest(raw) != event_ref.content_digest:
            raise PersistentBurstHostError(
                f"event content digest mismatch: {event_ref.path}"
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PersistentBurstHostError(
                f"event is not valid UTF-8 JSON: {event_ref.path}"
            ) from exc
        _reject_credential_shaped(payload)
        if payload.get("schema_version") != "ge.persistent-runtime-event.v1":
            raise PersistentBurstHostError("burst contains unsupported event schema")
        if payload.get("operation") != "transition":
            raise PersistentBurstHostError(
                "native burst manifest may contain transition events only"
            )
        event_id = payload.get("event_id")
        _nonempty("event_id", event_id)
        expected_name = f"{event_id}.json"
        if PurePosixPath(event_ref.path).name != expected_name:
            raise PersistentBurstHostError(
                "event path filename must match event_id"
            )
        if event_id in seen_event_ids:
            raise PersistentBurstHostError("burst event_id values must be unique")
        seen_event_ids.add(event_id)

        body = payload.get("body")
        if not isinstance(body, dict):
            raise PersistentBurstHostError("transition event body must be an object")
        contract = body.get("contract")
        if not isinstance(contract, dict) or contract.get("portfolio_id") != manifest.portfolio_id:
            raise PersistentBurstHostError("burst event portfolio mismatch")

        authenticated_digest = trigger_digest_from_event(payload)
        if authenticated_digest is None:
            raise PersistentBurstHostError(
                "transition event did not yield authenticated trigger digest"
            )

        result: PersistentRuntimeEventReport = process_persistent_runtime_event(
            database,
            payload,
            authenticated_trigger_digest=authenticated_digest,
            core_requirement=core_requirement,
            core_verification=core_verification,
            core_report=core_report,
        )
        step = PersistentBurstStep(
            index=index,
            event_path=event_ref.path,
            event_content_digest=event_ref.content_digest,
            event_id=result.event_id,
            event_report_digest=result.digest,
            status=result.status,
            pre_generation=result.pre_generation,
            post_generation=result.post_generation,
            pre_state_digest=result.pre_state_digest,
            post_state_digest=result.post_state_digest,
            human_required=result.human_required,
        )
        steps.append(step)

        # Fresh durable recovery after every exact atomic event.
        state, _, _ = recover_portfolio_after_restart(store, manifest.portfolio_id)

        if (
            state.generation != result.post_generation
            or state.digest != result.post_state_digest
        ):
            raise PersistentBurstHostError(
                "fresh durable recovery disagrees with event report"
            )

        if result.status != "committed":
            return _report(
                manifest,
                disposition="stopped",
                stop_reason=f"NON_COMMITTED_{result.status.upper()}",
                initial_generation=initial_generation,
                initial_state_digest=initial_digest,
                final_generation=state.generation,
                final_state_digest=state.digest,
                steps=steps,
            )

        if result.human_required or state.active.state == "human_gate":
            return _report(
                manifest,
                disposition="stopped",
                stop_reason="HUMAN_GATE",
                initial_generation=initial_generation,
                initial_state_digest=initial_digest,
                final_generation=state.generation,
                final_state_digest=state.digest,
                steps=steps,
            )

        terminal_reason = _TERMINAL_STATE_REASONS.get(state.active.state)
        if terminal_reason is not None:
            return _report(
                manifest,
                disposition="completed" if state.active.state == "complete" else "stopped",
                stop_reason=terminal_reason,
                initial_generation=initial_generation,
                initial_state_digest=initial_digest,
                final_generation=state.generation,
                final_state_digest=state.digest,
                steps=steps,
            )

        if state.active.state not in _CONTINUABLE_STATES:
            return _report(
                manifest,
                disposition="stopped",
                stop_reason=f"UNSUPPORTED_ACTIVE_STATE_{state.active.state.upper()}",
                initial_generation=initial_generation,
                initial_state_digest=initial_digest,
                final_generation=state.generation,
                final_state_digest=state.digest,
                steps=steps,
            )

    return _report(
        manifest,
        disposition="stopped",
        stop_reason="MANIFEST_EXHAUSTED_REQUIRES_FRESH_EVIDENCE",
        initial_generation=initial_generation,
        initial_state_digest=initial_digest,
        final_generation=state.generation,
        final_state_digest=state.digest,
        steps=steps,
    )
