import json
import sqlite3
from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    admit_physical_observation,
    authorize_physical_attempt,
    bind_session,
    initialize_capacity_state,
    observe_failure,
    plan_execution,
    reference_runner,
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.dispatch import (
    DispatchIntentError,
    SqliteDispatchIntentStore,
    prepare_dispatch_intent,
    recover_dispatch_after_restart,
    verify_dispatch_permit,
    verify_dispatch_recovery,
)
from general_execution.dispatch_guard import (
    authorize_live_dispatch,
    verify_live_dispatch_permit,
)

D = "sha256:" + "d" * 64


def make_context(runner, suffix):
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-dispatch-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable dispatch conformance {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://dispatch/{suffix}", D),),
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


def failure_outcome(context, runner, status="timed_out"):
    spec, registry, plan, session, authorization = context
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


def prepare_store(tmp_path, suffix="base", runner=None):
    runner = runner or reference_runner()
    context = make_context(runner, suffix)
    genesis = initialize_capacity_state(runner)
    capacity_state, grant, _ = reserve_capacity(
        genesis,
        *context[:4],
        runner,
        context[4],
    )
    capacity_store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    capacity_store.initialize(runner, genesis)
    capacity_store.commit(runner, genesis.digest, capacity_state)

    intent = prepare_dispatch_intent(
        capacity_state,
        runner,
        grant.lease,
        context[4],
    )
    dispatch_store = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    prepared = dispatch_store.initialize(intent)
    return (
        runner,
        context,
        capacity_store,
        capacity_state,
        grant,
        intent,
        dispatch_store,
        prepared,
    )


def test_prepared_restart_authorizes_begin_submission_only(tmp_path):
    runner, _, _, _, _, intent, _, prepared = prepare_store(tmp_path, "prepared")
    restarted = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    report = recover_dispatch_after_restart(restarted, runner.runner_id)
    assert report.prepared_count == 1
    assert report.submission_unknown_count == 0
    assert report.observed_count == 0
    assert report.items[0].intent_id == intent.intent_id
    assert report.items[0].recovery_action == "begin_submission"
    assert report.items[0].blind_resubmission_authorized is False
    assert report.items[0].provider_outcome_inferred is False
    assert verify_dispatch_recovery(restarted, report)
    assert restarted.load(intent.intent_id) == prepared


def test_submission_unknown_restart_requires_reconciliation_not_resubmit(tmp_path):
    runner, _, capacity_store, _, _, intent, store, prepared = prepare_store(tmp_path, "unknown")
    unknown, permit = store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    assert unknown.status == "submission_unknown"
    assert verify_dispatch_permit(unknown, permit)
    assert permit.transport_authority is False

    restarted = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    report = recover_dispatch_after_restart(restarted, runner.runner_id)
    assert report.prepared_count == 0
    assert report.submission_unknown_count == 1
    assert report.items[0].recovery_action == "reconcile_provider"
    assert report.blind_resubmissions_authorized == 0
    assert report.provider_outcomes_inferred == 0
    with pytest.raises(DispatchIntentError):
        restarted.begin_submission(
            intent.intent_id,
            unknown.digest,
            capacity_store,
            runner,
        )


def test_live_dispatch_permit_binds_canonical_durable_capacity_head(tmp_path):
    runner, _, capacity_store, capacity_state, _, intent, store, prepared = prepare_store(tmp_path, "live")
    unknown, permit = store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    live = authorize_live_dispatch(unknown, permit, capacity_store, runner)
    _, head = capacity_store.load(runner)
    assert live.capacity_head_digest == head.digest
    assert live.capacity_state_digest == capacity_state.digest
    assert live.capacity_snapshot_digest == head.snapshot_digest
    assert live.capacity_generation == capacity_state.generation
    assert verify_live_dispatch_permit(unknown, permit, live, capacity_store, runner)


def test_revocation_after_live_permit_invalidates_transport_authority_even_with_stale_memory(tmp_path):
    (
        runner,
        context,
        capacity_store,
        stale_capacity_state,
        grant,
        intent,
        store,
        prepared,
    ) = prepare_store(tmp_path, "revoke")
    unknown, permit = store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    live = authorize_live_dispatch(unknown, permit, capacity_store, runner)

    revoked = revoke_session(context[3])
    released, _, _ = release_capacity_for_revocation(
        stale_capacity_state,
        runner,
        grant.lease,
        revoked,
    )
    capacity_store.commit(runner, stale_capacity_state.digest, released)
    assert stale_capacity_state.active_leases == (grant.lease,)
    assert released.active_leases == ()

    # Keeping the old replay-valid state in memory must not restore authority.
    assert not verify_live_dispatch_permit(unknown, permit, live, capacity_store, runner)
    with pytest.raises(DispatchIntentError, match="no longer active"):
        authorize_live_dispatch(unknown, permit, capacity_store, runner)


def test_unrelated_durable_capacity_generation_change_requires_live_permit_refresh(tmp_path):
    runner = replace(reference_runner(), max_parallelism=2)
    (
        _,
        _,
        capacity_store,
        first_state,
        first_grant,
        intent,
        store,
        prepared,
    ) = prepare_store(tmp_path, "generation-a", runner=runner)
    unknown, permit = store.begin_submission(intent.intent_id, prepared.digest, capacity_store, runner)
    live = authorize_live_dispatch(unknown, permit, capacity_store, runner)

    second = make_context(runner, "generation-b")
    advanced, _, _ = reserve_capacity(first_state, *second[:4], runner, second[4])
    capacity_store.commit(runner, first_state.digest, advanced)
    assert advanced.generation == first_state.generation + 1
    assert any(lease.lease_id == first_grant.lease.lease_id for lease in advanced.active_leases)
    assert not verify_live_dispatch_permit(unknown, permit, live, capacity_store, runner)

    refreshed = authorize_live_dispatch(unknown, permit, capacity_store, runner)
    assert refreshed.capacity_state_digest == advanced.digest
    assert refreshed.digest != live.digest
    assert verify_live_dispatch_permit(unknown, permit, refreshed, capacity_store, runner)


def test_stale_begin_submission_compare_and_swap_is_rejected(tmp_path):
    runner, _, capacity_store, _, _, intent, store_a, prepared = prepare_store(tmp_path, "cas")
    store_b = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    store_a.begin_submission(intent.intent_id, prepared.digest, capacity_store, runner)
    with pytest.raises(DispatchIntentError, match="stale durable dispatch intent state"):
        store_b.begin_submission(intent.intent_id, prepared.digest, capacity_store, runner)


def test_begin_submission_rejects_intent_after_durable_capacity_release(tmp_path):
    (
        runner,
        context,
        capacity_store,
        capacity_state,
        grant,
        intent,
        store,
        prepared,
    ) = prepare_store(tmp_path, "released-before-begin")
    revoked = revoke_session(context[3])
    released, _, _ = release_capacity_for_revocation(
        capacity_state,
        runner,
        grant.lease,
        revoked,
    )
    capacity_store.commit(runner, capacity_state.digest, released)
    with pytest.raises(DispatchIntentError, match="active capacity lease"):
        store.begin_submission(intent.intent_id, prepared.digest, capacity_store, runner)


def test_observed_outcome_closes_ambiguity_and_restart_is_terminal(tmp_path):
    runner, context, capacity_store, _, _, intent, store, prepared = prepare_store(tmp_path, "observed")
    unknown, permit = store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    authorize_live_dispatch(unknown, permit, capacity_store, runner)
    outcome = failure_outcome(context, runner)
    observed = store.record_observed(
        intent.intent_id,
        unknown.digest,
        *context[:4],
        runner,
        outcome,
    )
    assert observed.status == "observed"
    assert observed.provider_invocation_id == outcome.receipt.provider_invocation_id
    assert observed.receipt_digest == outcome.receipt.digest
    assert observed.outcome_digest == outcome.digest

    restarted = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    report = recover_dispatch_after_restart(restarted, runner.runner_id)
    assert report.observed_count == 1
    assert report.items[0].recovery_action == "none"
    assert report.blind_resubmissions_authorized == 0


def test_durable_row_tampering_fails_closed(tmp_path):
    runner, _, _, _, _, intent, store, _ = prepare_store(tmp_path, "tamper")
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "UPDATE dispatch_intents SET state_digest = ? WHERE intent_id = ?",
            (D, intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="row metadata mismatch"):
        store.load(intent.intent_id)
    with pytest.raises(DispatchIntentError):
        recover_dispatch_after_restart(store, runner.runner_id)


def test_serialized_state_tampering_fails_closed(tmp_path):
    _, _, _, _, _, intent, store, _ = prepare_store(tmp_path, "json-tamper")
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        raw = connection.execute(
            "SELECT state_json FROM dispatch_intents WHERE intent_id = ?",
            (intent.intent_id,),
        ).fetchone()[0]
        data = json.loads(raw)
        data["revision"] = 9
        connection.execute(
            "UPDATE dispatch_intents SET state_json = ? WHERE intent_id = ?",
            (json.dumps(data), intent.intent_id),
        )
    with pytest.raises(DispatchIntentError):
        store.load(intent.intent_id)


def test_live_permit_tampering_is_detected(tmp_path):
    runner, _, capacity_store, _, _, intent, store, prepared = prepare_store(tmp_path, "permit-tamper")
    unknown, permit = store.begin_submission(intent.intent_id, prepared.digest, capacity_store, runner)
    live = authorize_live_dispatch(unknown, permit, capacity_store, runner)
    tampered = replace(live, request_digest=D)
    assert not verify_live_dispatch_permit(unknown, permit, tampered, capacity_store, runner)
