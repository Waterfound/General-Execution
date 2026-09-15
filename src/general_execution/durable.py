from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest
from .capacity import (
    CapacityError,
    CapacityLease,
    CapacityRelease,
    CapacityTransition,
    RunnerCapacityState,
    initialize_capacity_state,
    verify_capacity_state,
)
from .models import RunnerCapabilities

SNAPSHOT_SCHEMA = "ge.capacity-snapshot.v1"
HEAD_SCHEMA = "ge.durable-capacity-head.v1"
RECOVERY_SCHEMA = "ge.restart-recovery.v1"
RECOVERED_LEASE_SCHEMA = "ge.recovered-lease.v1"

RecoveryLeaseStatus = Literal["in_flight_unresolved"]


class DurableCapacityError(CapacityError):
    pass


@dataclass(frozen=True, slots=True)
class DurableCapacityHead:
    runner_id: str
    runner_capability_digest: str
    state_digest: str
    generation: int
    snapshot_digest: str
    schema_version: str = HEAD_SCHEMA

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RecoveredLease:
    lease_id: str
    lease_digest: str
    runner_id: str
    slot: int
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    status: RecoveryLeaseStatus = "in_flight_unresolved"
    physical_outcome_fabricated: bool = False
    capacity_released: bool = False
    schema_version: str = RECOVERED_LEASE_SCHEMA

    def __post_init__(self) -> None:
        if self.status != "in_flight_unresolved":
            raise ValueError("recovered lease status must remain in_flight_unresolved")
        if self.physical_outcome_fabricated:
            raise ValueError("restart recovery cannot fabricate a physical outcome")
        if self.capacity_released:
            raise ValueError("restart recovery cannot release unresolved capacity")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RestartRecoveryReport:
    runner_id: str
    runner_capability_digest: str
    state_digest: str
    snapshot_digest: str
    generation: int
    active_lease_count: int
    unresolved_leases: tuple[RecoveredLease, ...]
    physical_outcomes_fabricated: int = 0
    capacity_releases_fabricated: int = 0
    schema_version: str = RECOVERY_SCHEMA

    def __post_init__(self) -> None:
        if self.active_lease_count != len(self.unresolved_leases):
            raise ValueError("active lease count must equal unresolved lease count")
        if self.physical_outcomes_fabricated != 0:
            raise ValueError("restart recovery cannot fabricate physical outcomes")
        if self.capacity_releases_fabricated != 0:
            raise ValueError("restart recovery cannot fabricate capacity releases")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _require_schema(data: Any, expected: str, label: str) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != expected:
        raise DurableCapacityError(f"unsupported {label} schema")


def _lease_from_dict(data: dict[str, Any]) -> CapacityLease:
    _require_schema(data, "ge.capacity-lease.v1", "capacity lease")
    try:
        return CapacityLease(**data)
    except (TypeError, ValueError) as exc:
        raise DurableCapacityError("invalid durable capacity lease") from exc


def _release_from_dict(data: dict[str, Any]) -> CapacityRelease:
    _require_schema(data, "ge.capacity-release.v1", "capacity release")
    try:
        return CapacityRelease(**data)
    except (TypeError, ValueError) as exc:
        raise DurableCapacityError("invalid durable capacity release") from exc


def _transition_from_dict(data: dict[str, Any]) -> CapacityTransition:
    _require_schema(data, "ge.capacity-transition.v1", "capacity transition")
    payload = dict(data)
    lease = payload.get("lease")
    release = payload.get("release")
    payload["lease"] = _lease_from_dict(lease) if isinstance(lease, dict) else None
    payload["release"] = _release_from_dict(release) if isinstance(release, dict) else None
    try:
        return CapacityTransition(**payload)
    except (TypeError, ValueError) as exc:
        raise DurableCapacityError("invalid durable capacity transition") from exc


def capacity_state_to_dict(state: RunnerCapacityState) -> dict[str, Any]:
    return asdict(state)


def capacity_state_from_dict(data: dict[str, Any]) -> RunnerCapacityState:
    _require_schema(data, "ge.runner-capacity-state.v1", "runner capacity state")
    payload = dict(data)
    transitions = payload.get("transitions")
    if not isinstance(transitions, (list, tuple)):
        raise DurableCapacityError("capacity state transitions must be a sequence")
    payload["transitions"] = tuple(_transition_from_dict(item) for item in transitions)
    try:
        return RunnerCapacityState(**payload)
    except (TypeError, ValueError) as exc:
        raise DurableCapacityError("invalid durable runner capacity state") from exc


