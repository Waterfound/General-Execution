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
    admit_physical_observation,
    authorize_physical_attempt,
    bind_session,
    build_durable_snapshot,
    initialize_capacity_state,
    observe_completed,
    observe_failure,
    plan_execution,
    recover_after_restart,
    reference_runner,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.reconciliation import (
    ReconciliationConflict,
    ReconciliationError,
    commit_reconciliation,
    plan_provider_outcome_reconciliation,
    plan_revocation_reconciliation,
    verify_reconciliation_plan,
    verify_reconciliation_receipt,
)

D = "sha256:" + "a" * 64
ZERO = "sha256:" + "0" * 64


def recovery_context(path, suffix="1"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-recovery-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Recovery reconciliation {suffix}",
        source_revision=f"source-recovery-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://recovery/{suffix}", D),),
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
        invocation_id=f"gei-recovery-{suffix}",
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
    store = SQLiteDurableHeadStore(path)
    store.compare_and_swap(snapshot, runner, expected_head_digest=None)
    return runner, spec, registry, execution_plan, session, authorization, snapshot, recovered, store


def timeout_outcome(context):
    runner, spec, registry, execution_plan, session, authorization, *_ = context
    observation = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-timeout-1",
    )
    return admit_physical_observation(
        spec,
        registry,
        execution_plan,
        session,
        runner,
        authorization,
        observation,
    )


def test_provider_outcome_plan_releases_exact_recovered_lease(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, _ = context
    outcome = timeout_outcome(context)
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, outcome
    )
    assert verify_reconciliation_plan(source, runner, plan)
    assert plan.target_snapshot.state.active_leases == ()
    assert plan.target_snapshot.head.previous_head_digest == source.head.digest


def test_provider_outcome_commit_advances_durable_head(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, store = context
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    target, persistence_receipt, receipt = commit_reconciliation(store, runner, plan)
    assert target == plan.target_snapshot
    assert store.load_current(runner) == target
    assert not receipt.idempotent
    assert verify_reconciliation_receipt(plan, persistence_receipt, receipt)


def test_lost_ack_replay_of_same_reconciliation_is_idempotent(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, store = context
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    commit_reconciliation(store, runner, plan)
    _, persistence_receipt, receipt = commit_reconciliation(store, runner, plan)
    assert persistence_receipt.idempotent
    assert receipt.idempotent
    assert verify_reconciliation_receipt(plan, persistence_receipt, receipt)


def test_revocation_can_resolve_unknown_lease(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, _, _, _, session, _, source, recovered, store = context
    revoked = revoke_session(session)
    plan = plan_revocation_reconciliation(source, runner, recovered, revoked)
    target, _, receipt = commit_reconciliation(store, runner, plan)
    assert target.state.active_leases == ()
    assert receipt.resolution_kind == "session_revoked"


def test_unrevoked_session_cannot_resolve_unknown_lease(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, _, _, _, session, _, source, recovered, _ = context
    with pytest.raises(ReconciliationError):
        plan_revocation_reconciliation(source, runner, recovered, session)


def test_tampered_recovered_lease_is_not_admitted(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, _ = context
    changed = replace(recovered, invocation_id="gei-not-the-recovered-attempt")
    with pytest.raises(ReconciliationConflict):
        plan_provider_outcome_reconciliation(
            source, spec, registry, execution_plan, session, runner, changed, timeout_outcome(context)
        )


def test_outcome_from_other_authorization_cannot_resolve_lease(tmp_path):
    context = recovery_context(tmp_path / "heads.db", "a")
    other = recovery_context(tmp_path / "other.db", "b")
    runner, spec, registry, execution_plan, session, _, source, recovered, _ = context
    with pytest.raises(ReconciliationError):
        plan_provider_outcome_reconciliation(
            source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(other)
        )


def test_provider_outcome_and_revocation_race_have_one_canonical_winner(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, store = context
    outcome_plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    revoked_plan = plan_revocation_reconciliation(source, runner, recovered, revoke_session(session))
    commit_reconciliation(store, runner, outcome_plan)
    with pytest.raises(ReconciliationConflict):
        commit_reconciliation(store, runner, revoked_plan)


def test_stale_plan_is_rejected_after_different_resolution(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, store = context
    old_plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    revocation = plan_revocation_reconciliation(source, runner, recovered, revoke_session(session))
    commit_reconciliation(store, runner, revocation)
    with pytest.raises(ReconciliationConflict):
        commit_reconciliation(store, runner, old_plan)


def test_completed_outcome_releases_capacity_without_submitting_session_result(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, authorization, source, recovered, store = context
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=session.attempt,
        status="completed",
        evidence=(),
        summary="Recovered provider completion.",
    )
    observation = observe_completed(
        authorization,
        result,
        provider_invocation_id="provider-completed-1",
    )
    outcome = admit_physical_observation(
        spec, registry, execution_plan, session, runner, authorization, observation
    )
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, outcome
    )
    target, _, _ = commit_reconciliation(store, runner, plan)
    assert target.state.active_leases == ()
    assert session.state == "running"


def test_receipt_tamper_is_detected(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, store = context
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    _, persistence_receipt, receipt = commit_reconciliation(store, runner, plan)
    changed = replace(receipt, target_snapshot_digest=ZERO)
    assert not verify_reconciliation_receipt(plan, persistence_receipt, changed)


def test_plan_release_digest_tamper_is_detected(tmp_path):
    context = recovery_context(tmp_path / "heads.db")
    runner, spec, registry, execution_plan, session, _, source, recovered, _ = context
    plan = plan_provider_outcome_reconciliation(
        source, spec, registry, execution_plan, session, runner, recovered, timeout_outcome(context)
    )
    changed = replace(plan, release_digest=ZERO)
    assert not verify_reconciliation_plan(source, runner, changed)
