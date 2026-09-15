from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .canonical import sha256_digest
from .durable import DurableCapacitySnapshot, load_durable_snapshot, verify_durable_snapshot
from .models import ExecutionSession, RunnerCapabilities
from .persistence import PersistenceIntegrityError, SQLiteDurableHeadStore
from .result_handoff import LogicalResultSubmission, PendingLogicalResult
from .session_persistence import (
    SQLiteSessionRegistry,
    SessionPersistenceConflict,
    SessionPersistenceIntegrityError,
)
from .session_registry import SessionRegistryTransition

CoherenceStatus = Literal["coherent", "recovery_required", "legacy_untracked", "inconsistent"]


@dataclass(frozen=True, slots=True)
class ExecutionCoherenceReport:
    runner_id: str
    session_id: str
    logical_attempt: int | None
    session_state: str | None
    capacity_head_digest: str | None
    capacity_transition_count: int
    active_lease_ids: tuple[str, ...]
    pending_id: str | None
    submission_id: str | None
    status: CoherenceStatus
    findings: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    schema_version: str = "ge.execution-coherence-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.execution-coherence-report.v1":
            raise ValueError("unsupported execution coherence report schema")
        if not self.runner_id or not self.runner_id.strip():
            raise ValueError("runner_id must be non-empty")
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must be non-empty")
        if self.logical_attempt is not None and self.logical_attempt < 1:
            raise ValueError("logical_attempt must be >= 1")
        if self.capacity_transition_count < 0:
            raise ValueError("capacity_transition_count must be >= 0")
        if self.status not in {"coherent", "recovery_required", "legacy_untracked", "inconsistent"}:
            raise ValueError("unsupported coherence status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _capacity_transition_identity(transition):
    item = transition.lease if transition.kind == "reserve" else transition.release
    if item is None:
        return None
    return item.session_id, item.logical_attempt


def _session_capacity_history(snapshot: DurableCapacitySnapshot, session_id: str, logical_attempt: int | None):
    return tuple(
        transition
        for transition in snapshot.state.transitions
        if (identity := _capacity_transition_identity(transition)) is not None
        and identity[0] == session_id
        and (logical_attempt is None or identity[1] == logical_attempt)
    )


def _history_has_revocation_release(history) -> bool:
    return any(
        transition.kind == "release"
        and transition.release is not None
        and transition.release.release_kind == "session_revoked"
        for transition in history
    )


def _history_has_completed_release(history) -> bool:
    return any(
        transition.kind == "release"
        and transition.release is not None
        and transition.release.release_kind == "terminal_outcome"
        and transition.release.transport_status == "completed"
        for transition in history
    )


def assess_execution_coherence(
    runner: RunnerCapabilities,
    session_id: str,
    *,
    session: ExecutionSession | None,
    capacity_snapshot: DurableCapacitySnapshot | None,
    pending: PendingLogicalResult | None,
    submission: LogicalResultSubmission | None,
    raw_pending_exists: bool = False,
    raw_submission_exists: bool = False,
) -> ExecutionCoherenceReport:
    capacity_head_digest = capacity_snapshot.head.digest if capacity_snapshot is not None else None
    logical_attempt = session.attempt if session is not None else None
    if capacity_snapshot is not None and not verify_durable_snapshot(capacity_snapshot, runner):
        return ExecutionCoherenceReport(
            runner_id=runner.runner_id,
            session_id=session_id,
            logical_attempt=logical_attempt,
            session_state=session.state if session else None,
            capacity_head_digest=capacity_head_digest,
            capacity_transition_count=0,
            active_lease_ids=(),
            pending_id=pending.pending_id if pending else None,
            submission_id=submission.submission_id if submission else None,
            status="inconsistent",
            findings=("INVALID_DURABLE_CAPACITY_SNAPSHOT",),
        )

    leases = ()
    capacity_history = ()
    if capacity_snapshot is not None:
        capacity_history = _session_capacity_history(capacity_snapshot, session_id, logical_attempt)
        leases = tuple(
            lease
            for lease in capacity_snapshot.state.active_leases
            if lease.session_id == session_id
            and (session is None or lease.logical_attempt == session.attempt)
        )
    lease_ids = tuple(lease.lease_id for lease in leases)
    capacity_transition_count = len(capacity_history)
    has_revocation_release = _history_has_revocation_release(capacity_history)
    has_completed_release = _history_has_completed_release(capacity_history)

    if session is None:
        if capacity_history or raw_pending_exists or raw_submission_exists:
            return ExecutionCoherenceReport(
                runner_id=runner.runner_id,
                session_id=session_id,
                logical_attempt=None,
                session_state=None,
                capacity_head_digest=capacity_head_digest,
                capacity_transition_count=capacity_transition_count,
                active_lease_ids=lease_ids,
                pending_id=pending.pending_id if pending else None,
                submission_id=submission.submission_id if submission else None,
                status="legacy_untracked",
                findings=("SESSION_REGISTRY_MISSING_FOR_EXISTING_EXECUTION_STATE",),
                required_actions=("KEEP_LEGACY_STATE_UNSYNTHESIZED",),
            )
        return ExecutionCoherenceReport(
            runner_id=runner.runner_id,
            session_id=session_id,
            logical_attempt=None,
            session_state=None,
            capacity_head_digest=capacity_head_digest,
            capacity_transition_count=0,
            active_lease_ids=(),
            pending_id=None,
            submission_id=None,
            status="coherent",
        )

    findings: list[str] = []
    state = session.state
    pending_id = pending.pending_id if pending else None
    submission_id = submission.submission_id if submission else None

    if raw_submission_exists and not raw_pending_exists:
        findings.append("ORPHAN_RESULT_SUBMISSION")
    if raw_pending_exists and pending is None:
        findings.append("UNREADABLE_PENDING_RESULT")
    if raw_submission_exists and submission is None and pending is not None:
        findings.append("UNREADABLE_RESULT_SUBMISSION")

    if state == "bound":
        if pending is not None or submission is not None or raw_pending_exists or raw_submission_exists:
            findings.append("BOUND_SESSION_HAS_RESULT_HANDOFF_STATE")
        if has_completed_release and not raw_pending_exists:
            findings.append("COMPLETED_RELEASE_MISSING_DURABLE_RESULT_HANDOFF")
        if capacity_history:
            if findings:
                findings.append("BOUND_SESSION_HAS_PHYSICAL_HISTORY")
            else:
                return ExecutionCoherenceReport(
                    runner_id=runner.runner_id,
                    session_id=session_id,
                    logical_attempt=session.attempt,
                    session_state=state,
                    capacity_head_digest=capacity_head_digest,
                    capacity_transition_count=capacity_transition_count,
                    active_lease_ids=lease_ids,
                    pending_id=None,
                    submission_id=None,
                    status="recovery_required",
                    findings=("BOUND_SESSION_HAS_PHYSICAL_HISTORY",),
                    required_actions=("COMMIT_START_SESSION_TRANSITION",),
                )

    elif state == "running":
        if leases and (pending is not None or submission is not None or raw_pending_exists or raw_submission_exists):
            findings.append("RUNNING_SESSION_HAS_ACTIVE_CAPACITY_AND_RESULT_STATE")
        if has_revocation_release:
            if pending is not None or submission is not None or raw_pending_exists or raw_submission_exists:
                findings.append("REVOCATION_RELEASE_HAS_RESULT_HANDOFF_STATE")
            elif not findings:
                return ExecutionCoherenceReport(
                    runner_id=runner.runner_id,
                    session_id=session_id,
                    logical_attempt=session.attempt,
                    session_state=state,
                    capacity_head_digest=capacity_head_digest,
                    capacity_transition_count=capacity_transition_count,
                    active_lease_ids=lease_ids,
                    pending_id=None,
                    submission_id=None,
                    status="recovery_required",
                    findings=("REVOCATION_RELEASE_NOT_YET_IN_SESSION_REGISTRY",),
                    required_actions=("COMMIT_REVOKE_SESSION_TRANSITION",),
                )
        if has_completed_release and not raw_pending_exists:
            findings.append("COMPLETED_RELEASE_MISSING_DURABLE_RESULT_HANDOFF")
        if not findings and submission is not None:
            if submission.submitted_session.session_id != session.session_id or submission.submitted_session.attempt != session.attempt:
                findings.append("RESULT_SUBMISSION_SESSION_MISMATCH")
            else:
                return ExecutionCoherenceReport(
                    runner_id=runner.runner_id,
                    session_id=session_id,
                    logical_attempt=session.attempt,
                    session_state=state,
                    capacity_head_digest=capacity_head_digest,
                    capacity_transition_count=capacity_transition_count,
                    active_lease_ids=lease_ids,
                    pending_id=pending_id,
                    submission_id=submission_id,
                    status="recovery_required",
                    findings=("RESULT_SUBMISSION_NOT_YET_IN_SESSION_REGISTRY",),
                    required_actions=("COMMIT_SUBMIT_RESULT_SESSION_TRANSITION",),
                )
        elif not findings and pending is not None:
            return ExecutionCoherenceReport(
                runner_id=runner.runner_id,
                session_id=session_id,
                logical_attempt=session.attempt,
                session_state=state,
                capacity_head_digest=capacity_head_digest,
                capacity_transition_count=capacity_transition_count,
                active_lease_ids=lease_ids,
                pending_id=pending_id,
                submission_id=None,
                status="recovery_required",
                findings=("PENDING_LOGICAL_RESULT_NOT_SUBMITTED",),
                required_actions=("PREPARE_AND_COMMIT_LOGICAL_RESULT_SUBMISSION",),
            )

    elif state == "revoked":
        if leases:
            findings.append("REVOKED_SESSION_HAS_ACTIVE_CAPACITY")
        if pending is not None or submission is not None or raw_pending_exists or raw_submission_exists:
            findings.append("REVOKED_SESSION_HAS_RESULT_HANDOFF_STATE")
        if has_completed_release:
            findings.append("REVOKED_SESSION_HAS_COMPLETED_OUTCOME")

    elif state == "result_submitted":
        if leases:
            findings.append("RESULT_SUBMITTED_SESSION_HAS_ACTIVE_CAPACITY")
        if has_revocation_release:
            findings.append("RESULT_SUBMITTED_SESSION_HAS_REVOCATION_RELEASE")
        if pending is None:
            findings.append("RESULT_SUBMITTED_SESSION_MISSING_PENDING_RESULT")
        if submission is None:
            findings.append("RESULT_SUBMITTED_SESSION_MISSING_SUBMISSION")
        if submission is not None and submission.submitted_session != session:
            findings.append("RESULT_SUBMITTED_SESSION_DOES_NOT_MATCH_DURABLE_SUBMISSION")
        if pending is not None and session.result_digest != pending.result.digest:
            findings.append("RESULT_SUBMITTED_DIGEST_MISMATCH")

    else:
        findings.append("UNSUPPORTED_SESSION_STATE")

    if findings:
        return ExecutionCoherenceReport(
            runner_id=runner.runner_id,
            session_id=session_id,
            logical_attempt=session.attempt,
            session_state=state,
            capacity_head_digest=capacity_head_digest,
            capacity_transition_count=capacity_transition_count,
            active_lease_ids=lease_ids,
            pending_id=pending_id,
            submission_id=submission_id,
            status="inconsistent",
            findings=tuple(findings),
        )

    return ExecutionCoherenceReport(
        runner_id=runner.runner_id,
        session_id=session_id,
        logical_attempt=session.attempt,
        session_state=state,
        capacity_head_digest=capacity_head_digest,
        capacity_transition_count=capacity_transition_count,
        active_lease_ids=lease_ids,
        pending_id=pending_id,
        submission_id=submission_id,
        status="coherent",
    )


class CoherentSQLiteSessionRegistry(SQLiteSessionRegistry):
    """v0.0.10 Session registry with atomic cross-layer history guards."""

    def _cross_layer_guard_locked(
        self,
        connection: sqlite3.Connection,
        transition: SessionRegistryTransition,
        runner: RunnerCapabilities,
    ) -> None:
        super()._cross_layer_guard_locked(connection, transition, runner)
        reference = transition.source_session or transition.target_session
        row = connection.execute(
            "SELECT head_digest, generation, snapshot_digest, snapshot_payload "
            "FROM ge_durable_heads WHERE runner_id = ?",
            (runner.runner_id,),
        ).fetchone()
        if row is None:
            return
        try:
            snapshot = load_durable_snapshot(
                row["snapshot_payload"],
                runner,
                expected_head_digest=row["head_digest"],
            )
        except ValueError as exc:
            raise SessionPersistenceIntegrityError(
                "durable capacity head is invalid during coherent Session transition"
            ) from exc
        if snapshot.head.generation != row["generation"] or snapshot.digest != row["snapshot_digest"]:
            raise SessionPersistenceIntegrityError(
                "durable capacity metadata does not match snapshot during coherent Session transition"
            )
        history = _session_capacity_history(snapshot, reference.session_id, reference.attempt)
        if transition.kind == "register" and history:
            raise SessionPersistenceConflict(
                "cannot register a new logical Session over existing physical capacity history"
            )
        if transition.kind in {"start", "revoke"} and _history_has_completed_release(history):
            pending_exists = connection.execute(
                "SELECT 1 FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, reference.session_id, reference.attempt),
            ).fetchone() is not None
            if not pending_exists:
                raise SessionPersistenceConflict(
                    "completed physical release lacks durable result handoff; Session transition fails closed"
                )
        if transition.kind == "revoke" and _history_has_completed_release(history):
            raise SessionPersistenceConflict(
                "Session with completed physical outcome cannot be canonically revoked"
            )


def inspect_sqlite_execution_coherence(
    path: str | Path,
    runner: RunnerCapabilities,
    session_id: str,
) -> ExecutionCoherenceReport:
    durable = SQLiteDurableHeadStore(path)
    registry = SQLiteSessionRegistry(path)
    session = registry.load_current(runner, session_id)
    capacity_snapshot = durable.load_current(runner)

    pending = None
    submission = None
    raw_pending_exists = False
    raw_submission_exists = False
    logical_attempt = session.attempt if session is not None else None

    with sqlite3.connect(str(path)) as connection:
        if logical_attempt is None:
            raw_pending_exists = connection.execute(
                "SELECT 1 FROM ge_pending_results WHERE runner_id = ? AND session_id = ? LIMIT 1",
                (runner.runner_id, session_id),
            ).fetchone() is not None
            raw_submission_exists = connection.execute(
                "SELECT 1 FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? LIMIT 1",
                (runner.runner_id, session_id),
            ).fetchone() is not None
        else:
            raw_pending_exists = connection.execute(
                "SELECT 1 FROM ge_pending_results WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, session_id, logical_attempt),
            ).fetchone() is not None
            raw_submission_exists = connection.execute(
                "SELECT 1 FROM ge_result_submissions WHERE runner_id = ? AND session_id = ? AND logical_attempt = ?",
                (runner.runner_id, session_id, logical_attempt),
            ).fetchone() is not None

    if session is not None:
        if raw_pending_exists:
            try:
                pending = durable.load_pending_result(runner, session_id, session.attempt)
            except PersistenceIntegrityError:
                pending = None
        if raw_submission_exists and pending is not None:
            try:
                submission = durable.load_result_submission(runner, session_id, session.attempt)
            except PersistenceIntegrityError:
                submission = None

    return assess_execution_coherence(
        runner,
        session_id,
        session=session,
        capacity_snapshot=capacity_snapshot,
        pending=pending,
        submission=submission,
        raw_pending_exists=raw_pending_exists,
        raw_submission_exists=raw_submission_exists,
    )
