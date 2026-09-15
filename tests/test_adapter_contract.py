from dataclasses import replace

import pytest

from general_execution import (
    AdapterError,
    ArtifactRef,
    ExecutionLedger,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    RunnerRegistry,
    admit_observation,
    bind_session,
    build_dispatch_request,
    make_reference_observation,
    plan_execution,
    record_invocation,
    reference_runner,
    start_session,
    submit_result,
    verify_dispatch_request,
    verify_invocation_bundle,
    verify_invocation_record,
)

D = "sha256:" + "b" * 64


def context():
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-v0.0.9",
        task_kind=REFERENCE_TASK_KIND,
        objective="Adapter conformance probe",
        source_revision="source-001",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", "bc://reference", D),),
    )
    runner = reference_runner()
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    return spec, runner, registry, plan, session


def test_request_is_reproducible():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner, invocation_id="gei-fixed")
    assert verify_dispatch_request(spec, registry, plan, session, runner, request)


def test_request_change_is_detected():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner, invocation_id="gei-fixed")
    changed = replace(request, spec_digest="sha256:" + "0" * 64)
    assert not verify_dispatch_request(spec, registry, plan, session, runner, changed)


def test_observation_round_trip():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner)
    observation = make_reference_observation(request, provider_invocation_id="provider-1")
    bundle = admit_observation(spec, registry, plan, session, runner, request, observation)
    assert verify_invocation_bundle(spec, registry, plan, session, runner, bundle)
    assert submit_result(session, bundle.result).state == "result_submitted"


def test_observation_change_is_rejected():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner)
    observation = make_reference_observation(request)
    changed = replace(observation, response_digest="sha256:" + "0" * 64)
    with pytest.raises(AdapterError):
        admit_observation(spec, registry, plan, session, runner, request, changed)


def test_provider_identity_is_separate_from_session_identity():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner, invocation_id="gei-one")
    a = make_reference_observation(request, provider_invocation_id="provider-a")
    b = make_reference_observation(request, provider_invocation_id="provider-b")
    assert a.provider_invocation_id != b.provider_invocation_id
    assert a.result.session_id == b.result.session_id == session.session_id


def test_invocation_record_is_verifiable():
    spec, runner, registry, plan, session = context()
    request = build_dispatch_request(spec, registry, plan, session, runner)
    bundle = admit_observation(spec, registry, plan, session, runner, request, make_reference_observation(request))
    ledger, record = record_invocation(ExecutionLedger(), bundle)
    assert verify_invocation_record(ledger, bundle, record)
