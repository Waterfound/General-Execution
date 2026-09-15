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
    observe_failure,
    plan_execution,
    reference_runner,
    reserve_capacity,
    start_session,
)
from general_execution.reattachment import (
    PROVIDER_REATTACHMENT_CAPABILITY,
    ProviderStatusObservation,
    ReattachmentError,
    assess_provider_status,
    build_status_probe,
    observe_provider_not_found,
    observe_provider_running,
    observe_provider_terminal,
    reattachment_key_from_authorization,
    reattachment_key_from_recovered,
    verify_reattachment_key,
    verify_status_observation,
    verify_status_probe,
)
from general_execution.reconciliation import (
    plan_provider_outcome_reconciliation,
    verify_reconciliation_plan,
)
from general_execution.durable import recover_after_restart

D = "sha256:" + "b" * 64
BAD = "sha256:" + "0" * 64


def reattachable_runner():
    return replace(
        reference_runner(),
        capabilities=(REFERENCE_CAPABILITY, PROVIDER_REATTACHMENT_CAPABILITY),
    )


def context(suffix="1"):
    runner = reattachable_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-reattach-pilot",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Provider reattachment {suffix}",
        source_revision=f"source-reattach-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://reattach/{suffix}", D),),
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
        invocation_id=f"gei-reattach-{suffix}",
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


def test_key_reconstructs_identically_before_dispatch_and_after_restart():
    runner, _, _, _, _, authorization, _, recovered, _ = context()
    before = reattachment_key_from_authorization(authorization, runner)
    after = reattachment_key_from_recovered(recovered, runner)
    assert before == after
    assert before.provider_key.startswith("gerk-")
    assert verify_reattachment_key(authorization, recovered, runner)


def test_non_reattachable_runner_cannot_create_key():
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-no-reattach",
        task_kind=REFERENCE_TASK_KIND,
        objective="No reattachment capability",
        source_revision="source-no-reattach",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://no-reattach", D),),
    )
    registry = RunnerRegistry((runner,))
    execution_plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, execution_plan))
    authorization = authorize_physical_attempt(spec, registry, execution_plan, session, runner)
    with pytest.raises(ReattachmentError):
        reattachment_key_from_authorization(authorization, runner)


def test_probe_is_deterministic_and_bound_to_recovery_head():
    runner, _, _, _, _, _, snapshot, recovered, probe = context()
    assert probe == build_status_probe(snapshot, runner, recovered)
    assert probe.source_head_digest == snapshot.head.digest
    assert verify_status_probe(snapshot, runner, probe)


def test_running_status_keeps_lease_in_flight_without_outcome():
    ctx = context()
    runner, spec, registry, execution_plan, session, authorization, snapshot, _, probe = ctx
    observation = observe_provider_running(probe, provider_invocation_id="provider-job-1")
    assessment, outcome = assess_provider_status(
        snapshot, spec, registry, execution_plan, session, runner, authorization, probe, observation
    )
    assert assessment.disposition == "keep_running"
    assert outcome is None
    assert len(snapshot.state.active_leases) == 1


def test_not_found_remains_unknown_and_does_not_release_capacity():
    ctx = context()
    runner, spec, registry, execution_plan, session, authorization, snapshot, _, probe = ctx
    observation = observe_provider_not_found(probe)
    assessment, outcome = assess_provider_status(
        snapshot, spec, registry, execution_plan, session, runner, authorization, probe, observation
    )
    assert assessment.disposition == "remain_unknown"
    assert outcome is None
    assert snapshot.state.active_leases == ctx[6].state.active_leases


