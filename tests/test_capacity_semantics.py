from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    CapacityError,
    ExecutionLedger,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    admit_physical_observation,
    authorize_physical_attempt,
    authorize_retry,
    bind_session,
    commit_capacity_reservation,
    initialize_capacity_state,
    observe_failure,
    plan_execution,
    propose_capacity_reservation,
    record_capacity_transition,
    reference_runner,
    release_capacity_for_outcome,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
    verify_active_lease_grant,
    verify_capacity_release_grant,
    verify_capacity_state,
    verify_capacity_transition_record,
)

D = "sha256:" + "d" * 64


def make_context(runner, suffix):
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-capacity-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Capacity conformance {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://capacity/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=f"gei-{suffix}-1",
    )
    return spec, registry, plan, session, authorization


def failure_outcome(context, runner, authorization, status="timed_out"):
    spec, registry, plan, session, _ = context
    observation = observe_failure(
        authorization,
        status,
        failure_code=f"reference.{status}",
        provider_invocation_id=f"provider-{authorization.request.invocation_id}",
    )
    return admit_physical_observation(
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
        observation,
    )


def test_max_parallelism_one_blocks_second_active_lease():
    runner = reference_runner()
    first = make_context(runner, "a")
    second = make_context(runner, "b")
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, *first[:4], runner, first[4])
    with pytest.raises(CapacityError):
        reserve_capacity(state, *second[:4], runner, second[4])


def test_max_parallelism_two_allocates_distinct_slots():
    runner = replace(reference_runner(), max_parallelism=2)
    first = make_context(runner, "a")
    second = make_context(runner, "b")
    state = initialize_capacity_state(runner)
    state, grant_a, _ = reserve_capacity(state, *first[:4], runner, first[4])
    state, grant_b, _ = reserve_capacity(state, *second[:4], runner, second[4])
    assert {grant_a.lease.slot, grant_b.lease.slot} == {0, 1}
    assert len(state.active_leases) == 2


def test_two_proposals_from_same_snapshot_use_compare_and_swap():
    runner = replace(reference_runner(), max_parallelism=2)
    first = make_context(runner, "a")
    second = make_context(runner, "b")
    state = initialize_capacity_state(runner)
    transition_a = propose_capacity_reservation(state, *first[:4], runner, first[4])
    transition_b = propose_capacity_reservation(state, *second[:4], runner, second[4])
    state, _ = commit_capacity_reservation(
        state, *first[:4], runner, first[4], transition_a
    )
    with pytest.raises(CapacityError):
        commit_capacity_reservation(
            state, *second[:4], runner, second[4], transition_b
        )


def test_retry_requires_predecessor_capacity_release():
    runner = reference_runner()
    context = make_context(runner, "retry")
    spec, registry, plan, session, first_authorization = context
    state = initialize_capacity_state(runner)
    state, first_grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, first_authorization
    )
    first_outcome = failure_outcome(context, runner, first_authorization)
    retry = authorize_retry(
        spec,
        registry,
        plan,
        session,
        runner,
        first_outcome,
        invocation_id="gei-retry-2",
    )
    with pytest.raises(CapacityError):
        reserve_capacity(state, spec, registry, plan, session, runner, retry)

    state, release_grant, _ = release_capacity_for_outcome(
        state,
        spec,
        registry,
        plan,
        session,
        runner,
        first_grant.lease,
        first_outcome,
    )
    assert verify_capacity_release_grant(state, runner, release_grant)
    state, retry_grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, retry
    )
    assert retry_grant.lease.physical_attempt == 2
    assert retry_grant.lease.slot == 0
    assert retry_grant.lease.previous_invocation_id == first_outcome.authorization.request.invocation_id
    assert retry_grant.lease.previous_receipt_digest == first_outcome.receipt.digest


def test_session_revocation_releases_active_capacity():
    runner = reference_runner()
    context = make_context(runner, "revoke")
    spec, registry, plan, session, authorization = context
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, authorization
    )
    revoked = revoke_session(session)
    state, release_grant, _ = release_capacity_for_revocation(
        state, runner, grant.lease, revoked
    )
    assert state.active_leases == ()
    assert not verify_active_lease_grant(state, runner, grant)
    assert verify_capacity_release_grant(state, runner, release_grant)


def test_competing_retry_proposals_cannot_both_commit():
    runner = reference_runner()
    context = make_context(runner, "race")
    spec, registry, plan, session, first_authorization = context
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, first_authorization
    )
    first_outcome = failure_outcome(context, runner, first_authorization)
    state, _, _ = release_capacity_for_outcome(
        state,
        spec,
        registry,
        plan,
        session,
        runner,
        grant.lease,
        first_outcome,
    )
    retry_a = authorize_retry(
        spec, registry, plan, session, runner, first_outcome, invocation_id="gei-race-2a"
    )
    retry_b = authorize_retry(
        spec, registry, plan, session, runner, first_outcome, invocation_id="gei-race-2b"
    )
    transition_a = propose_capacity_reservation(
        state, spec, registry, plan, session, runner, retry_a
    )
    transition_b = propose_capacity_reservation(
        state, spec, registry, plan, session, runner, retry_b
    )
    state, _ = commit_capacity_reservation(
        state, spec, registry, plan, session, runner, retry_a, transition_a
    )
    with pytest.raises(CapacityError):
        commit_capacity_reservation(
            state, spec, registry, plan, session, runner, retry_b, transition_b
        )


def test_capacity_state_replays_and_grant_fields_are_verified():
    runner = reference_runner()
    context = make_context(runner, "ledger")
    state = initialize_capacity_state(runner)
    state, grant, transition = reserve_capacity(
        state, *context[:4], runner, context[4]
    )
    assert verify_capacity_state(state, runner)
    assert verify_active_lease_grant(state, runner, grant)
    assert not verify_active_lease_grant(
        state, runner, replace(grant, committed_state_digest=D)
    )
    ledger, record = record_capacity_transition(
        ExecutionLedger(), transition, state
    )
    assert verify_capacity_transition_record(
        ledger, transition, state, record
    )


def test_retry_predecessor_binding_is_replayed_from_capacity_state():
    runner = reference_runner()
    context = make_context(runner, "replay")
    spec, registry, plan, session, first_authorization = context
    state = initialize_capacity_state(runner)
    state, first_grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, first_authorization
    )
    first_outcome = failure_outcome(context, runner, first_authorization)
    state, _, _ = release_capacity_for_outcome(
        state,
        spec,
        registry,
        plan,
        session,
        runner,
        first_grant.lease,
        first_outcome,
    )
    retry = authorize_retry(
        spec,
        registry,
        plan,
        session,
        runner,
        first_outcome,
        invocation_id="gei-replay-2",
    )
    state, _, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, retry
    )
    assert verify_capacity_state(state, runner)

    final_transition = state.transitions[-1]
    bad_lease = replace(
        final_transition.lease,
        previous_receipt_digest="sha256:" + "0" * 64,
    )
    bad_transition = replace(final_transition, lease=bad_lease)
    tampered = replace(
        state,
        transitions=state.transitions[:-1] + (bad_transition,),
    )
    assert not verify_capacity_state(tampered, runner)
