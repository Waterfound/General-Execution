from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

from .canonical import canonical_json, sha256_digest, stable_id
from .capacity import RunnerCapacityState, verify_capacity_state
from .durable_codec import DurableCodecError, capacity_state_from_dict, capacity_state_to_dict
from .models import RunnerCapabilities

RecoveryStatus = Literal["clean", "reconciliation_required"]
RECOVERED_LEASE_STATUS = "in_flight_unknown"


class DurableStateError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _require_schema(actual: str, expected: str) -> None:
    if actual != expected:
        raise ValueError(f"schema_version must be {expected}")


@dataclass(frozen=True, slots=True)
class DurableCapacityHead:
    runner_id: str
    runner_capability_digest: str
    generation: int
    state_digest: str
    payload_digest: str
    previous_head_digest: str | None = None
    schema_version: str = "ge.durable-capacity-head.v1"

    def __post_init__(self) -> None:
        _require_schema(self.schema_version, "ge.durable-capacity-head.v1")
        if not self.runner_id or not self.runner_id.strip():
            raise ValueError("runner_id must be non-empty")
        if self.generation < 0:
            raise ValueError("generation must be >= 0")
        for name in ("runner_capability_digest", "state_digest", "payload_digest"):
            _require_sha256(name, getattr(self, name))
        if self.previous_head_digest is not None:
            _require_sha256("previous_head_digest", self.previous_head_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def head_id(self) -> str:
        return stable_id("gedh", self)


@dataclass(frozen=True, slots=True)
class DurableCapacitySnapshot:
    head: DurableCapacityHead
    state: RunnerCapacityState
    schema_version: str = "ge.durable-capacity-snapshot.v1"

    def __post_init__(self) -> None:
        _require_schema(self.schema_version, "ge.durable-capacity-snapshot.v1")

    @property
    def digest(self) -> str:
        return sha256_digest(
            {
                "schema_version": self.schema_version,
                "head": asdict(self.head),
                "state": capacity_state_to_dict(self.state),
            }
        )


@dataclass(frozen=True, slots=True)
class RecoveredInFlightLease:
    lease_id: str
    lease_digest: str
    slot: int
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    previous_invocation_id: str | None
    previous_receipt_digest: str | None
    status: Literal["in_flight_unknown"] = "in_flight_unknown"
    schema_version: str = "ge.recovered-in-flight-lease.v1"

    def __post_init__(self) -> None:
        _require_schema(self.schema_version, "ge.recovered-in-flight-lease.v1")
        if self.status != RECOVERED_LEASE_STATUS:
            raise ValueError("recovered lease status must remain in_flight_unknown")
        if self.slot < 0:
            raise ValueError("slot must be >= 0")
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError("attempt ordinals must be >= 1")
        for name in ("lease_id", "session_id", "authorization_id", "invocation_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        _require_sha256("lease_digest", self.lease_digest)
        _require_sha256("authorization_digest", self.authorization_digest)
        if self.previous_receipt_digest is not None:
            _require_sha256("previous_receipt_digest", self.previous_receipt_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RestartRecoveryReport:
    durable_head_digest: str
    snapshot_digest: str
    state_digest: str
    generation: int
    status: RecoveryStatus
    active_leases: tuple[RecoveredInFlightLease, ...] = ()
    schema_version: str = "ge.restart-recovery-report.v1"

    def __post_init__(self) -> None:
        _require_schema(self.schema_version, "ge.restart-recovery-report.v1")
        for name in ("durable_head_digest", "snapshot_digest", "state_digest"):
            _require_sha256(name, getattr(self, name))
        if self.generation < 0:
            raise ValueError("generation must be >= 0")
        expected = "clean" if not self.active_leases else "reconciliation_required"
        if self.status != expected:
            raise ValueError("recovery status does not match active lease set")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _payload_digest(state: RunnerCapacityState) -> str:
    return sha256_digest(
        {
            "schema_version": "ge.durable-capacity-state-payload.v1",
            "state": capacity_state_to_dict(state),
        }
    )


def _state_digest_at_generation(state: RunnerCapacityState, generation: int) -> str | None:
    if generation < 0 or generation > state.generation:
        return None
    if generation == state.generation:
        return state.digest
    if generation == 0:
        return state.transitions[0].expected_state_digest if state.transitions else state.digest
    return state.transitions[generation].expected_state_digest


def _head_from_dict(data: dict) -> DurableCapacityHead:
    if data.get("schema_version") != "ge.durable-capacity-head.v1":
        raise DurableStateError("unsupported or missing durable capacity head schema")
    try:
        return DurableCapacityHead(
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            generation=int(data["generation"]),
            state_digest=str(data["state_digest"]),
            payload_digest=str(data["payload_digest"]),
            previous_head_digest=(
                str(data["previous_head_digest"]) if data.get("previous_head_digest") is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DurableStateError("invalid durable capacity head") from exc


def verify_durable_snapshot(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    *,
    expected_head_digest: str | None = None,
) -> bool:
    if snapshot.schema_version != "ge.durable-capacity-snapshot.v1":
        return False
    state, head = snapshot.state, snapshot.head
    if head.schema_version != "ge.durable-capacity-head.v1":
        return False
    if not verify_capacity_state(state, runner):
        return False
    if expected_head_digest is not None and head.digest != expected_head_digest:
        return False
    return (
        head.runner_id == runner.runner_id
        and head.runner_capability_digest == runner.digest
        and head.generation == state.generation
        and head.state_digest == state.digest
        and head.payload_digest == _payload_digest(state)
    )


def verify_durable_successor(
    previous: DurableCapacitySnapshot,
    current: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
) -> bool:
    if not verify_durable_snapshot(previous, runner) or not verify_durable_snapshot(current, runner):
        return False
    if current.head.previous_head_digest != previous.head.digest:
        return False
    if current.head.generation <= previous.head.generation:
        return False
    return _state_digest_at_generation(current.state, previous.head.generation) == previous.head.state_digest


def build_durable_snapshot(
    state: RunnerCapacityState,
    runner: RunnerCapabilities,
    *,
    previous: DurableCapacitySnapshot | None = None,
) -> DurableCapacitySnapshot:
    if not verify_capacity_state(state, runner):
        raise DurableStateError("capacity state does not replay for runner")
    previous_head_digest = None
    if previous is not None:
        if not verify_durable_snapshot(previous, runner):
            raise DurableStateError("previous durable snapshot is invalid")
        if state.generation <= previous.head.generation:
            raise DurableStateError("durable head update must advance generation")
        if _state_digest_at_generation(state, previous.head.generation) != previous.head.state_digest:
            raise DurableStateError("capacity state does not extend previous durable head")
        previous_head_digest = previous.head.digest

    snapshot = DurableCapacitySnapshot(
        head=DurableCapacityHead(
            runner_id=runner.runner_id,
            runner_capability_digest=runner.digest,
            generation=state.generation,
            state_digest=state.digest,
            payload_digest=_payload_digest(state),
            previous_head_digest=previous_head_digest,
        ),
        state=state,
    )
    if not verify_durable_snapshot(snapshot, runner):
        raise DurableStateError("constructed durable snapshot did not verify")
    if previous is not None and not verify_durable_successor(previous, snapshot, runner):
        raise DurableStateError("constructed durable snapshot is not a valid successor")
    return snapshot


def serialize_durable_snapshot(snapshot: DurableCapacitySnapshot) -> str:
    return canonical_json(
        {
            "schema_version": snapshot.schema_version,
            "head": asdict(snapshot.head),
            "state": capacity_state_to_dict(snapshot.state),
        }
    )


def load_durable_snapshot(
    payload: str | bytes,
    runner: RunnerCapabilities,
    *,
    expected_head_digest: str | None = None,
) -> DurableCapacitySnapshot:
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DurableStateError("durable snapshot is not valid UTF-8 JSON") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "ge.durable-capacity-snapshot.v1":
        raise DurableStateError("unsupported or missing durable snapshot schema")
    if not isinstance(data.get("head"), dict) or not isinstance(data.get("state"), dict):
        raise DurableStateError("durable snapshot requires head and state objects")
    try:
        snapshot = DurableCapacitySnapshot(
            head=_head_from_dict(data["head"]),
            state=capacity_state_from_dict(data["state"]),
        )
    except DurableCodecError as exc:
        raise DurableStateError("durable capacity state payload is invalid") from exc
    if not verify_durable_snapshot(snapshot, runner, expected_head_digest=expected_head_digest):
        raise DurableStateError("durable snapshot failed replay or head verification")
    return snapshot


def recover_after_restart(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    *,
    expected_head_digest: str | None = None,
) -> tuple[RunnerCapacityState, RestartRecoveryReport]:
    if not verify_durable_snapshot(snapshot, runner, expected_head_digest=expected_head_digest):
        raise DurableStateError("cannot recover from an invalid durable snapshot")
    recovered = tuple(
        RecoveredInFlightLease(
            lease_id=lease.lease_id,
            lease_digest=lease.digest,
            slot=lease.slot,
            session_id=lease.session_id,
            logical_attempt=lease.logical_attempt,
            authorization_id=lease.authorization_id,
            authorization_digest=lease.authorization_digest,
            invocation_id=lease.invocation_id,
            physical_attempt=lease.physical_attempt,
            previous_invocation_id=lease.previous_invocation_id,
            previous_receipt_digest=lease.previous_receipt_digest,
        )
        for lease in snapshot.state.active_leases
    )
    report = RestartRecoveryReport(
        durable_head_digest=snapshot.head.digest,
        snapshot_digest=snapshot.digest,
        state_digest=snapshot.state.digest,
        generation=snapshot.state.generation,
        status="clean" if not recovered else "reconciliation_required",
        active_leases=recovered,
    )
    return snapshot.state, report


def verify_restart_recovery(
    snapshot: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    report: RestartRecoveryReport,
) -> bool:
    if not verify_durable_snapshot(snapshot, runner):
        return False
    try:
        recovered_state, expected = recover_after_restart(snapshot, runner)
    except DurableStateError:
        return False
    return recovered_state == snapshot.state and report == expected
