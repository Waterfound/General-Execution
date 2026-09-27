import json

import pytest

from general_execution import (
    CheckpointEvidence,
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    PortfolioEntry,
    PortfolioState,
    ResumeTickObservation,
    TransitionPolicy,
    TransitionRule,
    canonical_json,
    sha256_digest,
)
from general_execution.asp_transition import TransitionAuthorityGrant
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)
from general_execution.external_trigger import ExternalTriggerEvidence, TriggerContract
from general_execution.persistent_runtime import (
    PersistentRuntimeError,
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import portfolio_state_to_dict
from general_execution.transition_policy import transition_policy_to_dict


REVISION = "a" * 40


def digest(value):
    return sha256_digest(value)


def encoded(value):
    return json.loads(canonical_json(value))


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://persistent-runtime",
        required_verifier_ref="verifier://persistent-runtime",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://persistent-runtime-core",
        evidence_digest=digest("persistent-runtime-core"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-09-27T16:00:00Z",
        passed=True,
        test_count=1,
    )
    assertions = tuple(
        CoreRehearsalAssertion(
            assertion_id=assertion_id,
            passed=True,
            evidence_refs=(f"fixture://{assertion_id}",),
            evidence_digests=(digest({"assertion": assertion_id}),),
        )
        for assertion_id in sorted(REQUIRED_CORE1_ASSERTIONS)
    )
    report = build_core_rehearsal_report(
        REVISION,
        receipt.digest,
        assertions,
    )
    return requirement, receipt, report


def portfolio():
    return PortfolioState(
        portfolio_id="persistent-runtime-test",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="Exercise persistent runtime",
            active_gate="RUNTIME",
            next_action_ref="action://await",
            source_revision="persistent-runtime-test",
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain available",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="persistent-runtime-test",
        ),
        passive=(),
    )


def policy():
    return TransitionPolicy(
        policy_id="persistent-runtime-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-human-stop",
                from_state="ready",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://persistent-runtime",
                effect="stop_human_gate",
                required_evidence=("authority_boundary_reached",),
                authority_mode="human_required",
                authority_boundary="persistent runtime test authority",
            ),
        ),
    )


def bootstrap_event():
    return {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": "bootstrap-001",
        "operation": "bootstrap",
        "body": {"portfolio": portfolio_state_to_dict(portfolio())},
    }


def transition_event():
    state = portfolio()
    p = policy()
    evidence = CheckpointEvidence(
        kind="authority_boundary_reached",
        locator="fixture://persistent-runtime/authority",
        digest=digest("authority-boundary"),
    )
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=0,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event="authority_required",
        evidence=(evidence,),
        action_ref="fixture://persistent-runtime/stop",
        observed_at="2026-09-27T16:01:00Z",
        summary="Persistent runtime must stop at authority boundary",
        canonical_refs=("fixture://persistent-runtime",),
    )
    trigger = ExternalTriggerEvidence(
        source="github-push",
        event_id="transition-001",
        event_kind="durable-transition",
        payload_digest=digest({"payload": "transition-001"}),
        observation_digest=observation.digest,
        admission_ref="github://push/transition-001",
    )
    contract = TriggerContract(
        source=trigger.source,
        event_kind=trigger.event_kind,
        portfolio_id=state.portfolio_id,
        policy_digest=p.digest,
        transition_event=observation.event,
    )
    return {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": trigger.event_id,
        "operation": "transition",
        "body": {
            "policy": transition_policy_to_dict(p),
            "contract": encoded(contract),
            "trigger": encoded(trigger),
            "observation": encoded(observation),
        },
    }


