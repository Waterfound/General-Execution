from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .adapter import verify_dispatch_request
from .canonical import sha256_digest, stable_id
from .ledger import ExecutionLedger, append_event, verify_ledger
from .models import ExecutionSession, RunnerCapabilities
from .physical import (
    VALID_TRANSPORT_STATUSES,
    PhysicalAttemptAuthorization,
    PhysicalOutcomeBundle,
    verify_physical_outcome,
)

ReleaseKind = Literal['terminal_outcome', 'session_revoked']
TransitionKind = Literal['reserve', 'release']


class CapacityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CapacityLease:
    runner_id: str
    runner_capability_digest: str
    slot: int
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    previous_invocation_id: str | None
    previous_receipt_digest: str | None
    expected_state_digest: str
    schema_version: str = 'ge.capacity-lease.v1'

    def __post_init__(self):
        if self.slot < 0:
            raise ValueError('slot must be >= 0')
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError('attempt ordinals must be >= 1')
        first = self.physical_attempt == 1
        if first and (self.previous_invocation_id is not None or self.previous_receipt_digest is not None):
            raise ValueError('first physical lease cannot have predecessor bindings')
        if not first and (self.previous_invocation_id is None or self.previous_receipt_digest is None):
            raise ValueError('retry physical lease requires predecessor bindings')

    @property
    def lease_id(self):
        return stable_id('gecl', self)

    @property
    def digest(self):
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CapacityRelease:
    lease_id: str
    lease_digest: str
    runner_id: str
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    release_kind: ReleaseKind
    expected_state_digest: str
    outcome_digest: str | None = None
    receipt_digest: str | None = None
    transport_status: str | None = None
    revoked_session_digest: str | None = None
    schema_version: str = 'ge.capacity-release.v1'

    def __post_init__(self):
        if self.release_kind == 'terminal_outcome':
            if not self.outcome_digest or not self.receipt_digest or not self.transport_status or self.revoked_session_digest is not None:
                raise ValueError('terminal outcome release requires outcome, receipt and transport status only')
            if self.transport_status not in VALID_TRANSPORT_STATUSES:
                raise ValueError('unsupported terminal transport status')
        elif self.release_kind == 'session_revoked':
            if not self.revoked_session_digest or self.outcome_digest is not None or self.receipt_digest is not None or self.transport_status is not None:
                raise ValueError('session revocation release requires revoked session digest only')
        else:
            raise ValueError('unsupported release_kind')

    @property
    def release_id(self):
        return stable_id('gecr', self)

    @property
    def digest(self):
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CapacityTransition:
    kind: TransitionKind
    expected_state_digest: str
    lease: CapacityLease | None = None
    release: CapacityRelease | None = None
    schema_version: str = 'ge.capacity-transition.v1'

    def __post_init__(self):
        if self.kind == 'reserve':
            if self.lease is None or self.release is not None:
                raise ValueError('reserve transition requires lease only')
        elif self.kind == 'release':
            if self.release is None or self.lease is not None:
                raise ValueError('release transition requires release only')
        else:
            raise ValueError('unsupported transition kind')

    @property
    def digest(self):
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RunnerCapacityState:
    runner_id: str
    runner_capability_digest: str
    max_parallelism: int
    generation: int = 0
    previous_state_digest: str | None = None
    transitions: tuple[CapacityTransition, ...] = ()
    schema_version: str = 'ge.runner-capacity-state.v1'

    def __post_init__(self):
        if self.max_parallelism < 1:
            raise ValueError('max_parallelism must be >= 1')
        if self.generation < 0:
            raise ValueError('generation must be >= 0')
        if self.generation == 0 and self.previous_state_digest is not None:
            raise ValueError('genesis capacity state cannot have predecessor')
        if self.generation > 0 and self.previous_state_digest is None:
            raise ValueError('non-genesis capacity state requires predecessor digest')
        if self.generation != len(self.transitions):
            raise ValueError('generation must equal transition count')

    @property
    def digest(self):
        return sha256_digest(self)

    @property
    def state_id(self):
        return stable_id('gecs', self)

    @property
    def leases(self):
        return tuple(t.lease for t in self.transitions if t.kind == 'reserve' and t.lease is not None)

    @property
    def releases(self):
        return tuple(t.release for t in self.transitions if t.kind == 'release' and t.release is not None)

    @property
    def active_leases(self):
        released = {r.lease_id for r in self.releases}
        return tuple(l for l in self.leases if l.lease_id not in released)


