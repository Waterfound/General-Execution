import sqlite3

import pytest

from general_execution.adapter import (
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    reference_runner,
)
from general_execution.canonical_cold import (
    CanonicalColdError,
    prepare_canonical_cold_ambiguity,
    recover_canonical_cold_ambiguity,
)
from general_execution.capacity import initialize_capacity_state, reserve_capacity
from general_execution.cold_guard import bootstrap_cold_coordinator_strict
from general_execution.coordinator_context import (
    CoordinatorContextIntegrityError,
    SqliteCoordinatorContextStore,
    build_coordinator_context,
)
from general_execution.dispatch import SqliteDispatchIntentStore
from general_execution.durable import SqliteCapacityHeadStore
from general_execution.models import ArtifactRef, ExecutionSpec, RunnerRegistry
from general_execution.physical import authorize_physical_attempt
from general_execution.planner import plan_execution
from general_execution.session import bind_session, start_session


def _paths(tmp_path):
    return (
        tmp_path / "capacity.db",
        tmp_path / "context.db",
        tmp_path / "dispatch.db",
    )


def _candidate(tmp_path, suffix="cut"):
    capacity_path, context_path, dispatch_path = _paths(tmp_path)
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-canonical-cold-test",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"canonical cut point {suffix}",
        source_revision=f"source-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(
            ArtifactRef(
                "package",
                f"bc://canonical-cut/{suffix}",
                "sha256:" + "c" * 64,
            ),
        ),
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
        invocation_id=f"gei-canonical-cut-{suffix}",
    )
    genesis = initialize_capacity_state(runner)
    reserved, grant, _ = reserve_capacity(
        genesis,
        spec,
        registry,
        plan,
        session,
        runner,
        authorization,
    )
    context = build_coordinator_context(
        reserved,
        spec,
        registry,
        plan,
        session,
        runner,
        grant.lease,
        authorization,
    )
    capacity = SqliteCapacityHeadStore(capacity_path)
    contexts = SqliteCoordinatorContextStore(context_path)
    dispatch = SqliteDispatchIntentStore(dispatch_path)
    capacity.initialize(runner, genesis)
    return {
        "paths": (capacity_path, context_path, dispatch_path),
        "runner": runner,
        "genesis": genesis,
        "reserved": reserved,
        "context": context,
        "capacity": capacity,
        "contexts": contexts,
        "dispatch": dispatch,
    }


def _bootstrap(candidate):
    return bootstrap_cold_coordinator_strict(
        candidate["contexts"], candidate["capacity"], candidate["dispatch"]
    )


