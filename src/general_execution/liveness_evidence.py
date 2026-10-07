from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Any
import re


REVISION = re.compile(r"^[a-f0-9]{40}$")


class LivenessKind(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    HEARTBEAT = "heartbeat"
    PROGRESS = "progress"
    COMPLETED = "completed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_FAILED = "provider_failed"
    WORKLOAD_FAILED = "workload_failed"
    RECOVERY_EXHAUSTED = "recovery_exhausted"


@dataclass(frozen=True, slots=True)
class LivenessObservation:
    sequence: int
    kind: LivenessKind
    observed_at: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class LivenessProjection:
    workstream_id: str
    repository: str
    source_revision: str
    provider: Mapping[str, object]
    durable_overlay: Mapping[str, object]
    authority_created: bool = False
    execution_triggered: bool = False


def _nonempty(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _revision(value: object) -> str:
    text = _nonempty("source_revision", value)
    if not REVISION.fullmatch(text):
        raise ValueError("source_revision must be an exact lowercase 40-hex revision")
    return text


def _observations(values: object) -> tuple[LivenessObservation, ...]:
    if not isinstance(values, list) or not values:
        raise ValueError("liveness observations must be a non-empty list")
    out: list[LivenessObservation] = []
    previous = -1
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping):
            raise ValueError(f"observations[{index}] must be an object")
        sequence = raw.get("sequence")
        if type(sequence) is not int or sequence < 0 or sequence <= previous:
            raise ValueError("liveness sequences must be strictly increasing non-negative integers")
        previous = sequence
        try:
            kind = LivenessKind(str(raw.get("kind")))
        except ValueError as exc:
            raise ValueError(f"unsupported liveness kind: {raw.get('kind')}") from exc
        observed_at = _nonempty("observed_at", raw.get("observed_at"))
        detail = raw.get("detail")
        if detail is not None:
            detail = _nonempty("detail", detail)
        out.append(LivenessObservation(sequence, kind, observed_at, detail))
    return tuple(out)


def normalize_liveness_mapping(data: Mapping[str, object]) -> LivenessProjection:
    workstream_id = _nonempty("workstream_id", data.get("workstream_id"))
    repository = _nonempty("repository", data.get("repository"))
    source_revision = _revision(data.get("source_revision"))
    provider_name = _nonempty("provider", data.get("provider"))
    dispatch_identity = _nonempty("dispatch_identity", data.get("dispatch_identity"))
    execution_expected = data.get("execution_expected")
    if type(execution_expected) is not bool:
        raise ValueError("execution_expected must be boolean")

    observations = _observations(data.get("observations"))
    provider_obs = next(
        (item for item in reversed(observations) if item.kind is not LivenessKind.RECOVERY_EXHAUSTED),
        None,
    )
    if provider_obs is None:
        provider_state = "UNKNOWN"
        failure_scope = "NONE"
        detail = "recovery evidence exists without provider-state observation"
    elif provider_obs.kind is LivenessKind.QUEUED:
        provider_state, failure_scope = "QUEUED", "NONE"
        detail = provider_obs.detail
    elif provider_obs.kind in {LivenessKind.STARTED, LivenessKind.HEARTBEAT, LivenessKind.PROGRESS}:
        provider_state, failure_scope = "ACTIVE", "NONE"
        detail = provider_obs.detail
    elif provider_obs.kind is LivenessKind.COMPLETED:
        provider_state, failure_scope = "COMPLETED", "NONE"
        detail = provider_obs.detail
    elif provider_obs.kind is LivenessKind.PROVIDER_UNAVAILABLE:
        provider_state, failure_scope = "UNAVAILABLE", "PROVIDER"
        detail = provider_obs.detail
    elif provider_obs.kind is LivenessKind.PROVIDER_FAILED:
        provider_state, failure_scope = "FAILED", "PROVIDER"
        detail = provider_obs.detail
    elif provider_obs.kind is LivenessKind.WORKLOAD_FAILED:
        provider_state, failure_scope = "FAILED", "WORKLOAD"
        detail = provider_obs.detail
    else:
        raise AssertionError(provider_obs.kind)

    recovery_exhausted = observations[-1].kind is LivenessKind.RECOVERY_EXHAUSTED
    if recovery_exhausted:
        provider_state = "UNKNOWN"
        failure_scope = "NONE"
        detail = observations[-1].detail or "bounded recovery semantics exhausted"

    progress_kinds = {
        LivenessKind.STARTED,
        LivenessKind.HEARTBEAT,
        LivenessKind.PROGRESS,
        LivenessKind.COMPLETED,
        LivenessKind.WORKLOAD_FAILED,
    }
    progress = next((item for item in reversed(observations) if item.kind in progress_kinds), None)
    active_dispatch = bool(
        provider_obs
        and provider_obs.kind in {LivenessKind.STARTED, LivenessKind.HEARTBEAT, LivenessKind.PROGRESS}
        and not recovery_exhausted
    )

    provider = {
        "provider": provider_name,
        "state": provider_state,
        "observed_at": observations[-1].observed_at if recovery_exhausted else (provider_obs.observed_at if provider_obs else observations[-1].observed_at),
        "subject_revision": source_revision,
        "failure_scope": failure_scope,
        "detail": detail,
        "dispatch_identity": dispatch_identity,
    }
    durable_overlay = {
        "active_dispatch": active_dispatch,
        "last_progress_at": progress.observed_at if progress else None,
        "execution_expected": execution_expected,
        "recovery_semantics_exhausted": recovery_exhausted,
    }
    return LivenessProjection(
        workstream_id=workstream_id,
        repository=repository,
        source_revision=source_revision,
        provider=provider,
        durable_overlay=durable_overlay,
    )


def apply_liveness_to_snapshot_mapping(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(snapshot))
    raw = out.pop("liveness", None)
    if raw is None:
        return out
    if not isinstance(raw, Mapping):
        raise ValueError("liveness must be an object")
    projection = normalize_liveness_mapping(raw)

    provider = dict(projection.provider)
    provider.pop("dispatch_identity", None)
    existing_provider = out.get("provider")
    if existing_provider is not None and existing_provider != provider:
        raise ValueError("explicit provider evidence conflicts with liveness projection")
    out["provider"] = provider

    durable = out.get("durable")
    if durable is not None:
        if not isinstance(durable, Mapping):
            raise ValueError("durable must be an object")
        durable = dict(durable)
        if str(durable.get("workstream_id")) != projection.workstream_id:
            raise ValueError("durable workstream identity conflicts with liveness")
        if durable.get("bound_repository") not in {None, projection.repository}:
            raise ValueError("durable repository binding conflicts with liveness")
        if durable.get("bound_branch_head") not in {None, projection.source_revision}:
            raise ValueError("durable revision binding conflicts with liveness")
        for key, value in projection.durable_overlay.items():
            durable[key] = value
        out["durable"] = durable
    elif projection.durable_overlay["recovery_semantics_exhausted"]:
        raise ValueError("recovery exhaustion requires existing durable-state evidence")

    return out