@dataclass(frozen=True, slots=True)
class CapacityLeaseGrant:
    lease: CapacityLease
    reservation_transition_digest: str
    committed_state_digest: str
    committed_generation: int
    schema_version: str = 'ge.capacity-lease-grant.v1'

    @property
    def digest(self):
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CapacityReleaseGrant:
    release: CapacityRelease
    release_transition_digest: str
    committed_state_digest: str
    committed_generation: int
    schema_version: str = 'ge.capacity-release-grant.v1'

    @property
    def digest(self):
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CapacityTransitionRecord:
    transition_digest: str
    state_digest: str
    event_index: int
    recorded_head: str
    schema_version: str = 'ge.capacity-transition-record.v1'

    @property
    def digest(self):
        return sha256_digest(self)


def initialize_capacity_state(runner: RunnerCapabilities) -> RunnerCapacityState:
    return RunnerCapacityState(runner.runner_id, runner.digest, runner.max_parallelism)


def _validate_state_runner(state: RunnerCapacityState, runner: RunnerCapabilities) -> None:
    if (state.runner_id, state.runner_capability_digest, state.max_parallelism) != (runner.runner_id, runner.digest, runner.max_parallelism):
        raise CapacityError('capacity state is not bound to the exact runner capabilities')
    if not verify_capacity_state(state, runner):
        raise CapacityError('capacity state does not replay')


def _active_session_keys(state):
    return {(l.session_id, l.logical_attempt) for l in state.active_leases}


def _predecessor_released(state, session_id, logical_attempt, physical_attempt, previous_invocation_id, previous_receipt_digest) -> bool:
    if physical_attempt == 1:
        return previous_invocation_id is None and previous_receipt_digest is None
    for release in state.releases:
        if (
            release.release_kind == 'terminal_outcome'
            and release.session_id == session_id
            and release.logical_attempt == logical_attempt
            and release.physical_attempt == physical_attempt - 1
            and release.invocation_id == previous_invocation_id
            and release.receipt_digest == previous_receipt_digest
            and release.transport_status != 'completed'
        ):
            return True
    return False


def _retry_predecessor_released(state: RunnerCapacityState, auth: PhysicalAttemptAuthorization) -> bool:
    return _predecessor_released(
        state,
        auth.request.session_id,
        auth.request.attempt,
        auth.physical_attempt,
        auth.previous_invocation_id,
        auth.previous_receipt_digest,
    )


def propose_capacity_reservation(state: RunnerCapacityState, spec, registry, plan, session: ExecutionSession, runner: RunnerCapabilities, auth: PhysicalAttemptAuthorization) -> CapacityTransition:
    _validate_state_runner(state, runner)
    if not verify_dispatch_request(spec, registry, plan, session, runner, auth.request):
        raise CapacityError('physical authorization request does not reproduce from execution context')
    request = auth.request
    if request.runner_id != runner.runner_id or request.runner_capability_digest != runner.digest:
        raise CapacityError('physical authorization is not bound to this runner')
    if len(state.active_leases) >= state.max_parallelism:
        raise CapacityError('runner capacity exhausted')
    if any(l.authorization_digest == auth.digest for l in state.leases):
        raise CapacityError('physical authorization already has a canonical capacity lease')
    if (request.session_id, request.attempt) in _active_session_keys(state):
        raise CapacityError('logical Session already has an active canonical physical lease')
    if not _retry_predecessor_released(state, auth):
        raise CapacityError('retry predecessor has not been canonically released')
    occupied = {l.slot for l in state.active_leases}
    slot = next((i for i in range(state.max_parallelism) if i not in occupied), None)
    if slot is None:
        raise CapacityError('runner capacity exhausted')
    lease = CapacityLease(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        slot=slot,
        session_id=request.session_id,
        logical_attempt=request.attempt,
        authorization_id=auth.authorization_id,
        authorization_digest=auth.digest,
        invocation_id=request.invocation_id,
        physical_attempt=auth.physical_attempt,
        previous_invocation_id=auth.previous_invocation_id,
        previous_receipt_digest=auth.previous_receipt_digest,
        expected_state_digest=state.digest,
    )
    return CapacityTransition('reserve', state.digest, lease=lease)