def test_terminal_status_admits_physical_outcome_and_feeds_v007_reconciliation():
    ctx = context()
    runner, spec, registry, execution_plan, session, authorization, snapshot, recovered, probe = ctx
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-job-1",
    )
    observation = observe_provider_terminal(probe, physical)
    assessment, outcome = assess_provider_status(
        snapshot, spec, registry, execution_plan, session, runner, authorization, probe, observation
    )
    assert assessment.disposition == "terminal_outcome"
    assert outcome is not None
    assert assessment.outcome_digest == outcome.digest
    reconciliation = plan_provider_outcome_reconciliation(
        snapshot, spec, registry, execution_plan, session, runner, recovered, outcome
    )
    assert verify_reconciliation_plan(snapshot, runner, reconciliation)
    assert reconciliation.target_snapshot.state.active_leases == ()


def test_foreign_terminal_observation_cannot_attach_to_recovered_lease():
    first = context("a")
    second = context("b")
    runner, spec, registry, execution_plan, session, authorization, snapshot, _, probe = first
    foreign_physical = observe_failure(
        second[5],
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-other",
    )
    observation = ProviderStatusObservation(
        probe_digest=probe.digest,
        reattachment_key_digest=probe.reattachment_key.digest,
        provider_key=probe.reattachment_key.provider_key,
        status="terminal",
        provider_invocation_id=foreign_physical.provider_invocation_id,
        physical_observation=foreign_physical,
    )
    assert not verify_status_observation(probe, observation)
    with pytest.raises(ReattachmentError):
        assess_provider_status(
            snapshot, spec, registry, execution_plan, session, runner, authorization, probe, observation
        )


def test_changed_provider_key_is_rejected():
    *_, probe = context()
    observation = observe_provider_running(probe)
    changed = replace(observation, provider_key="gerk-not-the-original-key")
    assert not verify_status_observation(probe, changed)


def test_changed_probe_digest_is_rejected():
    *_, probe = context()
    observation = observe_provider_running(probe)
    changed = replace(observation, probe_digest=BAD)
    assert not verify_status_observation(probe, changed)


def test_non_terminal_status_cannot_carry_physical_observation():
    ctx = context()
    authorization, probe = ctx[5], ctx[8]
    physical = observe_failure(
        authorization,
        "timed_out",
        failure_code="reference.timeout",
        provider_invocation_id="provider-job-1",
    )
    with pytest.raises(ValueError):
        ProviderStatusObservation(
            probe_digest=probe.digest,
            reattachment_key_digest=probe.reattachment_key.digest,
            provider_key=probe.reattachment_key.provider_key,
            status="running",
            physical_observation=physical,
        )


def test_not_found_cannot_claim_provider_invocation_id():
    *_, probe = context()
    with pytest.raises(ValueError):
        ProviderStatusObservation(
            probe_digest=probe.digest,
            reattachment_key_digest=probe.reattachment_key.digest,
            provider_key=probe.reattachment_key.provider_key,
            status="not_found",
            provider_invocation_id="provider-job-1",
        )


def test_tampered_recovered_lease_cannot_build_probe():
    runner, _, _, _, _, _, snapshot, recovered, _ = context()
    changed = replace(recovered, invocation_id="gei-different")
    with pytest.raises(ReattachmentError):
        build_status_probe(snapshot, runner, changed)


def test_capability_added_after_original_authorization_does_not_retrofit_reattachment():
    original = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-retrofit",
        task_kind=REFERENCE_TASK_KIND,
        objective="No retroactive reattachment",
        source_revision="source-retrofit",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://retrofit", D),),
    )
    registry = RunnerRegistry((original,))
    execution_plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, execution_plan))
    authorization = authorize_physical_attempt(spec, registry, execution_plan, session, original)
    upgraded = replace(
        original,
        capabilities=(REFERENCE_CAPABILITY, PROVIDER_REATTACHMENT_CAPABILITY),
    )
    with pytest.raises(ReattachmentError):
        reattachment_key_from_authorization(authorization, upgraded)


def test_invalid_detail_digest_is_rejected():
    *_, probe = context()
    with pytest.raises(ValueError):
        observe_provider_running(probe, detail_digest="not-a-sha256-digest")