def capacity_snapshot(state: RunnerCapacityState) -> dict[str, Any]:
    payload = {
        "schema_version": SNAPSHOT_SCHEMA,
        "state": capacity_state_to_dict(state),
        "state_digest": state.digest,
    }
    return {**payload, "snapshot_digest": sha256_digest(payload)}


def serialize_capacity_snapshot(state: RunnerCapacityState) -> str:
    return canonical_json(capacity_snapshot(state))


def deserialize_capacity_snapshot(snapshot_json: str, runner: RunnerCapabilities) -> tuple[RunnerCapacityState, str]:
    try:
        data = json.loads(snapshot_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise DurableCapacityError("durable capacity snapshot is not valid JSON") from exc
    if not isinstance(data, dict):
        raise DurableCapacityError("durable capacity snapshot must be an object")
    if set(data) != {"schema_version", "state", "state_digest", "snapshot_digest"}:
        raise DurableCapacityError("durable capacity snapshot fields mismatch")
    _require_schema(data, SNAPSHOT_SCHEMA, "capacity snapshot")
    snapshot_digest = data.get("snapshot_digest")
    if not isinstance(snapshot_digest, str):
        raise DurableCapacityError("capacity snapshot digest is required")
    payload = dict(data)
    del payload["snapshot_digest"]
    if sha256_digest(payload) != snapshot_digest:
        raise DurableCapacityError("capacity snapshot digest mismatch")
    state_data = data.get("state")
    if not isinstance(state_data, dict):
        raise DurableCapacityError("capacity snapshot state is required")
    state = capacity_state_from_dict(state_data)
    if state.digest != data.get("state_digest"):
        raise DurableCapacityError("capacity snapshot state digest mismatch")
    if not verify_capacity_state(state, runner):
        raise DurableCapacityError("capacity snapshot does not replay for runner")
    return state, snapshot_digest


def _head(state: RunnerCapacityState, snapshot_digest: str) -> DurableCapacityHead:
    return DurableCapacityHead(
        runner_id=state.runner_id,
        runner_capability_digest=state.runner_capability_digest,
        state_digest=state.digest,
        generation=state.generation,
        snapshot_digest=snapshot_digest,
    )


def _decode_head_row(row: tuple[Any, ...], runner: RunnerCapabilities) -> tuple[RunnerCapacityState, DurableCapacityHead]:
    capability_digest, state_digest, generation, stored_snapshot_digest, snapshot_json = row
    if capability_digest != runner.digest:
        raise DurableCapacityError("durable capacity head runner capabilities changed")
    state, snapshot_digest = deserialize_capacity_snapshot(snapshot_json, runner)
    if (
        state.digest != state_digest
        or state.generation != generation
        or snapshot_digest != stored_snapshot_digest
    ):
        raise DurableCapacityError("durable capacity head metadata mismatch")
    return state, _head(state, snapshot_digest)


class SqliteCapacityHeadStore:
    """Durable one-head-per-runner store with transactional compare-and-swap."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS capacity_heads (
                    runner_id TEXT PRIMARY KEY,
                    runner_capability_digest TEXT NOT NULL,
                    state_digest TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )

    def initialize(self, runner: RunnerCapabilities, state: RunnerCapacityState | None = None) -> DurableCapacityHead:
        state = state or initialize_capacity_state(runner)
        if not verify_capacity_state(state, runner):
            raise DurableCapacityError("initial durable capacity state does not replay for runner")
        snapshot_json = serialize_capacity_snapshot(state)
        _, snapshot_digest = deserialize_capacity_snapshot(snapshot_json, runner)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT runner_capability_digest, state_digest, generation, snapshot_digest, snapshot_json
                FROM capacity_heads WHERE runner_id = ?
                """,
                (runner.runner_id,),
            ).fetchone()
            if row is not None:
                existing, existing_head = _decode_head_row(row, runner)
                if existing != state:
                    raise DurableCapacityError("durable capacity head already exists with different state")
                connection.commit()
                return existing_head
            connection.execute(
                """
                INSERT INTO capacity_heads
                    (runner_id, runner_capability_digest, state_digest, generation, snapshot_digest, snapshot_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    state.runner_id,
                    state.runner_capability_digest,
                    state.digest,
                    state.generation,
                    snapshot_digest,
                    snapshot_json,
                ),
            )
            connection.commit()
            return _head(state, snapshot_digest)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, runner: RunnerCapabilities) -> tuple[RunnerCapacityState, DurableCapacityHead]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT runner_capability_digest, state_digest, generation, snapshot_digest, snapshot_json
                FROM capacity_heads WHERE runner_id = ?
                """,
                (runner.runner_id,),
            ).fetchone()
        if row is None:
            raise DurableCapacityError("durable capacity head does not exist")
        return _decode_head_row(row, runner)

    def commit(
        self,
        runner: RunnerCapabilities,
        expected_state_digest: str,
        new_state: RunnerCapacityState,
    ) -> DurableCapacityHead:
        if not verify_capacity_state(new_state, runner):
            raise DurableCapacityError("candidate durable capacity state does not replay for runner")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT runner_capability_digest, state_digest, generation, snapshot_digest, snapshot_json
                FROM capacity_heads WHERE runner_id = ?
                """,
                (runner.runner_id,),
            ).fetchone()
            if row is None:
                raise DurableCapacityError("durable capacity head does not exist")
            current_state, _ = _decode_head_row(row, runner)
            if current_state.digest != expected_state_digest:
                raise DurableCapacityError("stale durable capacity head")
            if new_state.generation != current_state.generation + 1:
                raise DurableCapacityError("durable capacity commit must advance exactly one generation")
            if new_state.previous_state_digest != current_state.digest:
                raise DurableCapacityError("durable capacity commit predecessor mismatch")
            if new_state.transitions[:-1] != current_state.transitions:
                raise DurableCapacityError("durable capacity commit must extend the canonical transition history")

            snapshot_json = serialize_capacity_snapshot(new_state)
            _, snapshot_digest = deserialize_capacity_snapshot(snapshot_json, runner)
            cursor = connection.execute(
                """
                UPDATE capacity_heads
                SET runner_capability_digest = ?, state_digest = ?, generation = ?, snapshot_digest = ?, snapshot_json = ?
                WHERE runner_id = ? AND state_digest = ? AND generation = ?
                """,
                (
                    new_state.runner_capability_digest,
                    new_state.digest,
                    new_state.generation,
                    snapshot_digest,
                    snapshot_json,
                    runner.runner_id,
                    expected_state_digest,
                    current_state.generation,
                ),
            )
            if cursor.rowcount != 1:
                raise DurableCapacityError("durable capacity compare-and-swap failed")
            connection.commit()
            return _head(new_state, snapshot_digest)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _recovery_report(state: RunnerCapacityState, head: DurableCapacityHead) -> RestartRecoveryReport:
    unresolved = tuple(
        RecoveredLease(
            lease_id=lease.lease_id,
            lease_digest=lease.digest,
            runner_id=lease.runner_id,
            slot=lease.slot,
            session_id=lease.session_id,
            logical_attempt=lease.logical_attempt,
            authorization_id=lease.authorization_id,
            authorization_digest=lease.authorization_digest,
            invocation_id=lease.invocation_id,
            physical_attempt=lease.physical_attempt,
        )
        for lease in state.active_leases
    )
    return RestartRecoveryReport(
        runner_id=state.runner_id,
        runner_capability_digest=state.runner_capability_digest,
        state_digest=state.digest,
        snapshot_digest=head.snapshot_digest,
        generation=state.generation,
        active_lease_count=len(unresolved),
        unresolved_leases=unresolved,
    )


def verify_restart_recovery(
    state: RunnerCapacityState,
    head: DurableCapacityHead,
    report: RestartRecoveryReport,
) -> bool:
    if state.digest != head.state_digest or state.generation != head.generation:
        return False
    if state.runner_id != head.runner_id or state.runner_capability_digest != head.runner_capability_digest:
        return False
    return report == _recovery_report(state, head)


def recover_capacity_after_restart(
    store: SqliteCapacityHeadStore,
    runner: RunnerCapabilities,
) -> tuple[RunnerCapacityState, RestartRecoveryReport]:
    state, head = store.load(runner)
    report = _recovery_report(state, head)
    if not verify_restart_recovery(state, head, report):
        raise DurableCapacityError("restart recovery report does not reproduce")
    return state, report
