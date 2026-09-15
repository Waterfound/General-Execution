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
    authorize_physical_attempt,
    bind_session,
    initialize_capacity_state,
    plan_execution,
    reference_runner,
    reserve_capacity,
    start_session,
)
from general_execution.dispatch import (
    DispatchIntentError,
    SqliteDispatchIntentStore,
    prepare_dispatch_intent,
    recover_dispatch_after_restart,
)

D = "sha256:" + "d" * 64


def prepared_store(tmp_path, suffix):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-dispatch-metadata",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Dispatch metadata {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://dispatch-metadata/{suffix}", D),),
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
    genesis = initialize_capacity_state(runner)
    capacity_state, grant, _ = reserve_capacity(
        genesis,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    intent = prepare_dispatch_intent(capacity_state, runner, grant.lease, authorization)
    store = SqliteDispatchIntentStore(tmp_path / "dispatch.db")
    prepared = store.initialize(intent)
    return runner, capacity_state, intent, store, prepared


def test_runner_metadata_tampering_cannot_hide_ambiguous_intent(tmp_path):
    runner, _, intent, store, _ = prepared_store(tmp_path, "runner-hide")
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "UPDATE dispatch_intents SET runner_id = ? WHERE intent_id = ?",
            ("other-runner", intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="row metadata mismatch"):
        recover_dispatch_after_restart(store, runner.runner_id)


def test_lease_metadata_tampering_fails_closed(tmp_path):
    _, _, intent, store, _ = prepared_store(tmp_path, "lease-hide")
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "UPDATE dispatch_intents SET lease_id = ? WHERE intent_id = ?",
            ("other-lease", intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="row metadata mismatch"):
        store.load(intent.intent_id)


def test_intent_id_metadata_tampering_is_found_by_recovery_scan(tmp_path):
    runner, _, intent, store, _ = prepared_store(tmp_path, "intent-hide")
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        connection.execute(
            "UPDATE dispatch_intents SET intent_id = ? WHERE intent_id = ?",
            ("gedi-hidden-row", intent.intent_id),
        )
    with pytest.raises(DispatchIntentError, match="row metadata mismatch"):
        recover_dispatch_after_restart(store, runner.runner_id)


def test_durable_dispatch_permit_explicitly_has_no_transport_authority(tmp_path):
    runner, capacity_state, intent, store, prepared = prepared_store(tmp_path, "authority")
    unknown, permit = store.begin_submission(
        intent.intent_id,
        prepared.digest,
        capacity_state,
        runner,
    )
    assert unknown.status == "submission_unknown"
    assert permit.transport_authority is False
    with pytest.raises(ValueError, match="cannot grant transport authority"):
        replace(permit, transport_authority=True)
