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
    authorize_physical_attempt,
    bind_session,
    build_durable_snapshot,
    initialize_capacity_state,
    plan_execution,
    reattachable_reference_runner,
    recover_after_restart,
    reserve_capacity,
    start_session,
)
from general_execution.recovery_context import (
    RecoveryContextConflict,
    RecoveryContextIntegrityError,
    SQLiteRecoveryContextStore,
    build_recovery_context,
    load_recovery_context,
    recovery_context_to_dict,
    serialize_recovery_context,
    verify_recovery_context,
)

D = "sha256:" + "e" * 64


def spec_for(suffix):
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-recovery-context",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable recovery context {suffix}",
        source_revision=f"source-recovery-context-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://recovery-context/{suffix}", D),),
    )


def first_context(max_parallelism=1):
    runner = replace(reattachable_reference_runner(), max_parallelism=max_parallelism)
    spec = spec_for("one")
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec, registry, plan, session, runner, invocation_id="gei-recovery-context-one"
    )
    state = initialize_capacity_state(runner)
    state, _, _ = reserve_capacity(
        state, spec, registry, plan, session, runner, authorization
    )
    anchor = build_durable_snapshot(state, runner)
    _, report = recover_after_restart(anchor, runner)
    recovered = report.active_leases[0]
    context = build_recovery_context(
        anchor, spec, registry, plan, session, runner, authorization, recovered
    )
    return runner, spec, registry, plan, session, authorization, anchor, recovered, context


def advance_with_independent_second_lease(runner, registry, anchor):
    spec = spec_for("two")
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    authorization = authorize_physical_attempt(
        spec, registry, plan, session, runner, invocation_id="gei-recovery-context-two"
    )
    state, _, _ = reserve_capacity(
        anchor.state, spec, registry, plan, session, runner, authorization
    )
    current = build_durable_snapshot(state, runner, previous=anchor)
    return current


def test_context_round_trip_reconstructs_exact_execution_objects():
    *_, anchor, _, context = first_context()
    payload = serialize_recovery_context(context)
    loaded = load_recovery_context(payload, anchor, expected_context_digest=context.digest)
    assert loaded == context
    assert loaded.spec == context.spec
    assert loaded.registry == context.registry
    assert loaded.plan == context.plan
    assert loaded.session == context.session
    assert loaded.authorization == context.authorization


def test_context_remains_valid_after_unrelated_capacity_head_advance():
    runner, _, registry, _, _, _, anchor, _, context = first_context(max_parallelism=2)
    current = advance_with_independent_second_lease(runner, registry, anchor)
    assert current.head.digest != anchor.head.digest
    assert verify_recovery_context(current, context)
    loaded = load_recovery_context(serialize_recovery_context(context), current)
    assert loaded == context


def test_context_fails_if_bound_lease_is_no_longer_active():
    runner, _, registry, _, _, _, anchor, recovered, context = first_context(max_parallelism=2)
    current = advance_with_independent_second_lease(runner, registry, anchor)
    first_active = [lease for lease in current.state.active_leases if lease.lease_id == recovered.lease_id]
    assert len(first_active) == 1
    # Removing the lease outside the canonical transition protocol cannot verify as a capacity state.
    changed_state = replace(
        current.state,
        active_leases=tuple(
            lease for lease in current.state.active_leases if lease.lease_id != recovered.lease_id
        ),
    )
    changed = replace(current, state=changed_state)
    assert not verify_recovery_context(changed, context)


def test_missing_nested_spec_schema_is_rejected():
    *_, anchor, _, context = first_context()
    data = recovery_context_to_dict(context)
    del data["spec"]["schema_version"]
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    with pytest.raises(RecoveryContextIntegrityError):
        load_recovery_context(payload, anchor)


def test_changed_session_binding_is_rejected():
    *_, anchor, _, context = first_context()
    changed = replace(context, session=replace(context.session, attempt=2))
    assert not verify_recovery_context(anchor, changed)


def test_store_save_reopen_and_load_for_recovered(tmp_path):
    path = tmp_path / "contexts.db"
    runner, _, _, _, _, _, anchor, recovered, context = first_context()
    receipt = SQLiteRecoveryContextStore(path).save(context, anchor)
    assert not receipt.idempotent
    reopened = SQLiteRecoveryContextStore(path)
    loaded, loaded_runner = reopened.load_for_recovered(anchor, recovered)
    assert loaded == context
    assert loaded_runner == runner


def test_exact_store_replay_is_idempotent(tmp_path):
    store = SQLiteRecoveryContextStore(tmp_path / "contexts.db")
    *_, anchor, _, context = first_context()
    first = store.save(context, anchor)
    second = store.save(context, anchor)
    assert not first.idempotent
    assert second.idempotent
    assert first.context_id == second.context_id
    assert first.context_digest == second.context_digest


def test_same_authorization_cannot_be_reanchored_silently(tmp_path):
    store = SQLiteRecoveryContextStore(tmp_path / "contexts.db")
    runner, spec, registry, plan, session, authorization, anchor, _, context = first_context(max_parallelism=2)
    store.save(context, anchor)
    current = advance_with_independent_second_lease(runner, registry, anchor)
    _, report = recover_after_restart(current, runner)
    recovered = next(lease for lease in report.active_leases if lease.authorization_id == authorization.authorization_id)
    reanchored = build_recovery_context(
        current, spec, registry, plan, session, runner, authorization, recovered
    )
    assert reanchored.digest != context.digest
    with pytest.raises(RecoveryContextConflict):
        store.save(reanchored, current)


def test_bootstrap_candidates_reconstruct_runner_without_live_coordinator_state(tmp_path):
    path = tmp_path / "contexts.db"
    runner, _, _, _, _, _, anchor, _, context = first_context()
    SQLiteRecoveryContextStore(path).save(context, anchor)
    candidates = SQLiteRecoveryContextStore(path).bootstrap_candidates()
    assert candidates == ((context, runner),)


def test_store_metadata_corruption_is_rejected(tmp_path):
    path = tmp_path / "contexts.db"
    _, _, _, _, _, _, anchor, _, context = first_context()
    store = SQLiteRecoveryContextStore(path)
    store.save(context, anchor)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_recovery_contexts SET context_digest = ? WHERE authorization_id = ?",
            ("sha256:" + "0" * 64, context.authorization.authorization_id),
        )
    with pytest.raises(RecoveryContextIntegrityError):
        SQLiteRecoveryContextStore(path).bootstrap_candidates()


def test_store_schema_change_is_rejected_on_reopen(tmp_path):
    path = tmp_path / "contexts.db"
    SQLiteRecoveryContextStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_recovery_context_metadata SET value = 'unsupported' WHERE key = 'schema_version'"
        )
    with pytest.raises(RecoveryContextIntegrityError):
        SQLiteRecoveryContextStore(path)


def test_memory_store_is_rejected():
    with pytest.raises(ValueError):
        SQLiteRecoveryContextStore(":memory:")


def test_load_for_unknown_authorization_is_rejected(tmp_path):
    store = SQLiteRecoveryContextStore(tmp_path / "contexts.db")
    *_, anchor, recovered, _ = first_context()
    unknown = replace(recovered, authorization_id="gea-unknown")
    with pytest.raises(RecoveryContextIntegrityError):
        store.load_for_recovered(anchor, unknown)
