from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionLedger,
    ExecutionSpec,
    ResultEnvelope,
    RunnerCapabilities,
    RunnerRegistry,
    SessionError,
    append_event,
    bind_session,
    plan_execution,
    revoke_session,
    start_session,
    submit_result,
    verify_ledger,
    verify_plan,
)

D = "sha256:" + "a" * 64


def spec(**changes):
    base = dict(
        producer="build-colony",
        producer_revision="bc-rev-001",
        task_kind="bounded-engineering-work",
        objective="Run one bounded package",
        source_revision="source-abc123",
        required_capabilities=("python",),
        allowed_scopes=("src/example.py",),
        forbidden_actions=("release", "change-authority"),
        evidence_requirements=("test-report",),
        inputs=(ArtifactRef("input", "repo://example/input", D),),
    )
    base.update(changes)
    return ExecutionSpec(**base)


def runner(runner_id="runner-a", caps=("python",), modes=("read_only",), max_parallelism=1):
    return RunnerCapabilities(
        runner_id=runner_id,
        provider="local",
        adapter="reference",
        adapter_version="1",
        capabilities=caps,
        modes=modes,
        max_parallelism=max_parallelism,
    )


def test_spec_identity_is_deterministic():
    a = spec()
    b = spec()
    assert a.digest == b.digest
    assert a.spec_id == b.spec_id


def test_spec_change_changes_identity():
    assert spec().digest != spec(objective="Different bounded objective").digest


def test_registry_digest_is_order_independent():
    a, b = runner("a"), runner("b")
    assert RunnerRegistry((a, b)).digest == RunnerRegistry((b, a)).digest


def test_duplicate_runner_ids_rejected():
    with pytest.raises(ValueError):
        RunnerRegistry((runner("same"), runner("same")))


def test_planner_is_deterministic_independent_of_registry_order():
    a, b = runner("a"), runner("b")
    first = plan_execution(spec(), RunnerRegistry((b, a)))
    second = plan_execution(spec(), RunnerRegistry((a, b)))
    assert first == second
    assert first.runner_id == "a"


def test_planner_defers_when_no_runner_is_compatible():
    plan = plan_execution(spec(required_capabilities=("gpu",)), RunnerRegistry((runner(),)))
    assert plan.runner_id is None
    assert plan.deferral_reason == "no_compatible_runner"


def test_planner_respects_execution_mode():
    plan = plan_execution(spec(), RunnerRegistry((runner(modes=("read_only",)),)), "bounded_write")
    assert plan.runner_id is None


def test_verify_plan_recomputes_exact_plan():
    registry = RunnerRegistry((runner("a"), runner("b")))
    plan = plan_execution(spec(), registry)
    assert verify_plan(spec(), registry, plan)
    assert not verify_plan(spec(objective="changed"), registry, plan)


def test_bind_rejects_deferred_plan():
    s = spec(required_capabilities=("gpu",))
    registry = RunnerRegistry((runner(),))
    with pytest.raises(SessionError):
        bind_session(s, registry, plan_execution(s, registry))


def test_session_identity_changes_by_attempt():
    s = spec()
    registry = RunnerRegistry((runner(),))
    plan = plan_execution(s, registry)
    one = bind_session(s, registry, plan, attempt=1)
    two = bind_session(s, registry, plan, attempt=2)
    assert one.session_id != two.session_id


def test_session_happy_path_binds_result_exactly():
    s = spec()
    registry = RunnerRegistry((runner(),))
    session = start_session(bind_session(s, registry, plan_execution(s, registry)))
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=s.spec_id,
        spec_digest=s.digest,
        runner_id=session.runner_id,
        attempt=session.attempt,
        status="completed",
        evidence=(ArtifactRef("test-report", "artifact://tests", D),),
    )
    submitted = submit_result(session, result)
    assert submitted.state == "result_submitted"
    assert submitted.result_digest == result.digest


def test_stale_attempt_result_is_rejected():
    s = spec()
    registry = RunnerRegistry((runner(),))
    plan = plan_execution(s, registry)
    old = start_session(bind_session(s, registry, plan, attempt=1))
    current = start_session(bind_session(s, registry, plan, attempt=2))
    stale = ResultEnvelope(
        session_id=old.session_id,
        spec_id=s.spec_id,
        spec_digest=s.digest,
        runner_id=old.runner_id,
        attempt=1,
        status="completed",
    )
    with pytest.raises(SessionError):
        submit_result(current, stale)


def test_revoked_session_cannot_submit():
    s = spec()
    registry = RunnerRegistry((runner(),))
    session = revoke_session(start_session(bind_session(s, registry, plan_execution(s, registry))))
    result = ResultEnvelope(
        session_id=session.session_id,
        spec_id=s.spec_id,
        spec_digest=s.digest,
        runner_id=session.runner_id,
        attempt=session.attempt,
        status="completed",
    )
    with pytest.raises(SessionError):
        submit_result(session, result)


def test_ledger_hash_chain_verifies():
    ledger = append_event(ExecutionLedger(), "ISSUE", {"spec": spec().digest})
    ledger = append_event(ledger, "BIND", {"runner": "runner-a"})
    assert verify_ledger(ledger)


def test_ledger_payload_tamper_is_detected():
    ledger = append_event(ExecutionLedger(), "ISSUE", {"spec": spec().digest})
    event = replace(ledger.events[0], payload={"spec": "tampered"})
    tampered = replace(ledger, events=(event,))
    assert not verify_ledger(tampered)


def test_ledger_reordering_is_detected():
    ledger = append_event(ExecutionLedger(), "ONE", {"n": 1})
    ledger = append_event(ledger, "TWO", {"n": 2})
    tampered = replace(ledger, events=(ledger.events[1], ledger.events[0]))
    assert not verify_ledger(tampered)


def test_artifact_digest_format_is_fail_closed():
    with pytest.raises(ValueError):
        ArtifactRef("bad", "artifact://bad", "not-a-digest")


def test_invalid_runner_mode_is_rejected_at_runtime():
    with pytest.raises(ValueError):
        runner(modes=("verified",))


def test_result_cannot_claim_verification_authority():
    s = spec()
    registry = RunnerRegistry((runner(),))
    session = start_session(bind_session(s, registry, plan_execution(s, registry)))
    with pytest.raises(ValueError):
        ResultEnvelope(
            session_id=session.session_id,
            spec_id=s.spec_id,
            spec_digest=s.digest,
            runner_id=session.runner_id,
            attempt=session.attempt,
            status="verified",
        )


def test_artifact_digest_rejects_non_hex_payload():
    with pytest.raises(ValueError):
        ArtifactRef("bad", "artifact://bad", "sha256:" + "z" * 64)
