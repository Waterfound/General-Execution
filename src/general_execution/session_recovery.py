from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest
from .capacity import CapacityLease, CapacityRelease, CapacityTransition, RunnerCapacityState, verify_capacity_state
from .dispatch import DispatchIntentState
from .durable import DurableCapacityError, SqliteCapacityHeadStore
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .observed import DurableObservedOutcome, SqliteDurableObservedOutcomeStore
from .physical import verify_physical_outcome
from .planner import verify_plan
from .session import bind_session, revoke_session, start_session, submit_result

ProjectionStatus = Literal["coherent", "recovery_required", "legacy_untracked", "inconsistent"]
RecoveryAction = Literal[
    "none",
    "start_session",
    "prepare_dispatch_intent",
    "begin_submission",
    "reconcile_provider",
    "release_observed_capacity",
]
ProjectedState = Literal["bound", "running", "revoked", "result_submitted"]


class SessionRecoveryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SessionRecoveryProjection:
    runner_id: str
    session_id: str
    logical_attempt: int
    status: ProjectionStatus
    projected_state: ProjectedState
    projected_session: ExecutionSession
    projected_session_digest: str
    capacity_state_digest: str
    capacity_generation: int
    capacity_head_digest: str
    physical_transition_count: int
    latest_physical_attempt: int | None
    active_lease_id: str | None
    dispatch_intent_id: str | None
    dispatch_status: str | None
    durable_outcome_digest: str | None
    last_release_digest: str | None
    retry_eligible: bool
    recovery_action: RecoveryAction
    finding: str | None = None
    schema_version: str = "ge.session-recovery-projection.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.session-recovery-projection.v1":
            raise ValueError("unsupported Session recovery projection schema")
        if self.logical_attempt < 1:
            raise ValueError("logical_attempt must be >= 1")
        if self.capacity_generation < 0 or self.physical_transition_count < 0:
            raise ValueError("capacity generation and transition count must be >= 0")
        if self.latest_physical_attempt is not None and self.latest_physical_attempt < 1:
            raise ValueError("latest_physical_attempt must be >= 1")
        if self.status not in {"coherent", "recovery_required", "legacy_untracked", "inconsistent"}:
            raise ValueError("unsupported Session recovery status")
        if self.projected_state not in {"bound", "running", "revoked", "result_submitted"}:
            raise ValueError("unsupported projected Session state")
        if self.recovery_action not in {
            "none",
            "start_session",
            "prepare_dispatch_intent",
            "begin_submission",
            "reconcile_provider",
            "release_observed_capacity",
        }:
            raise ValueError("unsupported Session recovery action")
        if self.projected_session.session_id != self.session_id:
            raise ValueError("projected Session identity mismatch")
        if self.projected_session.attempt != self.logical_attempt:
            raise ValueError("projected Session attempt mismatch")
        if self.projected_session.state != self.projected_state:
            raise ValueError("projected Session state mismatch")
        if sha256_digest(self.projected_session) != self.projected_session_digest:
            raise ValueError("projected Session digest mismatch")
        for name in ("projected_session_digest", "capacity_state_digest", "capacity_head_digest"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _transition_identity(transition: CapacityTransition):
    item = transition.lease if transition.kind == "reserve" else transition.release
    if item is None:
        return None
    return item.session_id, item.logical_attempt, item.physical_attempt


def _session_transitions(
    state: RunnerCapacityState,
    session_id: str,
    logical_attempt: int,
) -> tuple[CapacityTransition, ...]:
    return tuple(
        transition
        for transition in state.transitions
        if (identity := _transition_identity(transition)) is not None
        and identity[0] == session_id
        and identity[1] == logical_attempt
    )


def _session_active_leases(
    state: RunnerCapacityState,
    session_id: str,
    logical_attempt: int,
) -> tuple[CapacityLease, ...]:
    return tuple(
        lease
        for lease in state.active_leases
        if lease.session_id == session_id and lease.logical_attempt == logical_attempt
    )


def _dispatch_states(
    store: SqliteDurableObservedOutcomeStore,
    runner_id: str,
    session_id: str,
    logical_attempt: int,
) -> tuple[DispatchIntentState, ...]:
    return tuple(
        state
        for state in store.load_for_runner(runner_id)
        if state.intent.session_id == session_id and state.intent.logical_attempt == logical_attempt
    )


def _dispatch_for_lease(states: tuple[DispatchIntentState, ...], lease: CapacityLease) -> DispatchIntentState | None:
    matches = [
        state
        for state in states
        if state.intent.lease_id == lease.lease_id
        and state.intent.lease_digest == lease.digest
        and state.intent.authorization_id == lease.authorization_id
        and state.intent.authorization_digest == lease.authorization_digest
        and state.intent.invocation_id == lease.invocation_id
        and state.intent.physical_attempt == lease.physical_attempt
    ]
    if len(matches) > 1:
        raise SessionRecoveryError("one capacity lease maps to multiple durable dispatch intents")
    return matches[0] if matches else None


def _dispatch_for_release(states: tuple[DispatchIntentState, ...], release: CapacityRelease) -> DispatchIntentState | None:
    matches = [
        state
        for state in states
        if state.intent.lease_id == release.lease_id
        and state.intent.lease_digest == release.lease_digest
        and state.intent.authorization_id == release.authorization_id
        and state.intent.authorization_digest == release.authorization_digest
        and state.intent.invocation_id == release.invocation_id
        and state.intent.physical_attempt == release.physical_attempt
    ]
    if len(matches) > 1:
        raise SessionRecoveryError("one capacity release maps to multiple durable dispatch intents")
    return matches[0] if matches else None


def _load_release_outcome(
    store: SqliteDurableObservedOutcomeStore,
    dispatch_state: DispatchIntentState,
    release: CapacityRelease,
) -> DurableObservedOutcome:
    if dispatch_state.status != "observed":
        raise SessionRecoveryError("terminal capacity release is not backed by observed durable dispatch state")
    record = store.load_observed_outcome(dispatch_state.intent.intent_id)
    if (
        record.lease_id != release.lease_id
        or record.lease_digest != release.lease_digest
        or record.authorization_id != release.authorization_id
        or record.authorization_digest != release.authorization_digest
        or record.invocation_id != release.invocation_id
        or record.physical_attempt != release.physical_attempt
        or record.outcome_digest != release.outcome_digest
        or record.receipt_digest != release.receipt_digest
        or record.transport_status != release.transport_status
    ):
        raise SessionRecoveryError("durable observed outcome does not match terminal capacity release")
    return record


def _projection(
    *,
    runner: RunnerCapabilities,
    session: ExecutionSession,
    status: ProjectionStatus,
    capacity_state: RunnerCapacityState,
    capacity_head_digest: str,
    physical_transition_count: int,
    latest_physical_attempt: int | None,
    active_lease_id: str | None = None,
    dispatch_state: DispatchIntentState | None = None,
    durable_outcome_digest: str | None = None,
    last_release_digest: str | None = None,
    retry_eligible: bool = False,
    recovery_action: RecoveryAction = "none",
    finding: str | None = None,
) -> SessionRecoveryProjection:
    return SessionRecoveryProjection(
        runner_id=runner.runner_id,
        session_id=session.session_id,
        logical_attempt=session.attempt,
        status=status,
        projected_state=session.state,
        projected_session=session,
        projected_session_digest=sha256_digest(session),
        capacity_state_digest=capacity_state.digest,
        capacity_generation=capacity_state.generation,
        capacity_head_digest=capacity_head_digest,
        physical_transition_count=physical_transition_count,
        latest_physical_attempt=latest_physical_attempt,
        active_lease_id=active_lease_id,
        dispatch_intent_id=dispatch_state.intent.intent_id if dispatch_state is not None else None,
        dispatch_status=dispatch_state.status if dispatch_state is not None else None,
        durable_outcome_digest=durable_outcome_digest,
        last_release_digest=last_release_digest,
        retry_eligible=retry_eligible,
        recovery_action=recovery_action,
        finding=finding,
    )


def project_session_after_restart(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    runner: RunnerCapabilities,
    capacity_store: SqliteCapacityHeadStore,
    dispatch_store: SqliteDurableObservedOutcomeStore,
    *,
    attempt: int = 1,
) -> SessionRecoveryProjection:
    if attempt < 1:
        raise SessionRecoveryError("logical Session attempt must be >= 1")
    if not verify_plan(spec, registry, plan):
        raise SessionRecoveryError("dispatch plan does not reproduce")
    bound = bind_session(spec, registry, plan, attempt=attempt)
    if bound.runner_id != runner.runner_id or bound.runner_capability_digest != runner.digest:
        raise SessionRecoveryError("logical Session is not bound to supplied runner")
    running = start_session(bound)

    try:
        capacity_state, capacity_head = capacity_store.load(runner)
    except DurableCapacityError as exc:
        raise SessionRecoveryError("canonical durable capacity head is unavailable") from exc
    if not verify_capacity_state(capacity_state, runner):
        raise SessionRecoveryError("canonical durable capacity state does not replay")

    transitions = _session_transitions(capacity_state, bound.session_id, attempt)
    active = _session_active_leases(capacity_state, bound.session_id, attempt)
    if len(active) > 1:
        raise SessionRecoveryError("logical Session has multiple active capacity leases")
    latest_physical_attempt = max(
        (identity[2] for transition in transitions if (identity := _transition_identity(transition)) is not None),
        default=None,
    )
    dispatch_states = _dispatch_states(dispatch_store, runner.runner_id, bound.session_id, attempt)

    if not transitions:
        if dispatch_states:
            return _projection(
                runner=runner,
                session=bound,
                status="inconsistent",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=0,
                latest_physical_attempt=None,
                finding="DISPATCH_WITHOUT_CAPACITY_HISTORY",
            )
        return _projection(
            runner=runner,
            session=bound,
            status="recovery_required",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=0,
            latest_physical_attempt=None,
            recovery_action="start_session",
            finding="NO_DURABLE_PHYSICAL_HISTORY",
        )

    if active:
        lease = active[0]
        dispatch_state = _dispatch_for_lease(dispatch_states, lease)
        if dispatch_state is None:
            return _projection(
                runner=runner,
                session=running,
                status="recovery_required",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=len(transitions),
                latest_physical_attempt=latest_physical_attempt,
                active_lease_id=lease.lease_id,
                recovery_action="prepare_dispatch_intent",
                finding="ACTIVE_LEASE_WITHOUT_DURABLE_DISPATCH_INTENT",
            )
        if dispatch_state.status == "prepared":
            return _projection(
                runner=runner,
                session=running,
                status="recovery_required",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=len(transitions),
                latest_physical_attempt=latest_physical_attempt,
                active_lease_id=lease.lease_id,
                dispatch_state=dispatch_state,
                recovery_action="begin_submission",
                finding="DURABLE_DISPATCH_PREPARED",
            )
        if dispatch_state.status == "submission_unknown":
            return _projection(
                runner=runner,
                session=running,
                status="recovery_required",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=len(transitions),
                latest_physical_attempt=latest_physical_attempt,
                active_lease_id=lease.lease_id,
                dispatch_state=dispatch_state,
                recovery_action="reconcile_provider",
                finding="DURABLE_DISPATCH_SUBMISSION_UNKNOWN",
            )
        if dispatch_state.status == "observed":
            try:
                record = dispatch_store.load_observed_outcome(dispatch_state.intent.intent_id)
            except Exception as exc:
                raise SessionRecoveryError("observed dispatch outcome is not durably recoverable") from exc
            if record.lease_id != lease.lease_id or record.lease_digest != lease.digest:
                raise SessionRecoveryError("durable observed outcome no longer matches active lease")
            return _projection(
                runner=runner,
                session=running,
                status="recovery_required",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=len(transitions),
                latest_physical_attempt=latest_physical_attempt,
                active_lease_id=lease.lease_id,
                dispatch_state=dispatch_state,
                durable_outcome_digest=record.outcome_digest,
                recovery_action="release_observed_capacity",
                finding="OBSERVED_OUTCOME_CAPACITY_RELEASE_PENDING",
            )
        raise SessionRecoveryError("unsupported durable dispatch state")

    releases = [transition.release for transition in transitions if transition.kind == "release" and transition.release is not None]
    if not releases:
        return _projection(
            runner=runner,
            session=running,
            status="inconsistent",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=len(transitions),
            latest_physical_attempt=latest_physical_attempt,
            finding="PHYSICAL_HISTORY_HAS_NO_ACTIVE_LEASE_OR_RELEASE",
        )
    last_release = releases[-1]

    if last_release.release_kind == "session_revoked":
        revoked = revoke_session(running)
        if last_release.revoked_session_digest != sha256_digest(revoked):
            return _projection(
                runner=runner,
                session=running,
                status="inconsistent",
                capacity_state=capacity_state,
                capacity_head_digest=capacity_head.digest,
                physical_transition_count=len(transitions),
                latest_physical_attempt=latest_physical_attempt,
                last_release_digest=last_release.digest,
                finding="REVOCATION_RELEASE_SESSION_DIGEST_MISMATCH",
            )
        return _projection(
            runner=runner,
            session=revoked,
            status="coherent",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=len(transitions),
            latest_physical_attempt=latest_physical_attempt,
            last_release_digest=last_release.digest,
        )

    if last_release.release_kind != "terminal_outcome":
        raise SessionRecoveryError("unsupported capacity release kind")

    dispatch_state = _dispatch_for_release(dispatch_states, last_release)
    if dispatch_state is None or dispatch_state.status != "observed":
        return _projection(
            runner=runner,
            session=running,
            status="legacy_untracked",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=len(transitions),
            latest_physical_attempt=latest_physical_attempt,
            last_release_digest=last_release.digest,
            retry_eligible=False,
            finding="TERMINAL_RELEASE_LACKS_RESTART_COMPLETE_DURABLE_OUTCOME",
        )
    try:
        record = _load_release_outcome(dispatch_store, dispatch_state, last_release)
    except Exception as exc:
        raise SessionRecoveryError("terminal release durable outcome failed verification") from exc
    outcome = record.outcome
    if not verify_physical_outcome(spec, registry, plan, running, runner, outcome):
        return _projection(
            runner=runner,
            session=running,
            status="inconsistent",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=len(transitions),
            latest_physical_attempt=latest_physical_attempt,
            dispatch_state=dispatch_state,
            durable_outcome_digest=record.outcome_digest,
            last_release_digest=last_release.digest,
            finding="DURABLE_OUTCOME_EXECUTION_CONTEXT_MISMATCH",
        )

    if last_release.transport_status == "completed":
        if outcome.result is None:
            raise SessionRecoveryError("completed terminal release has no durable logical result")
        submitted = submit_result(running, outcome.result)
        return _projection(
            runner=runner,
            session=submitted,
            status="coherent",
            capacity_state=capacity_state,
            capacity_head_digest=capacity_head.digest,
            physical_transition_count=len(transitions),
            latest_physical_attempt=latest_physical_attempt,
            dispatch_state=dispatch_state,
            durable_outcome_digest=record.outcome_digest,
            last_release_digest=last_release.digest,
        )

    if outcome.result is not None:
        raise SessionRecoveryError("failed transport release unexpectedly carries logical result")
    return _projection(
        runner=runner,
        session=running,
        status="coherent",
        capacity_state=capacity_state,
        capacity_head_digest=capacity_head.digest,
        physical_transition_count=len(transitions),
        latest_physical_attempt=latest_physical_attempt,
        dispatch_state=dispatch_state,
        durable_outcome_digest=record.outcome_digest,
        last_release_digest=last_release.digest,
        retry_eligible=True,
    )
