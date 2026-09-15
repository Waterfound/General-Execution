from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .capacity import CapacityLease, CapacityRelease, CapacityTransition, RunnerCapacityState


class DurableCodecError(ValueError):
    pass


def _require_schema(data: dict[str, Any], expected: str) -> None:
    if data.get("schema_version") != expected:
        raise DurableCodecError(f"unsupported or missing schema: expected {expected}")


def capacity_lease_to_dict(lease: CapacityLease) -> dict[str, Any]:
    return asdict(lease)


def capacity_lease_from_dict(data: dict[str, Any]) -> CapacityLease:
    _require_schema(data, "ge.capacity-lease.v1")
    try:
        return CapacityLease(
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            slot=int(data["slot"]),
            session_id=str(data["session_id"]),
            logical_attempt=int(data["logical_attempt"]),
            authorization_id=str(data["authorization_id"]),
            authorization_digest=str(data["authorization_digest"]),
            invocation_id=str(data["invocation_id"]),
            physical_attempt=int(data["physical_attempt"]),
            previous_invocation_id=(
                str(data["previous_invocation_id"]) if data.get("previous_invocation_id") is not None else None
            ),
            previous_receipt_digest=(
                str(data["previous_receipt_digest"]) if data.get("previous_receipt_digest") is not None else None
            ),
            expected_state_digest=str(data["expected_state_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DurableCodecError("invalid capacity lease payload") from exc


def capacity_release_to_dict(release: CapacityRelease) -> dict[str, Any]:
    return asdict(release)


def capacity_release_from_dict(data: dict[str, Any]) -> CapacityRelease:
    _require_schema(data, "ge.capacity-release.v1")
    try:
        return CapacityRelease(
            lease_id=str(data["lease_id"]),
            lease_digest=str(data["lease_digest"]),
            runner_id=str(data["runner_id"]),
            session_id=str(data["session_id"]),
            logical_attempt=int(data["logical_attempt"]),
            authorization_id=str(data["authorization_id"]),
            authorization_digest=str(data["authorization_digest"]),
            invocation_id=str(data["invocation_id"]),
            physical_attempt=int(data["physical_attempt"]),
            release_kind=str(data["release_kind"]),
            expected_state_digest=str(data["expected_state_digest"]),
            outcome_digest=str(data["outcome_digest"]) if data.get("outcome_digest") is not None else None,
            receipt_digest=str(data["receipt_digest"]) if data.get("receipt_digest") is not None else None,
            transport_status=str(data["transport_status"]) if data.get("transport_status") is not None else None,
            revoked_session_digest=(
                str(data["revoked_session_digest"]) if data.get("revoked_session_digest") is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DurableCodecError("invalid capacity release payload") from exc


def capacity_transition_to_dict(transition: CapacityTransition) -> dict[str, Any]:
    return {
        "schema_version": transition.schema_version,
        "kind": transition.kind,
        "expected_state_digest": transition.expected_state_digest,
        "lease": capacity_lease_to_dict(transition.lease) if transition.lease else None,
        "release": capacity_release_to_dict(transition.release) if transition.release else None,
    }


def capacity_transition_from_dict(data: dict[str, Any]) -> CapacityTransition:
    _require_schema(data, "ge.capacity-transition.v1")
    try:
        lease_data = data.get("lease")
        release_data = data.get("release")
        return CapacityTransition(
            kind=str(data["kind"]),
            expected_state_digest=str(data["expected_state_digest"]),
            lease=capacity_lease_from_dict(lease_data) if lease_data is not None else None,
            release=capacity_release_from_dict(release_data) if release_data is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DurableCodecError):
            raise
        raise DurableCodecError("invalid capacity transition payload") from exc


def capacity_state_to_dict(state: RunnerCapacityState) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "runner_id": state.runner_id,
        "runner_capability_digest": state.runner_capability_digest,
        "max_parallelism": state.max_parallelism,
        "generation": state.generation,
        "previous_state_digest": state.previous_state_digest,
        "transitions": [capacity_transition_to_dict(item) for item in state.transitions],
    }


def capacity_state_from_dict(data: dict[str, Any]) -> RunnerCapacityState:
    _require_schema(data, "ge.runner-capacity-state.v1")
    try:
        return RunnerCapacityState(
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            max_parallelism=int(data["max_parallelism"]),
            generation=int(data["generation"]),
            previous_state_digest=(
                str(data["previous_state_digest"]) if data.get("previous_state_digest") is not None else None
            ),
            transitions=tuple(capacity_transition_from_dict(item) for item in data.get("transitions", [])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DurableCodecError):
            raise
        raise DurableCodecError("invalid runner capacity state payload") from exc