def _apply_transition_unchecked(state: RunnerCapacityState, transition: CapacityTransition) -> RunnerCapacityState:
    if transition.expected_state_digest != state.digest:
        raise CapacityError('stale capacity transition')
    if transition.kind == 'reserve':
        lease = transition.lease
        assert lease is not None
        if lease.expected_state_digest != state.digest:
            raise CapacityError('lease snapshot binding mismatch')
        if lease.runner_id != state.runner_id or lease.runner_capability_digest != state.runner_capability_digest:
            raise CapacityError('lease runner binding mismatch')
        if lease.slot >= state.max_parallelism:
            raise CapacityError('lease slot is outside runner capacity')
        if len(state.active_leases) >= state.max_parallelism or lease.slot in {x.slot for x in state.active_leases}:
            raise CapacityError('capacity slot is already occupied')
        if any(x.lease_id == lease.lease_id or x.authorization_digest == lease.authorization_digest for x in state.leases):
            raise CapacityError('duplicate canonical lease')
        if (lease.session_id, lease.logical_attempt) in _active_session_keys(state):
            raise CapacityError('logical Session already has an active lease')
        if not _predecessor_released(
            state,
            lease.session_id,
            lease.logical_attempt,
            lease.physical_attempt,
            lease.previous_invocation_id,
            lease.previous_receipt_digest,
        ):
            raise CapacityError('lease retry predecessor is not canonically released')
    else:
        release = transition.release
        assert release is not None
        if release.expected_state_digest != state.digest:
            raise CapacityError('release snapshot binding mismatch')
        matches = [x for x in state.active_leases if x.lease_id == release.lease_id and x.digest == release.lease_digest]
        if len(matches) != 1:
            raise CapacityError('release does not reference one active lease')
        lease = matches[0]
        if (
            release.runner_id,
            release.session_id,
            release.logical_attempt,
            release.authorization_id,
            release.authorization_digest,
            release.invocation_id,
            release.physical_attempt,
        ) != (
            lease.runner_id,
            lease.session_id,
            lease.logical_attempt,
            lease.authorization_id,
            lease.authorization_digest,
            lease.invocation_id,
            lease.physical_attempt,
        ):
            raise CapacityError('release identity does not match active lease')
    return RunnerCapacityState(
        runner_id=state.runner_id,
        runner_capability_digest=state.runner_capability_digest,
        max_parallelism=state.max_parallelism,
        generation=state.generation + 1,
        previous_state_digest=state.digest,
        transitions=state.transitions + (transition,),
    )


def commit_capacity_reservation(state, spec, registry, plan, session, runner, auth, transition):
    expected = propose_capacity_reservation(state, spec, registry, plan, session, runner, auth)
    if transition != expected:
        raise CapacityError('reservation transition does not reproduce from current state')
    new_state = _apply_transition_unchecked(state, transition)
    return new_state, CapacityLeaseGrant(transition.lease, transition.digest, new_state.digest, new_state.generation)


def reserve_capacity(state, spec, registry, plan, session, runner, auth):
    transition = propose_capacity_reservation(state, spec, registry, plan, session, runner, auth)
    new_state, grant = commit_capacity_reservation(state, spec, registry, plan, session, runner, auth, transition)
    return new_state, grant, transition


