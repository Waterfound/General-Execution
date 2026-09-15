import json
from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    authorize_physical_attempt,
    bind_session,
    initialize_capacity_state,
    plan_execution,
    reference_runner,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.durable import (
    DurableCapacityHead,
    DurableCapacitySnapshot,
    DurableStateError,
    build_durable_snapshot,
    load_durable_snapshot,
    recover_after_restart,
    serialize_durable_snapshot,
    verify_durable_snapshot,
    verify_durable_successor,
    verify_restart_recovery,
)

D = "sha256:" + "e" * 64
ZERO = "sha256:" + "0" * 64


def active_context():
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-durable-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective="Durable restart conformance",
        source_revision="source-durable-1",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://durable/1", D),),
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
        invocation_id="gei-durable-1",
    )
    state = initialize_capacity_state(runner)
    state, grant, _ = reserve_capacity(
        state,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    return runner, spec, registry, plan, session, state, grant


def test_snapshot_round_trip_replays_exact_capacity_state():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    payload = serialize_durable_snapshot(snapshot)
    loaded = load_durable_snapshot(payload, runner, expected_head_digest=snapshot.head.digest)
    assert loaded == snapshot
    assert verify_durable_snapshot(loaded, runner)


def test_restart_preserves_in_flight_lease_as_unknown():
    runner, _, _, _, _, state, grant = active_context()
    snapshot = build_durable_snapshot(state, runner)
    recovered_state, report = recover_after_restart(snapshot, runner)
    assert recovered_state == state
    assert recovered_state.active_leases == state.active_leases
    assert report.status == "reconciliation_required"
    assert len(report.active_leases) == 1
    assert report.active_leases[0].lease_id == grant.lease.lease_id
    assert report.active_leases[0].status == "in_flight_unknown"
    assert verify_restart_recovery(snapshot, runner, report)


def test_clean_restart_after_explicit_revocation_release():
    runner, _, _, _, session, state, grant = active_context()
    revoked = revoke_session(session)
    state, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    snapshot = build_durable_snapshot(state, runner)
    recovered_state, report = recover_after_restart(snapshot, runner)
    assert recovered_state.active_leases == ()
    assert report.status == "clean"
    assert report.active_leases == ()


def test_expected_head_digest_rejects_outdated_payload():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    payload = serialize_durable_snapshot(snapshot)
    with pytest.raises(DurableStateError):
        load_durable_snapshot(payload, runner, expected_head_digest=ZERO)


def test_payload_consistency_error_is_rejected_before_recovery():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    data = json.loads(serialize_durable_snapshot(snapshot))
    data["state"]["generation"] += 1
    with pytest.raises(DurableStateError):
        load_durable_snapshot(json.dumps(data), runner)


def test_nested_schema_change_is_rejected():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    data = json.loads(serialize_durable_snapshot(snapshot))
    data["state"]["transitions"][0]["lease"]["schema_version"] = "ge.capacity-lease.v999"
    with pytest.raises(DurableStateError):
        load_durable_snapshot(json.dumps(data), runner)


def test_missing_nested_schema_is_rejected():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    data = json.loads(serialize_durable_snapshot(snapshot))
    del data["state"]["transitions"][0]["lease"]["schema_version"]
    with pytest.raises(DurableStateError):
        load_durable_snapshot(json.dumps(data), runner)


def test_wrong_runner_cannot_adopt_durable_head():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    other = reference_runner("different-runner")
    with pytest.raises(DurableStateError):
        load_durable_snapshot(serialize_durable_snapshot(snapshot), other)


def test_successor_head_binds_previous_head_and_state_prefix():
    runner, _, _, _, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    revoked = revoke_session(session)
    state, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    second = build_durable_snapshot(state, runner, previous=first)
    assert second.head.previous_head_digest == first.head.digest
    assert verify_durable_successor(first, second, runner)


def test_durable_head_cannot_move_backwards():
    runner, _, _, _, _, state, _ = active_context()
    current = build_durable_snapshot(state, runner)
    older = initialize_capacity_state(runner)
    with pytest.raises(DurableStateError):
        build_durable_snapshot(older, runner, previous=current)


def test_previous_head_mismatch_is_not_a_valid_successor():
    runner, _, _, _, session, state, grant = active_context()
    first = build_durable_snapshot(state, runner)
    revoked = revoke_session(session)
    state, _, _ = release_capacity_for_revocation(state, runner, grant.lease, revoked)
    second = build_durable_snapshot(state, runner, previous=first)
    changed = DurableCapacitySnapshot(
        head=replace(second.head, previous_head_digest=ZERO),
        state=second.state,
    )
    assert verify_durable_snapshot(changed, runner)
    assert not verify_durable_successor(first, changed, runner)


def test_in_memory_schema_version_is_strict():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    with pytest.raises(ValueError):
        DurableCapacityHead(
            runner_id=snapshot.head.runner_id,
            runner_capability_digest=snapshot.head.runner_capability_digest,
            generation=snapshot.head.generation,
            state_digest=snapshot.head.state_digest,
            payload_digest=snapshot.head.payload_digest,
            schema_version="ge.durable-capacity-head.v999",
        )


def test_serialization_is_deterministic():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    assert serialize_durable_snapshot(snapshot) == serialize_durable_snapshot(snapshot)


def test_recovery_report_consistency_change_is_detected():
    runner, _, _, _, _, state, _ = active_context()
    snapshot = build_durable_snapshot(state, runner)
    _, report = recover_after_restart(snapshot, runner)
    changed = replace(report, state_digest=ZERO)
    assert not verify_restart_recovery(snapshot, runner, changed)
