import sqlite3
from concurrent.futures import ThreadPoolExecutor

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
    build_durable_snapshot,
    initialize_capacity_state,
    observe_failure,
    plan_execution,
    recover_after_restart,
    reserve_capacity,
    start_session,
)
from general_execution.reattachment import assess_provider_status, build_status_probe
from general_execution.reconciliation import plan_provider_outcome_reconciliation, verify_reconciliation_plan
from general_execution.reference_bridge import (
    ReferenceBridgeError,
    query_reference_status,
    reattachable_reference_runner,
    record_reference_terminal,
    register_reference_invocation,
)
from general_execution.reference_registry import (
    ReferenceRegistryConflict,
    ReferenceRegistryIntegrityError,
    SQLiteReferenceJobRegistry,
)

D = "sha256:" + "c" * 64


def context(suffix="1"):
    runner = reattachable_reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-reference-provider-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Reference provider reattachment {suffix}",
        source_revision=f"source-reference-provider-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://reference-provider/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    execution_plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, execution_plan))
    authorization = authorize_physical_attempt(
        spec,
        registry,
        execution_plan,
        session,
        runner,
        invocation_id=f"gei-reference-provider-{suffix}",
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(
        state,
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
    )
    snapshot = build_durable_snapshot(state, runner)
    _, report = recover_after_restart(snapshot, runner)
    recovered = report.active_leases[0]
    probe = build_status_probe(snapshot, runner, recovered)
    return runner, spec, registry, execution_plan, session, authorization, snapshot, recovered, probe


def test_register_then_query_running_survives_registry_reopen(tmp_path):
    path = tmp_path / "provider.db"
    runner, _, _, _, _, authorization, _, _, probe = context()
    registry = SQLiteReferenceJobRegistry(path)
    key, receipt = register_reference_invocation(registry, authorization, runner)
    assert not receipt.idempotent
    assert receipt.provider_key == key.provider_key
    reopened = SQLiteReferenceJobRegistry(path)
    status = query_reference_status(reopened, probe)
    assert status.status == "running"
    assert status.provider_invocation_id == receipt.job_id


def test_repeat_registration_is_idempotent_and_keeps_same_job_id(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    runner, _, _, _, _, authorization, _, _, _ = context()
    key_a, first = register_reference_invocation(registry, authorization, runner)
    key_b, second = register_reference_invocation(registry, authorization, runner)
    assert key_a == key_b
    assert not first.idempotent
    assert second.idempotent
    assert first.job_id == second.job_id


def test_query_without_registration_returns_not_found(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    *_, probe = context()
    status = query_reference_status(registry, probe)
    assert status.status == "not_found"
    assert status.provider_invocation_id is None


def test_terminal_status_survives_reopen_and_feeds_reconciliation(tmp_path):
    path = tmp_path / "provider.db"
    registry = SQLiteReferenceJobRegistry(path)
    ctx = context()
    runner, spec, runners, execution_plan, session, authorization, snapshot, recovered, probe = ctx
    key, receipt = register_reference_invocation(registry, authorization, runner)
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id=receipt.job_id,
    )
    assert not record_reference_terminal(registry, key, physical)

    reopened = SQLiteReferenceJobRegistry(path)
    status = query_reference_status(reopened, probe)
    assert status.status == "terminal"
    assert status.physical_observation == physical

    assessment, outcome = assess_provider_status(
        snapshot,
        spec,
        runners,
        execution_plan,
        session,
        runner,
        authorization,
        probe,
        status,
    )
    assert assessment.disposition == "terminal_outcome"
    assert outcome is not None
    reconciliation = plan_provider_outcome_reconciliation(
        snapshot,
        spec,
        runners,
        execution_plan,
        session,
        runner,
        recovered,
        outcome,
    )
    assert verify_reconciliation_plan(snapshot, runner, reconciliation)
    assert reconciliation.target_snapshot.state.active_leases == ()


def test_same_terminal_observation_replay_is_idempotent(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    runner, _, _, _, _, authorization, _, _, _ = context()
    key, receipt = register_reference_invocation(registry, authorization, runner)
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id=receipt.job_id,
    )
    assert not record_reference_terminal(registry, key, physical)
    assert record_reference_terminal(registry, key, physical)


def test_different_terminal_observation_cannot_replace_canonical_terminal(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    runner, _, _, _, _, authorization, _, _, _ = context()
    key, receipt = register_reference_invocation(registry, authorization, runner)
    first = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id=receipt.job_id,
    )
    second = observe_failure(
        authorization,
        "cancelled",
        failure_code="reference.cancelled",
        provider_invocation_id=receipt.job_id,
    )
    record_reference_terminal(registry, key, first)
    with pytest.raises(ReferenceRegistryConflict):
        record_reference_terminal(registry, key, second)


def test_terminal_observation_with_other_job_id_is_rejected(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    runner, _, _, _, _, authorization, _, _, _ = context()
    key, _ = register_reference_invocation(registry, authorization, runner)
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="gerj-not-this-job",
    )
    with pytest.raises(ReferenceRegistryConflict):
        record_reference_terminal(registry, key, physical)


def test_two_concurrent_registrations_create_one_job_identity(tmp_path):
    path = tmp_path / "provider.db"
    runner, _, _, _, _, authorization, _, _, _ = context()

    def register_once():
        registry = SQLiteReferenceJobRegistry(path)
        _, receipt = register_reference_invocation(registry, authorization, runner)
        return receipt.job_id, receipt.idempotent

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register_once(), range(2)))
    assert results[0][0] == results[1][0]
    assert sorted(flag for _, flag in results) == [False, True]


def test_registry_schema_change_is_rejected_on_reopen(tmp_path):
    path = tmp_path / "provider.db"
    SQLiteReferenceJobRegistry(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_reference_registry_metadata SET value = 'unsupported' WHERE key = 'schema_version'"
        )
    with pytest.raises(ReferenceRegistryIntegrityError):
        SQLiteReferenceJobRegistry(path)


def test_memory_registry_is_rejected():
    with pytest.raises(ValueError):
        SQLiteReferenceJobRegistry(":memory:")


def test_non_reattachable_reference_runner_cannot_register(tmp_path):
    from general_execution import reference_runner

    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-non-reattachable",
        task_kind=REFERENCE_TASK_KIND,
        objective="Non reattachable reference runner",
        source_revision="source-non-reattachable",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://non-reattachable", D),),
    )
    runners = RunnerRegistry((runner,))
    execution_plan = plan_execution(spec, runners)
    session = start_session(bind_session(spec, runners, execution_plan))
    authorization = authorize_physical_attempt(spec, runners, execution_plan, session, runner)
    with pytest.raises(ReferenceBridgeError):
        register_reference_invocation(
            SQLiteReferenceJobRegistry(tmp_path / "provider.db"),
            authorization,
            runner,
        )


def test_registration_after_terminal_does_not_reset_job_to_running(tmp_path):
    registry = SQLiteReferenceJobRegistry(tmp_path / "provider.db")
    runner, _, _, _, _, authorization, _, _, probe = context()
    key, receipt = register_reference_invocation(registry, authorization, runner)
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id=receipt.job_id,
    )
    record_reference_terminal(registry, key, physical)
    _, repeated = register_reference_invocation(registry, authorization, runner)
    assert repeated.idempotent
    assert query_reference_status(registry, probe).status == "terminal"
