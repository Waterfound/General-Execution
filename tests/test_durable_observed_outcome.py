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
    ResultEnvelope,
    RunnerRegistry,
    SqliteCapacityHeadStore,
    admit_physical_observation,
    authorize_physical_attempt,
    bind_session,
    initialize_capacity_state,
    observe_completed,
    observe_failure,
    plan_execution,
    reference_runner,
    reserve_capacity,
    start_session,
)
from general_execution.dispatch import DispatchIntentError, prepare_dispatch_intent
from general_execution.durable import DurableCapacityError
from general_execution.observed import (
    SqliteDurableObservedOutcomeStore,
    release_observed_capacity_after_restart,
)
from general_execution.physical_wire import (
    PhysicalOutcomeCodecError,
    deserialize_physical_outcome,
    serialize_physical_outcome,
)

D = "sha256:" + "f" * 64


def make_context(suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-observed-outcome",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable observed outcome {suffix}",
        source_revision=f"source-observed-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://observed/{suffix}", D),),
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
        invocation_id=f"gei-observed-{suffix}-1",
    )
    return runner, spec, registry, plan, session, authorization


def failure_outcome(ctx, *, status="timed_out", provider_id="provider-timeout"):
    runner, spec, registry, plan, session, authorization = ctx
    observation = observe_failure(
        authorization,
        status,
        failure_code=f"reference.{status}",
        provider_invocation_id=provider_id,
    )
    return admit_physical_observation(
        spec, registry, plan, session, runner, authorization, observation
    )


def completed_outcome(ctx):
    runner, spec, registry, plan, session, authorization = ctx
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=session.attempt,
        status="completed",
        evidence=(
            ArtifactRef(
                REFERENCE_EVIDENCE,
                "ge+reference://observed/completed",
                D,
            ),
        ),
        summary="Completed durable observed outcome.",
    )
    observation = observe_completed(
        authorization,
        result,
        provider_invocation_id="provider-completed",
    )
    return admit_physical_observation(
        spec, registry, plan, session, runner, authorization, observation
    )


def prepare_store(tmp_path, suffix="1"):
    ctx = make_context(suffix)
    runner, spec, registry, plan, session, authorization = ctx
    genesis = initialize_capacity_state(runner)
    capacity_state, grant, _ = reserve_capacity(
        genesis, spec, registry, plan, session, runner, authorization
    )
    capacity_store = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    capacity_store.initialize(runner, genesis)
    capacity_store.commit(runner, genesis.digest, capacity_state)

    intent = prepare_dispatch_intent(capacity_state, runner, grant.lease, authorization)
    dispatch_store = SqliteDurableObservedOutcomeStore(tmp_path / "dispatch.db")
    prepared = dispatch_store.initialize(intent)
    unknown, _ = dispatch_store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_store,
        runner,
    )
    return ctx, capacity_store, capacity_state, grant, intent, dispatch_store, unknown


def test_failure_outcome_codec_round_trip_is_exact():
    outcome = failure_outcome(make_context("codec-failure"))
    encoded = serialize_physical_outcome(outcome)
    assert deserialize_physical_outcome(encoded) == outcome
    assert serialize_physical_outcome(deserialize_physical_outcome(encoded)) == encoded


def test_completed_outcome_codec_preserves_full_result():
    outcome = completed_outcome(make_context("codec-completed"))
    recovered = deserialize_physical_outcome(serialize_physical_outcome(outcome))
    assert recovered == outcome
    assert recovered.result == outcome.result
    assert recovered.result.digest == outcome.result.digest


def test_codec_rejects_changed_nested_result():
    outcome = completed_outcome(make_context("codec-tamper"))
    data = json.loads(serialize_physical_outcome(outcome))
    data["result"]["summary"] = "changed after admission"
    with pytest.raises(PhysicalOutcomeCodecError):
        deserialize_physical_outcome(json.dumps(data))


def test_observed_state_and_full_outcome_survive_reopen(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "reopen")
    outcome = failure_outcome(ctx)
    observed = store.record_observed(
        intent.intent_id,
        unknown.digest,
        *ctx[1:5],
        ctx[0],
        outcome,
    )
    reopened = SqliteDurableObservedOutcomeStore(tmp_path / "dispatch.db")
    durable = reopened.load_observed_outcome(intent.intent_id)
    assert reopened.load(intent.intent_id) == observed
    assert durable.outcome == outcome
    assert durable.outcome_digest == outcome.digest
    assert durable.receipt_digest == outcome.receipt.digest