def _find_active_lease(state: RunnerCapacityState, lease: CapacityLease) -> CapacityLease:
    matches = [x for x in state.active_leases if x.lease_id == lease.lease_id and x.digest == lease.digest]
    if len(matches) != 1:
        raise CapacityError('capacity lease is not active')
    return matches[0]


def propose_outcome_release(state, spec, registry, plan, session, runner, lease, outcome: PhysicalOutcomeBundle):
    _validate_state_runner(state, runner)
    if not verify_physical_outcome(spec, registry, plan, session, runner, outcome):
        raise CapacityError('physical outcome does not reproduce from execution context')
    lease = _find_active_lease(state, lease)
    auth = outcome.authorization
    if (auth.authorization_id, auth.digest, auth.request.invocation_id, auth.physical_attempt) != (lease.authorization_id, lease.authorization_digest, lease.invocation_id, lease.physical_attempt):
        raise CapacityError('physical outcome does not belong to active lease')
    if (auth.request.session_id, auth.request.attempt, auth.request.runner_id) != (lease.session_id, lease.logical_attempt, lease.runner_id):
        raise CapacityError('physical outcome Session binding mismatch')
    release = CapacityRelease(
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        runner_id=lease.runner_id,
        session_id=lease.session_id,
        logical_attempt=lease.logical_attempt,
        authorization_id=lease.authorization_id,
        authorization_digest=lease.authorization_digest,
        invocation_id=lease.invocation_id,
        physical_attempt=lease.physical_attempt,
        release_kind='terminal_outcome',
        expected_state_digest=state.digest,
        outcome_digest=outcome.digest,
        receipt_digest=outcome.receipt.digest,
        transport_status=outcome.receipt.transport_status,
    )
    return CapacityTransition('release', state.digest, release=release)


def commit_outcome_release(state, spec, registry, plan, session, runner, lease, outcome, transition):
    expected = propose_outcome_release(state, spec, registry, plan, session, runner, lease, outcome)
    if transition != expected:
        raise CapacityError('outcome release transition does not reproduce')
    new_state = _apply_transition_unchecked(state, transition)
    return new_state, CapacityReleaseGrant(transition.release, transition.digest, new_state.digest, new_state.generation)


def release_capacity_for_outcome(state, spec, registry, plan, session, runner, lease, outcome):
    transition = propose_outcome_release(state, spec, registry, plan, session, runner, lease, outcome)
    new_state, grant = commit_outcome_release(state, spec, registry, plan, session, runner, lease, outcome, transition)
    return new_state, grant, transition


def propose_revocation_release(state, runner, lease, revoked_session: ExecutionSession):
    _validate_state_runner(state, runner)
    lease = _find_active_lease(state, lease)
    if revoked_session.state != 'revoked':
        raise CapacityError('Session must be revoked before capacity release')
    if (revoked_session.session_id, revoked_session.attempt, revoked_session.runner_id, revoked_session.runner_capability_digest) != (lease.session_id, lease.logical_attempt, lease.runner_id, lease.runner_capability_digest):
        raise CapacityError('revoked Session does not own this capacity lease')
    release = CapacityRelease(
        lease_id=lease.lease_id,
        lease_digest=lease.digest,
        runner_id=lease.runner_id,
        session_id=lease.session_id,
        logical_attempt=lease.logical_attempt,
        authorization_id=lease.authorization_id,
        authorization_digest=lease.authorization_digest,
        invocation_id=lease.invocation_id,
        physical_attempt=lease.physical_attempt,
        release_kind='session_revoked',
        expected_state_digest=state.digest,
        revoked_session_digest=sha256_digest(revoked_session),
    )
    return CapacityTransition('release', state.digest, release=release)


def commit_revocation_release(state, runner, lease, revoked_session, transition):
    expected = propose_revocation_release(state, runner, lease, revoked_session)
    if transition != expected:
        raise CapacityError('revocation release transition does not reproduce')
    new_state = _apply_transition_unchecked(state, transition)
    return new_state, CapacityReleaseGrant(transition.release, transition.digest, new_state.digest, new_state.generation)