def test_bootstrap_is_idempotent_and_generation_zero(tmp_path):
    db = tmp_path / "state.db"
    event = bootstrap_event()

    first = process_persistent_runtime_event(db, event)
    second = process_persistent_runtime_event(db, event)

    assert first.status == "bootstrapped"
    assert second.status == "bootstrapped"
    assert first.post_generation == second.post_generation == 0
    assert first.post_state_digest == second.post_state_digest == portfolio().digest

    state, checkpoint, report = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db),
        portfolio().portfolio_id,
    )
    assert state == portfolio()
    assert checkpoint is None
    assert report.generation == 0


def test_transition_consumes_exact_authenticated_trigger_and_stops_at_human_gate(tmp_path):
    db = tmp_path / "state.db"
    process_persistent_runtime_event(db, bootstrap_event())
    event = transition_event()
    admission = trigger_digest_from_event(event)
    requirement, receipt, report = gate()

    result = process_persistent_runtime_event(
        db,
        event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )

    assert result.status == "committed"
    assert result.pre_generation == 0
    assert result.post_generation == 1
    assert result.human_required
    assert result.requested_action_ref == "authority://persistent-runtime"

    state, checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db),
        portfolio().portfolio_id,
    )
    assert state.active.state == "human_gate"
    assert state.active.authority_ref is None
    assert checkpoint is not None
    assert checkpoint.authority_stop
    assert checkpoint.next_transition_refs == ()


def test_redelivery_is_idempotent_after_persistent_restart(tmp_path):
    db = tmp_path / "state.db"
    process_persistent_runtime_event(db, bootstrap_event())
    event = transition_event()
    admission = trigger_digest_from_event(event)
    requirement, receipt, report = gate()

    first = process_persistent_runtime_event(
        db,
        event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )
    second = process_persistent_runtime_event(
        db,
        event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )

    assert first.status == "committed"
    assert second.status == "already_applied"
    assert second.pre_generation == second.post_generation == 1


def test_transition_rejects_unadmitted_trigger(tmp_path):
    db = tmp_path / "state.db"
    process_persistent_runtime_event(db, bootstrap_event())
    event = transition_event()
    requirement, receipt, report = gate()

    with pytest.raises(Exception, match="independently admitted"):
        process_persistent_runtime_event(
            db,
            event,
            authenticated_trigger_digest=digest("wrong-trigger"),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=report,
        )


def test_persistent_transport_cannot_carry_authority_grant(tmp_path):
    db = tmp_path / "state.db"
    process_persistent_runtime_event(db, bootstrap_event())
    event = transition_event()
    p = policy()
    rule = p.rules[0]
    grant = TransitionAuthorityGrant(
        policy_digest=p.digest,
        rule_digest=rule.digest,
        authority_boundary=rule.authority_boundary,
        authority_ref="authority://forbidden-transport-grant",
        authority_digest=digest("forbidden-grant"),
    )
    event["body"]["observation"]["authority_grant"] = encoded(grant)
    observation = event["body"]["observation"]

    # Rebind the trigger to the modified observation so the rejection tests authority,
    # not a stale observation digest.
    from general_execution.persistent_runtime import _observation

    decoded = _observation(observation)
    event["body"]["trigger"]["observation_digest"] = decoded.digest
    admission = trigger_digest_from_event(event)
    requirement, receipt, report = gate()

    with pytest.raises(PersistentRuntimeError, match="cannot carry transition authority"):
        process_persistent_runtime_event(
            db,
            event,
            authenticated_trigger_digest=admission,
            core_requirement=requirement,
            core_verification=receipt,
            core_report=report,
        )


def test_schema_rejects_unknown_fields_and_transition_requires_gate(tmp_path):
    db = tmp_path / "state.db"
    bad = bootstrap_event()
    bad["secret"] = "must-not-be-admitted"
    with pytest.raises(PersistentRuntimeError, match="fields mismatch"):
        process_persistent_runtime_event(db, bad)

    process_persistent_runtime_event(db, bootstrap_event())
    event = transition_event()
    with pytest.raises(PersistentRuntimeError, match="requires authenticated trigger"):
        process_persistent_runtime_event(db, event)
