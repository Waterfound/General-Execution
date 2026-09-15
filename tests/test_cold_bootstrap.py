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
    release_capacity_for_revocation,
    reserve_capacity,
    revoke_session,
    start_session,
)
from general_execution.cold_bootstrap import bootstrap_active_recovery_contexts
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.recovery_context import SQLiteRecoveryContextStore, build_recovery_context

D = "sha256:" + "a" * 64


def context_fixture():
    runner = reattachable_reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-cold-bootstrap",
        task_kind=REFERENCE_TASK_KIND,
        objective="Cold bootstrap context",
        source_revision="source-cold-bootstrap",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://cold-bootstrap", D),),
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
        invocation_id="gei-cold-bootstrap",
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


def test_cold_bootstrap_reconstructs_active_context_from_stores_only(tmp_path):
    runner, spec, registry, plan, session, authorization, anchor, recovered, context = context_fixture()
    context_path = tmp_path / "contexts.db"
    capacity_path = tmp_path / "capacity.db"

    SQLiteRecoveryContextStore(context_path).save(context, anchor)
    SQLiteDurableHeadStore(capacity_path).compare_and_swap(
        anchor, runner, expected_head_digest=None
    )

    bindings = bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(context_path),
        SQLiteDurableHeadStore(capacity_path),
    )
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.context == context
    assert binding.runner == runner
    assert binding.current_snapshot == anchor
    assert binding.recovered_lease == recovered
    assert binding.context.spec == spec
    assert binding.context.registry == registry
    assert binding.context.plan == plan
    assert binding.context.session == session
    assert binding.context.authorization == authorization


def test_context_persisted_before_capacity_commit_is_safe_orphan(tmp_path):
    _, _, _, _, _, _, anchor, _, context = context_fixture()
    context_path = tmp_path / "contexts.db"
    capacity_path = tmp_path / "capacity.db"
    SQLiteRecoveryContextStore(context_path).save(context, anchor)

    bindings = bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(context_path),
        SQLiteDurableHeadStore(capacity_path),
    )
    assert bindings == ()


def test_released_lease_context_is_ignored_after_cold_bootstrap(tmp_path):
    runner, _, _, _, session, _, anchor, recovered, context = context_fixture()
    context_path = tmp_path / "contexts.db"
    capacity_path = tmp_path / "capacity.db"
    context_store = SQLiteRecoveryContextStore(context_path)
    capacity_store = SQLiteDurableHeadStore(capacity_path)
    context_store.save(context, anchor)
    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=None)

    active = next(lease for lease in anchor.state.active_leases if lease.lease_id == recovered.lease_id)
    revoked = revoke_session(session)
    state, _, _ = release_capacity_for_revocation(anchor.state, runner, active, revoked)
    released = build_durable_snapshot(state, runner, previous=anchor)
    capacity_store.compare_and_swap(
        released, runner, expected_head_digest=anchor.head.digest
    )

    assert bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(context_path),
        SQLiteDurableHeadStore(capacity_path),
    ) == ()