def release_capacity_for_revocation(state, runner, lease, revoked_session):
    transition = propose_revocation_release(state, runner, lease, revoked_session)
    new_state, grant = commit_revocation_release(state, runner, lease, revoked_session, transition)
    return new_state, grant, transition


def verify_capacity_state(state: RunnerCapacityState, runner: RunnerCapabilities) -> bool:
    if (state.runner_id, state.runner_capability_digest, state.max_parallelism) != (runner.runner_id, runner.digest, runner.max_parallelism):
        return False
    current = initialize_capacity_state(runner)
    try:
        for transition in state.transitions:
            current = _apply_transition_unchecked(current, transition)
    except (CapacityError, ValueError):
        return False
    return current == state


def _committed_transition_at_generation(state: RunnerCapacityState, runner: RunnerCapabilities, generation: int):
    if generation < 1 or generation > state.generation:
        return None
    current = initialize_capacity_state(runner)
    try:
        for index, transition in enumerate(state.transitions, start=1):
            current = _apply_transition_unchecked(current, transition)
            if index == generation:
                return current, transition
    except (CapacityError, ValueError):
        return None
    return None


def verify_active_lease_grant(state: RunnerCapacityState, runner: RunnerCapabilities, grant: CapacityLeaseGrant) -> bool:
    if not verify_capacity_state(state, runner):
        return False
    committed = _committed_transition_at_generation(state, runner, grant.committed_generation)
    if committed is None:
        return False
    committed_state, transition = committed
    if (
        transition.kind != 'reserve'
        or transition.lease != grant.lease
        or transition.digest != grant.reservation_transition_digest
        or committed_state.digest != grant.committed_state_digest
    ):
        return False
    return any(lease == grant.lease for lease in state.active_leases)


def verify_capacity_release_grant(state: RunnerCapacityState, runner: RunnerCapabilities, grant: CapacityReleaseGrant) -> bool:
    if not verify_capacity_state(state, runner):
        return False
    committed = _committed_transition_at_generation(state, runner, grant.committed_generation)
    if committed is None:
        return False
    committed_state, transition = committed
    if (
        transition.kind != 'release'
        or transition.release != grant.release
        or transition.digest != grant.release_transition_digest
        or committed_state.digest != grant.committed_state_digest
    ):
        return False
    return any(release == grant.release for release in state.releases)


def record_capacity_transition(ledger: ExecutionLedger, transition: CapacityTransition, state: RunnerCapacityState):
    if not state.transitions or state.transitions[-1] != transition:
        raise CapacityError('state does not end with supplied capacity transition')
    event_type = 'CAPACITY_RESERVED' if transition.kind == 'reserve' else 'CAPACITY_RELEASED'
    payload = {
        'transition': asdict(transition),
        'transition_digest': transition.digest,
        'state_digest': state.digest,
        'generation': state.generation,
    }
    if any(isinstance(e.payload, dict) and e.payload.get('transition_digest') == transition.digest for e in ledger.events):
        raise CapacityError('capacity transition is already recorded')
    updated = append_event(ledger, event_type, payload)
    record = CapacityTransitionRecord(transition.digest, state.digest, len(updated.events) - 1, updated.head)
    return updated, record


def verify_capacity_transition_record(ledger, transition, state, record):
    if not verify_ledger(ledger):
        return False
    if record.event_index < 0 or record.event_index >= len(ledger.events):
        return False
    event = ledger.events[record.event_index]
    expected_type = 'CAPACITY_RESERVED' if transition.kind == 'reserve' else 'CAPACITY_RELEASED'
    expected_payload = {
        'transition': asdict(transition),
        'transition_digest': transition.digest,
        'state_digest': state.digest,
        'generation': state.generation,
    }
    return (
        record.transition_digest == transition.digest
        and record.state_digest == state.digest
        and event.event_type == expected_type
        and event.payload == expected_payload
        and event.event_hash == record.recorded_head
    )
