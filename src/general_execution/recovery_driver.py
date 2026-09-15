from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest
from .capacity import CapacityLease
from .dispatch import DispatchIntentError, DispatchPermit, prepare_dispatch_intent
from .durable import DurableCapacityError, SqliteCapacityHeadStore
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .observed import (
    ObservedOutcomeReleaseRecovery,
    SqliteDurableObservedOutcomeStore,
    release_observed_capacity_after_restart,
)
from .physical import (
    PhysicalAttemptAuthorization,
    PhysicalOutcomeBundle,
    authorize_physical_attempt,
    authorize_retry,
)
from .session import start_session
from .session_recovery import (
    SessionRecoveryProjection,
    project_session_after_restart,
)

RecoveryDriverStatus = Literal["applied", "no_action", "external_input_required"]


class RecoveryDriverError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryDriverResult:
    projection_digest: str
    action: str
    status: RecoveryDriverStatus
    resulting_session: ExecutionSession
    resulting_session_digest: str
    dispatch_state_digest: str | None = None
    dispatch_permit_digest: str | None = None
    capacity_recovery_digest: str | None = None
    next_projection_digest: str | None = None
    transport_authority: bool = False
    automatic_retry_authorized: bool = False
    schema_version: str = "ge.recovery-driver-result.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.recovery-driver-result.v1":
            raise ValueError("unsupported recovery driver result schema")
        if self.status not in {"applied", "no_action", "external_input_required"}:
            raise ValueError("unsupported recovery driver status")
        if self.transport_authority:
            raise ValueError("recovery driver cannot grant transport authority")
        if self.automatic_retry_authorized:
            raise ValueError("recovery driver cannot authorize automatic retry")
        if self.resulting_session_digest != sha256_digest(self.resulting_session):
            raise ValueError("resulting Session digest mismatch")
        for name in (
            "projection_digest",
            "resulting_session_digest",
            "dispatch_state_digest",
            "dispatch_permit_digest",
            "capacity_recovery_digest",
            "next_projection_digest",
        ):
            value = getattr(self, name)
            if value is None:
                continue
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _fresh_projection(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    runner: RunnerCapabilities,
    capacity_store: SqliteCapacityHeadStore,
    dispatch_store: SqliteDurableObservedOutcomeStore,
    supplied: SessionRecoveryProjection,
) -> SessionRecoveryProjection:
    fresh = project_session_after_restart(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
        attempt=supplied.logical_attempt,
    )
    if fresh != supplied:
        raise RecoveryDriverError("recovery projection is stale")
    return fresh


def _active_lease_for_projection(
    capacity_store: SqliteCapacityHeadStore,
    runner: RunnerCapabilities,
    projection: SessionRecoveryProjection,
) -> tuple[object, CapacityLease]:
    if projection.active_lease_id is None:
        raise RecoveryDriverError("recovery action requires an active capacity lease")
    try:
        state, _ = capacity_store.load(runner)
    except DurableCapacityError as exc:
        raise RecoveryDriverError("canonical durable capacity head is unavailable") from exc
    matches = [
        lease
        for lease in state.active_leases
        if lease.lease_id == projection.active_lease_id
        and lease.session_id == projection.session_id
        and lease.logical_attempt == projection.logical_attempt
    ]
    if len(matches) != 1:
        raise RecoveryDriverError("projection does not identify one exact active capacity lease")
    return state, matches[0]


def _prior_outcome_for_retry(
    dispatch_store: SqliteDurableObservedOutcomeStore,
    runner: RunnerCapabilities,
    lease: CapacityLease,
) -> PhysicalOutcomeBundle:
    if lease.physical_attempt <= 1:
        raise RecoveryDriverError("first physical attempt has no prior outcome")
    if lease.previous_invocation_id is None or lease.previous_receipt_digest is None:
        raise RecoveryDriverError("retry lease is missing predecessor bindings")
    matches = []
    for record in dispatch_store.recover_observed_for_runner(runner.runner_id):
        outcome = record.outcome
        auth = outcome.authorization
        if (
            auth.request.session_id == lease.session_id
            and auth.request.attempt == lease.logical_attempt
            and auth.physical_attempt == lease.physical_attempt - 1
            and auth.request.invocation_id == lease.previous_invocation_id
            and outcome.receipt.digest == lease.previous_receipt_digest
        ):
            matches.append(outcome)
    if len(matches) != 1:
        raise RecoveryDriverError("retry lease does not identify one exact durable predecessor outcome")
    return matches[0]


def _rebuild_authorization(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    dispatch_store: SqliteDurableObservedOutcomeStore,
    lease: CapacityLease,
) -> PhysicalAttemptAuthorization:
    try:
        if lease.physical_attempt == 1:
            authorization = authorize_physical_attempt(
                spec,
                registry,
                plan,
                session,
                runner,
                invocation_id=lease.invocation_id,
            )
        else:
            prior = _prior_outcome_for_retry(dispatch_store, runner, lease)
            authorization = authorize_retry(
                spec,
                registry,
                plan,
                session,
                runner,
                prior,
                invocation_id=lease.invocation_id,
            )
    except ValueError as exc:
        raise RecoveryDriverError("physical authorization could not be reproduced") from exc

    request = authorization.request
    if (
        authorization.authorization_id != lease.authorization_id
        or authorization.digest != lease.authorization_digest
        or authorization.physical_attempt != lease.physical_attempt
        or request.invocation_id != lease.invocation_id
        or request.session_id != lease.session_id
        or request.attempt != lease.logical_attempt
        or request.runner_id != lease.runner_id
        or request.runner_capability_digest != lease.runner_capability_digest
        or authorization.previous_invocation_id != lease.previous_invocation_id
        or authorization.previous_receipt_digest != lease.previous_receipt_digest
    ):
        raise RecoveryDriverError("reproduced physical authorization does not match active lease")
    return authorization