def test_lost_ack_replay_of_exact_outcome_is_idempotent(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "lost-ack")
    outcome = failure_outcome(ctx)
    first = store.record_observed(
        intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome
    )
    replay = store.record_observed(
        intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome
    )
    assert replay == first
    assert store.load_observed_outcome(intent.intent_id).outcome == outcome


def test_conflicting_second_outcome_is_rejected(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "conflict")
    first = failure_outcome(ctx, provider_id="provider-a")
    second = failure_outcome(ctx, status="cancelled", provider_id="provider-b")
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], first)
    with pytest.raises(DispatchIntentError):
        store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], second)


def test_observed_state_missing_outcome_bytes_fails_closed(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "missing")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "DELETE FROM dispatch_observed_outcomes WHERE intent_id = ?",
            (intent.intent_id,),
        )
    with pytest.raises(DispatchIntentError, match="missing durable physical outcome bytes"):
        store.load_observed_outcome(intent.intent_id)


def test_outcome_metadata_tamper_fails_closed(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "metadata-tamper")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "UPDATE dispatch_observed_outcomes SET receipt_digest = ? WHERE intent_id = ?",
            (D, intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="metadata mismatch"):
        store.load_observed_outcome(intent.intent_id)


def test_outcome_payload_tamper_fails_closed(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "payload-tamper")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        raw = connection.execute(
            "SELECT outcome_json FROM dispatch_observed_outcomes WHERE intent_id = ?",
            (intent.intent_id,),
        ).fetchone()[0]
        data = json.loads(raw)
        data["receipt"]["failure_code"] = "changed.failure"
        connection.execute(
            "UPDATE dispatch_observed_outcomes SET outcome_json = ? WHERE intent_id = ?",
            (json.dumps(data), intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="payload is invalid"):
        store.load_observed_outcome(intent.intent_id)


def test_recover_observed_for_runner_returns_exact_outcome(tmp_path):
    ctx, _, _, _, intent, store, unknown = prepare_store(tmp_path, "runner-recovery")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    recovered = store.recover_observed_for_runner(ctx[0].runner_id)
    assert len(recovered) == 1
    assert recovered[0].outcome == outcome


def test_restart_releases_capacity_from_durable_outcome(tmp_path):
    ctx, capacity_store, _, grant, intent, store, unknown = prepare_store(tmp_path, "release")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)

    restarted_dispatch = SqliteDurableObservedOutcomeStore(tmp_path / "dispatch.db")
    restarted_capacity = SqliteCapacityHeadStore(tmp_path / "capacity.db")
    recovery = release_observed_capacity_after_restart(
        restarted_dispatch,
        restarted_capacity,
        intent.intent_id,
        *ctx[1:5],
        ctx[0],
    )
    state, _ = restarted_capacity.load(ctx[0])
    assert recovery.idempotent is False
    assert state.active_leases == ()
    assert state.releases[-1].lease_digest == grant.lease.digest
    assert state.releases[-1].outcome_digest == outcome.digest


def test_restart_capacity_release_replay_is_idempotent(tmp_path):
    ctx, capacity_store, _, _, intent, store, unknown = prepare_store(tmp_path, "release-replay")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    first = release_observed_capacity_after_restart(
        store, capacity_store, intent.intent_id, *ctx[1:5], ctx[0]
    )
    second = release_observed_capacity_after_restart(
        store, capacity_store, intent.intent_id, *ctx[1:5], ctx[0]
    )
    assert first.idempotent is False
    assert second.idempotent is True
    assert second.release_digest == first.release_digest


def test_restart_release_rejects_wrong_execution_context(tmp_path):
    ctx, capacity_store, _, _, intent, store, unknown = prepare_store(tmp_path, "wrong-context")
    outcome = failure_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    other = make_context("other-context")
    with pytest.raises(DispatchIntentError, match="no longer verifies"):
        release_observed_capacity_after_restart(
            store,
            capacity_store,
            intent.intent_id,
            *other[1:5],
            other[0],
        )


def test_completed_outcome_can_release_capacity_after_restart(tmp_path):
    ctx, capacity_store, _, _, intent, store, unknown = prepare_store(tmp_path, "completed-release")
    outcome = completed_outcome(ctx)
    store.record_observed(intent.intent_id, unknown.digest, *ctx[1:5], ctx[0], outcome)
    recovery = release_observed_capacity_after_restart(
        store, capacity_store, intent.intent_id, *ctx[1:5], ctx[0]
    )
    state, _ = capacity_store.load(ctx[0])
    assert recovery.idempotent is False
    assert state.releases[-1].transport_status == "completed"
    assert store.load_observed_outcome(intent.intent_id).outcome.result == outcome.result
