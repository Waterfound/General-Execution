import pytest

from general_execution import (
    ArtifactRef,
    ExecutionLedger,
    ExecutionSpec,
    PhysicalAttemptError,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    admit_physical_observation,
    authorize_physical_attempt,
    authorize_retry,
    bind_session,
    identify_duplicate_physical_attempt,
    make_reference_observation,
    observe_completed,
    observe_failure,
    plan_execution,
    record_physical_attempt,
    reference_runner,
    start_session,
    verify_physical_attempt_record,
    verify_physical_outcome,
    verify_retry_chain,
)

D = "sha256:" + "c" * 64


def context():
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-v0.0.9",
        task_kind=REFERENCE_TASK_KIND,
        objective="Physical outcome conformance",
        source_revision="source-002",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://physical", D),),
    )
    runner = reference_runner()
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    return spec, runner, registry, plan, session


def completed_result(auth):
    return make_reference_observation(auth.request, provider_invocation_id="provider-complete").result


def test_status_matrix():
    spec, runner, registry, plan, session = context()
    for status in ("rejected", "timed_out", "cancelled", "transport_failed"):
        auth = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id=f"gei-{status}")
        observation = observe_failure(auth, status, failure_code=f"reference.{status}")
        bundle = admit_physical_observation(spec, registry, plan, session, runner, auth, observation)
        assert bundle.result is None
        assert verify_physical_outcome(spec, registry, plan, session, runner, bundle)


def test_logical_session_remains_active_after_provider_outcome():
    spec, runner, registry, plan, session = context()
    auth = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-one")
    bundle = admit_physical_observation(
        spec, registry, plan, session, runner, auth,
        observe_failure(auth, "timed_out", failure_code="provider.timeout"),
    )
    retry = authorize_retry(spec, registry, plan, session, runner, bundle, invocation_id="gei-two")
    assert session.state == "running"
    assert retry.physical_attempt == 2
    assert retry.request.session_id == session.session_id


def test_retry_lineage_binds_prior_receipt():
    spec, runner, registry, plan, session = context()
    first = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-one")
    first_outcome = admit_physical_observation(
        spec, registry, plan, session, runner, first,
        observe_failure(first, "rejected", failure_code="provider.busy"),
    )
    second = authorize_retry(spec, registry, plan, session, runner, first_outcome, invocation_id="gei-two")
    assert second.previous_invocation_id == first.request.invocation_id
    assert second.previous_receipt_digest == first_outcome.receipt.digest


def test_completed_attempt_has_no_retry():
    spec, runner, registry, plan, session = context()
    auth = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-success")
    outcome = admit_physical_observation(
        spec, registry, plan, session, runner, auth,
        observe_completed(auth, completed_result(auth), provider_invocation_id="provider-complete"),
    )
    with pytest.raises(PhysicalAttemptError):
        authorize_retry(spec, registry, plan, session, runner, outcome, invocation_id="gei-next")


def test_retry_chain_round_trip():
    spec, runner, registry, plan, session = context()
    a1 = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-1")
    b1 = admit_physical_observation(
        spec, registry, plan, session, runner, a1,
        observe_failure(a1, "timed_out", failure_code="provider.timeout"),
    )
    a2 = authorize_retry(spec, registry, plan, session, runner, b1, invocation_id="gei-2")
    b2 = admit_physical_observation(
        spec, registry, plan, session, runner, a2,
        observe_completed(a2, completed_result(a2), provider_invocation_id="provider-2"),
    )
    assert verify_retry_chain((b1, b2))


def test_provider_duplicate_is_separate_evidence():
    spec, runner, registry, plan, session = context()
    auth = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-dup")
    first = observe_failure(auth, "timed_out", failure_code="timeout", provider_invocation_id="provider-a")
    second = observe_failure(auth, "timed_out", failure_code="timeout", provider_invocation_id="provider-b")
    evidence = identify_duplicate_physical_attempt(auth, first, second)
    assert evidence.canonical_provider_invocation_id != evidence.duplicate_provider_invocation_id


def test_ledger_record_round_trip():
    spec, runner, registry, plan, session = context()
    auth = authorize_physical_attempt(spec, registry, plan, session, runner, invocation_id="gei-ledger")
    outcome = admit_physical_observation(
        spec, registry, plan, session, runner, auth,
        observe_failure(auth, "transport_failed", failure_code="transport.reset"),
    )
    ledger, record = record_physical_attempt(ExecutionLedger(), outcome)
    assert verify_physical_attempt_record(ledger, outcome, record)
    assert ledger.events[-1].event_type == "PHYSICAL_TERMINAL_FAILURE"
