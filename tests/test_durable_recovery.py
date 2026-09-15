import json
import sqlite3
from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    CapacityError,
    DurableCapacityError,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    admit_physical_observation,
    authorize_physical_attempt,
    bind_session,
    deserialize_capacity_snapshot,
    initialize_capacity_state,
    observe_failure,
    plan_execution,
    recover_capacity_after_restart,
    reference_runner,
    release_capacity_for_outcome,
    reserve_capacity,
    serialize_capacity_snapshot,
    start_session,
    verify_restart_recovery,
)

D = "sha256:" + "d" * 64


def make_context(runner, suffix):
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-durable-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable recovery conformance {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://durable/{suffix}", D),),
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


def test_capacity_snapshot_round_trip_replays_exact_state():
    runner = reference_runner()
    context = make_context(runner, "roundtrip")
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(state, *context[:4], runner, context[4])
    encoded = serialize_capacity_snapshot(state)
    decoded, snapshot_digest = deserialize_capacity_snapshot(encoded, runner)
    assert decoded == state
    assert decoded.digest == state.digest
    assert snapshot_digest.startswith("sha256:")


def test_store_initialize_and_reload_is_restart_stable(tmp_path):
    runner = reference_runner()
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    initial = initialize_capacity_state(runner)
    head = store.initialize(runner, initial)

    restarted = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    loaded, loaded_head = restarted.load(runner)
    assert loaded == initial
    assert loaded_head == head


def test_active_lease_survives_restart_and_still_consumes_capacity(tmp_path):
    runner = reference_runner()
    first = make_context(runner, "active")
    second = make_context(runner, "blocked")
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    state = initialize_capacity_state(runner)
    store.initialize(runner, state)
    reserved, grant, _ = reserve_capacity(state, *first[:4], runner, first[4])
    store.commit(runner, state.digest, reserved)

    restarted = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    recovered, report = recover_capacity_after_restart(restarted, runner)
    _, head = restarted.load(runner)
    assert recovered == reserved
    assert recovered.active_leases == (grant.lease,)
    assert report.active_lease_count == 1
    assert report.unresolved_leases[0].lease_id == grant.lease.lease_id
    assert report.unresolved_leases[0].authorization_id == grant.lease.authorization_id
    assert report.unresolved_leases[0].authorization_digest == grant.lease.authorization_digest
    assert report.unresolved_leases[0].status == "in_flight_unresolved"
    assert report.physical_outcomes_fabricated == 0
    assert report.capacity_releases_fabricated == 0
    assert verify_restart_recovery(recovered, head, report)
    assert not verify_restart_recovery(recovered, head, replace(report, state_digest=D))
    with pytest.raises(CapacityError):
        reserve_capacity(recovered, *second[:4], runner, second[4])


def test_real_outcome_after_restart_releases_recovered_lease(tmp_path):
    runner = reference_runner()
    context = make_context(runner, "continue")
    spec, registry, plan, session, authorization = context
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    state = initialize_capacity_state(runner)
    store.initialize(runner, state)
    reserved, grant, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, authorization
    )
    store.commit(runner, state.digest, reserved)

    restarted = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    recovered, report = recover_capacity_after_restart(restarted, runner)
    assert report.active_lease_count == 1

    outcome = failure_outcome(context, runner, authorization)
    released, _, _ = release_capacity_for_outcome(
        recovered,
        spec,
        registry,
        plan,
        session,
        runner,
        recovered.active_leases[0],
        outcome,
    )
    restarted.commit(runner, recovered.digest, released)

    second_restart = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    final_state, final_report = recover_capacity_after_restart(second_restart, runner)
    assert final_state == released
    assert final_state.active_leases == ()
    assert final_report.active_lease_count == 0
    assert final_report.unresolved_leases == ()


def test_stale_durable_compare_and_swap_is_rejected(tmp_path):
    runner = replace(reference_runner(), max_parallelism=2)
    first = make_context(runner, "race-a")
    second = make_context(runner, "race-b")
    store_a = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    genesis = initialize_capacity_state(runner)
    store_a.initialize(runner, genesis)

    state_a, _, _ = reserve_capacity(genesis, *first[:4], runner, first[4])
    state_b, _, _ = reserve_capacity(genesis, *second[:4], runner, second[4])
    store_b = SqliteCapacityHeadStore(tmp_path / "capacity.db")

    store_a.commit(runner, genesis.digest, state_a)
    with pytest.raises(DurableCapacityError, match="stale durable capacity head"):
        store_b.commit(runner, genesis.digest, state_b)


def test_store_rejects_generation_skip_even_if_candidate_replays(tmp_path):
    runner = reference_runner()
    context = make_context(runner, "skip")
    spec, registry, plan, session, authorization = context
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    genesis = initialize_capacity_state(runner)
    store.initialize(runner, genesis)
    reserved, grant, _ = reserve_capacity(
        genesis, spec, registry, plan, session, runner, authorization
    )
    outcome = failure_outcome(context, runner, authorization)
    released, _, _ = release_capacity_for_outcome(
        reserved, spec, registry, plan, session, runner, grant.lease, outcome
    )
    assert released.generation == 2
    with pytest.raises(DurableCapacityError, match="advance exactly one generation"):
        store.commit(runner, genesis.digest, released)


def test_tampered_snapshot_is_rejected_on_restart(tmp_path):
    runner = reference_runner()
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    store.initialize(runner)
    with sqlite3.connect(tmp_path / "capacity.db") as connection:
        raw = connection.execute(
            "SELECT snapshot_json FROM capacity_heads WHERE runner_id = ?",
            (runner.runner_id,),
        ).fetchone()[0]
        data = json.loads(raw)
        data["state"]["generation"] = 7
        connection.execute(
            "UPDATE capacity_heads SET snapshot_json = ? WHERE runner_id = ?",
            (json.dumps(data), runner.runner_id),
        )
    restarted = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    with pytest.raises(DurableCapacityError, match="snapshot digest mismatch"):
        restarted.load(runner)


def test_tampered_head_metadata_is_rejected(tmp_path):
    runner = reference_runner()
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    store.initialize(runner)
    with sqlite3.connect(tmp_path / "capacity.db") as connection:
        connection.execute(
            "UPDATE capacity_heads SET state_digest = ? WHERE runner_id = ?",
            ("sha256:" + "0" * 64, runner.runner_id),
        )
    with pytest.raises(DurableCapacityError, match="metadata mismatch"):
        store.load(runner)
    with pytest.raises(DurableCapacityError, match="metadata mismatch"):
        store.initialize(runner)


def test_runner_capability_drift_is_rejected(tmp_path):
    runner = reference_runner()
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    store.initialize(runner)
    changed_runner = replace(runner, max_parallelism=2)
    with pytest.raises(DurableCapacityError, match="runner capabilities changed"):
        store.load(changed_runner)


def test_initialize_is_idempotent_only_for_identical_state(tmp_path):
    runner = reference_runner()
    context = make_context(runner, "init")
    store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    genesis = initialize_capacity_state(runner)
    head_a = store.initialize(runner, genesis)
    head_b = store.initialize(runner, genesis)
    assert head_a == head_b

    reserved, _, _ = reserve_capacity(genesis, *context[:4], runner, context[4])
    with pytest.raises(DurableCapacityError, match="already exists with different state"):
        store.initialize(runner, reserved)