def test_context_only_is_inert_orphan(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    assert _bootstrap(candidate) == ()


def test_context_plus_prepared_without_capacity_commit_is_inert(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    prepared = candidate["dispatch"].initialize(candidate["context"].dispatch_intent)
    assert prepared.status == "prepared"
    assert _bootstrap(candidate) == ()


def test_capacity_commit_after_context_and_prepared_recovers_begin_submission(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    prepared = candidate["dispatch"].initialize(candidate["context"].dispatch_intent)
    candidate["capacity"].commit(
        candidate["runner"], candidate["genesis"].digest, candidate["reserved"]
    )

    (binding,) = _bootstrap(candidate)
    assert binding.dispatch_state == prepared
    assert binding.recovery_action == "begin_submission"
    assert binding.context == candidate["context"]


def test_submission_unknown_recovers_only_reconcile_provider(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    prepared = candidate["dispatch"].initialize(candidate["context"].dispatch_intent)
    candidate["capacity"].commit(
        candidate["runner"], candidate["genesis"].digest, candidate["reserved"]
    )
    unknown, permit = candidate["dispatch"].begin_submission(
        candidate["context"].dispatch_intent.intent_id,
        prepared.digest,
        candidate["capacity"],
        candidate["runner"],
    )

    (binding,) = _bootstrap(candidate)
    assert unknown.status == "submission_unknown"
    assert permit.transport_authority is False
    assert binding.dispatch_state == unknown
    assert binding.recovery_action == "reconcile_provider"


def test_active_lease_without_durable_dispatch_intent_fails_closed(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    candidate["capacity"].commit(
        candidate["runner"], candidate["genesis"].digest, candidate["reserved"]
    )

    with pytest.raises(CoordinatorContextIntegrityError, match="missing its durable dispatch intent"):
        _bootstrap(candidate)


def test_corrupt_capacity_metadata_is_not_treated_as_orphan(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    candidate["dispatch"].initialize(candidate["context"].dispatch_intent)
    candidate["capacity"].commit(
        candidate["runner"], candidate["genesis"].digest, candidate["reserved"]
    )

    capacity_path = candidate["paths"][0]
    with sqlite3.connect(capacity_path) as connection:
        connection.execute(
            "UPDATE capacity_heads SET runner_capability_digest = ? WHERE runner_id = ?",
            ("sha256:" + "0" * 64, candidate["runner"].runner_id),
        )

    with pytest.raises(
        CoordinatorContextIntegrityError,
        match="capacity head failed integrity verification",
    ):
        _bootstrap(candidate)


def test_context_store_schema_drift_fails_closed(tmp_path):
    candidate = _candidate(tmp_path)
    context_path = candidate["paths"][1]
    with sqlite3.connect(context_path) as connection:
        connection.execute(
            "UPDATE coordinator_context_metadata SET value = ? WHERE key = 'schema_version'",
            ("ge.coordinator-recovery-context-store.v999",),
        )

    with pytest.raises(CoordinatorContextIntegrityError, match="unsupported coordinator context store schema"):
        SqliteCoordinatorContextStore(context_path)


def test_context_row_metadata_tamper_fails_closed(tmp_path):
    candidate = _candidate(tmp_path)
    candidate["contexts"].save(candidate["context"])
    context_path = candidate["paths"][1]
    with sqlite3.connect(context_path) as connection:
        connection.execute(
            "UPDATE coordinator_contexts SET context_digest = ?",
            ("sha256:" + "f" * 64,),
        )

    with pytest.raises(CoordinatorContextIntegrityError, match="row metadata mismatch"):
        candidate["contexts"].candidates()


def test_full_canonical_cold_recovery_reconstructs_and_preserves_ambiguity(tmp_path):
    capacity_path, context_path, dispatch_path = _paths(tmp_path)
    prepared = prepare_canonical_cold_ambiguity(
        capacity_path, context_path, dispatch_path, suffix="e2e"
    )
    recovered = recover_canonical_cold_ambiguity(
        capacity_path, context_path, dispatch_path
    )

    assert recovered.context_mode == "cold_reconstructed"
    assert recovered.context_id == prepared.context_id
    assert recovered.context_digest == prepared.context_digest
    assert recovered.invocation_id == prepared.invocation_id
    assert recovered.recovery_action == "reconcile_provider"
    assert recovered.blind_resubmissions_authorized == 0
    assert recovered.provider_outcomes_inferred == 0


def test_lost_ack_prepare_replay_is_exact_and_does_not_advance_state(tmp_path):
    paths = _paths(tmp_path)
    first = prepare_canonical_cold_ambiguity(*paths, suffix="lost-ack")
    capacity_path, _, dispatch_path = paths

    runner = reference_runner()
    state_before, head_before = SqliteCapacityHeadStore(capacity_path).load(runner)
    dispatch_before = SqliteDispatchIntentStore(dispatch_path).load(first.intent_id)

    second = prepare_canonical_cold_ambiguity(*paths, suffix="lost-ack")
    state_after, head_after = SqliteCapacityHeadStore(capacity_path).load(runner)
    dispatch_after = SqliteDispatchIntentStore(dispatch_path).load(first.intent_id)

    assert second == first
    assert second.digest == first.digest
    assert state_after == state_before
    assert head_after == head_before
    assert dispatch_after == dispatch_before
    assert dispatch_after.status == "submission_unknown"


def test_canonical_cold_artifacts_are_path_independent(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    p1 = prepare_canonical_cold_ambiguity(*_paths(first), suffix="same")
    r1 = recover_canonical_cold_ambiguity(*_paths(first))
    p2 = prepare_canonical_cold_ambiguity(*_paths(second), suffix="same")
    r2 = recover_canonical_cold_ambiguity(*_paths(second))

    assert p1 == p2
    assert r1 == r2
    assert p1.digest == p2.digest
    assert r1.digest == r2.digest


def test_store_paths_must_be_distinct(tmp_path):
    shared = tmp_path / "shared.db"
    with pytest.raises(CanonicalColdError, match="distinct files"):
        prepare_canonical_cold_ambiguity(shared, shared, tmp_path / "dispatch.db")