def _next_projection(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    runner: RunnerCapabilities,
    capacity_store: SqliteCapacityHeadStore,
    dispatch_store: SqliteDurableObservedOutcomeStore,
    attempt: int,
) -> SessionRecoveryProjection:
    return project_session_after_restart(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
        attempt=attempt,
    )


def _result(
    projection: SessionRecoveryProjection,
    *,
    status: RecoveryDriverStatus,
    session: ExecutionSession,
    dispatch_state_digest: str | None = None,
    permit: DispatchPermit | None = None,
    capacity_recovery: ObservedOutcomeReleaseRecovery | None = None,
    next_projection: SessionRecoveryProjection | None = None,
) -> RecoveryDriverResult:
    return RecoveryDriverResult(
        projection_digest=projection.digest,
        action=projection.recovery_action,
        status=status,
        resulting_session=session,
        resulting_session_digest=sha256_digest(session),
        dispatch_state_digest=dispatch_state_digest,
        dispatch_permit_digest=permit.digest if permit is not None else None,
        capacity_recovery_digest=capacity_recovery.digest if capacity_recovery is not None else None,
        next_projection_digest=next_projection.digest if next_projection is not None else None,
    )


def apply_recovery_step(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    runner: RunnerCapabilities,
    capacity_store: SqliteCapacityHeadStore,
    dispatch_store: SqliteDurableObservedOutcomeStore,
    projection: SessionRecoveryProjection,
) -> RecoveryDriverResult:
    """Apply at most one bounded mechanical restart-recovery action.

    This function never authorizes provider transport, never submits provider work,
    never performs provider reconciliation, and never turns retry eligibility into
    retry policy.
    """

    fresh = _fresh_projection(
        spec,
        registry,
        plan,
        runner,
        capacity_store,
        dispatch_store,
        projection,
    )
    if fresh.status in {"legacy_untracked", "inconsistent"}:
        raise RecoveryDriverError("recovery driver refuses non-recoverable projection")

    if fresh.status == "coherent":
        if fresh.recovery_action != "none":
            raise RecoveryDriverError("coherent projection cannot require a recovery action")
        return _result(fresh, status="no_action", session=fresh.projected_session)

    action = fresh.recovery_action
    if action == "start_session":
        if fresh.projected_session.state != "bound":
            raise RecoveryDriverError("start_session recovery requires a bound Session")
        session = start_session(fresh.projected_session)
        return _result(fresh, status="applied", session=session)

    if action == "prepare_dispatch_intent":
        if fresh.projected_session.state != "running":
            raise RecoveryDriverError("dispatch preparation requires a running Session")
        capacity_state, lease = _active_lease_for_projection(capacity_store, runner, fresh)
        authorization = _rebuild_authorization(
            spec,
            registry,
            plan,
            fresh.projected_session,
            runner,
            dispatch_store,
            lease,
        )
        try:
            intent = prepare_dispatch_intent(capacity_state, runner, lease, authorization)
            dispatch_state = dispatch_store.initialize(intent)
        except DispatchIntentError as exc:
            raise RecoveryDriverError("durable dispatch intent recovery failed") from exc
        next_projection = _next_projection(
            spec,
            registry,
            plan,
            runner,
            capacity_store,
            dispatch_store,
            fresh.logical_attempt,
        )
        return _result(
            fresh,
            status="applied",
            session=next_projection.projected_session,
            dispatch_state_digest=dispatch_state.digest,
            next_projection=next_projection,
        )

    if action == "begin_submission":
        if fresh.dispatch_intent_id is None:
            raise RecoveryDriverError("begin_submission recovery has no durable dispatch intent")
        try:
            current = dispatch_store.load(fresh.dispatch_intent_id)
            committed, permit = dispatch_store.begin_submission(
                fresh.dispatch_intent_id,
                current.digest,
                capacity_store,
                runner,
            )
        except DispatchIntentError as exc:
            raise RecoveryDriverError("durable begin_submission recovery failed") from exc
        if permit.transport_authority:
            raise RecoveryDriverError("dispatch permit unexpectedly grants transport authority")
        next_projection = _next_projection(
            spec,
            registry,
            plan,
            runner,
            capacity_store,
            dispatch_store,
            fresh.logical_attempt,
        )
        return _result(
            fresh,
            status="applied",
            session=next_projection.projected_session,
            dispatch_state_digest=committed.digest,
            permit=permit,
            next_projection=next_projection,
        )

    if action == "reconcile_provider":
        return _result(
            fresh,
            status="external_input_required",
            session=fresh.projected_session,
        )

    if action == "release_observed_capacity":
        if fresh.dispatch_intent_id is None:
            raise RecoveryDriverError("capacity release recovery has no durable dispatch intent")
        try:
            recovery = release_observed_capacity_after_restart(
                dispatch_store,
                capacity_store,
                fresh.dispatch_intent_id,
                spec,
                registry,
                plan,
                fresh.projected_session,
                runner,
            )
        except (DispatchIntentError, DurableCapacityError) as exc:
            raise RecoveryDriverError("observed capacity release recovery failed") from exc
        next_projection = _next_projection(
            spec,
            registry,
            plan,
            runner,
            capacity_store,
            dispatch_store,
            fresh.logical_attempt,
        )
        return _result(
            fresh,
            status="applied",
            session=next_projection.projected_session,
            capacity_recovery=recovery,
            next_projection=next_projection,
        )

    raise RecoveryDriverError("recovery projection names an unsupported action")
