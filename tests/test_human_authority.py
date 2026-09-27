import pytest

from general_execution.asp_transition import CheckpointEvidence
from general_execution.canonical import sha256_digest
from general_execution.human_authority import (
    HumanAuthorityError,
    consume_human_authority,
)
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import PortfolioEntry, PortfolioState
from general_execution.resume_tick import (
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    ResumeTickObservation,
    resume_tick,
)
from general_execution.transition_policy import (
    TransitionPolicy,
    TransitionPolicyError,
    TransitionRule,
)


REVISION = "b" * 40
BOUNDARY = "merge durable execution canonical runtime"
AUTHORITY_REF = "github://Waterfound/General-Execution/commit/test-authority"


def digest(value):
    return sha256_digest(value)


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://human-authority",
        required_verifier_ref="verifier://human-authority",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://human-authority-core",
        evidence_digest=digest("human-authority-core"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-09-27T20:00:00Z",
        passed=True,
        test_count=1,
    )
    return requirement, receipt


def portfolio():
    return PortfolioState(
        portfolio_id="human-authority-test",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="Exercise durable human authority",
            active_gate="AUTHORITY",
            next_action_ref="action://reach-authority",
            source_revision=REVISION,
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain available",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision=REVISION,
        ),
    )


def evidence(kind):
    return CheckpointEvidence(
        kind=kind,
        locator=f"fixture://human-authority/{kind}",
        digest=digest({"kind": kind}),
    )


def stop_policy():
    return TransitionPolicy(
        policy_id="human-stop",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-stop",
                from_state="ready",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://approve-merge",
                effect="stop_human_gate",
                required_evidence=("authority_boundary_reached",),
                authority_mode="human_required",
                authority_boundary=BOUNDARY,
            ),
        ),
    )


def resume_policy():
    return TransitionPolicy(
        policy_id="human-resume",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-resume",
                from_state="human_gate",
                event="verification_passed",
                to_state="complete",
                next_action_ref="action://closed",
                effect="none",
                required_evidence=("human_authority_recorded",),
                authority_mode="preauthorized_required",
                authority_boundary=BOUNDARY,
            ),
        ),
    )


def observation(state, policy, event, kind, action_ref):
    return ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=policy.digest,
        event=event,
        evidence=(evidence(kind),),
        action_ref=action_ref,
        observed_at="2026-09-27T20:00:00Z",
        summary=f"Human authority test {event}",
        canonical_refs=("fixture://human-authority",),
    )


def human_gate_store(tmp_path):
    store = SqlitePortfolioHeadStore(tmp_path / "state.db")
    initial = portfolio()
    store.initialize(initial)
    requirement, receipt = gate()
    policy = stop_policy()
    tick = resume_tick(
        store,
        initial.portfolio_id,
        policy,
        observation(
            initial,
            policy,
            "authority_required",
            "authority_boundary_reached",
            "fixture://stop",
        ),
        core_requirement=requirement,
        core_verification=receipt,
    )
    assert tick.disposition == "committed"
    state, checkpoint, _ = recover_portfolio_after_restart(
        store,
        initial.portfolio_id,
    )
    assert state.active.state == "human_gate"
    assert checkpoint is not None and checkpoint.authority_stop
    return store, state, requirement, receipt


def test_human_authority_consumes_exact_gate_and_clears_blocker(tmp_path):
    store, state, requirement, verification = human_gate_store(tmp_path)
    policy = resume_policy()
    obs = observation(
        state,
        policy,
        "verification_passed",
        "human_authority_recorded",
        "fixture://resume",
    )

    receipt, bound, result = consume_human_authority(
        store,
        policy,
        obs,
        event_id="human-authority-001",
        approved_action_ref="authority://approve-merge",
        approved_at="2026-09-27T20:01:00Z",
        provider_actor="Waterfound",
        authority_ref=AUTHORITY_REF,
        core_requirement=requirement,
        core_verification=verification,
    )

    assert result.disposition == "committed"
    assert result.pre_generation == 1
    assert result.post_generation == 2
    assert bound.authority_grant is not None
    assert bound.authority_grant.authority_digest == receipt.digest

    after, checkpoint, _ = recover_portfolio_after_restart(
        store,
        state.portfolio_id,
    )
    assert after.active.state == "complete"
    assert after.active.authority_boundary is None
    assert after.active.authority_ref == AUTHORITY_REF
    assert after.active.blockers == ()
    assert checkpoint is not None
    assert not checkpoint.authority_stop
    assert AUTHORITY_REF in checkpoint.canonical_refs


def test_human_authority_rejects_untrusted_actor(tmp_path):
    store, state, requirement, verification = human_gate_store(tmp_path)
    policy = resume_policy()
    obs = observation(
        state,
        policy,
        "verification_passed",
        "human_authority_recorded",
        "fixture://resume",
    )

    with pytest.raises(HumanAuthorityError, match="provider actor"):
        consume_human_authority(
            store,
            policy,
            obs,
            event_id="human-authority-002",
            approved_action_ref="authority://approve-merge",
            approved_at="2026-09-27T20:01:00Z",
            provider_actor="not-waterfound",
            authority_ref=AUTHORITY_REF,
            core_requirement=requirement,
            core_verification=verification,
        )


def test_human_authority_rejects_wrong_pending_action(tmp_path):
    store, state, requirement, verification = human_gate_store(tmp_path)
    policy = resume_policy()
    obs = observation(
        state,
        policy,
        "verification_passed",
        "human_authority_recorded",
        "fixture://resume",
    )

    with pytest.raises(HumanAuthorityError, match="approved action"):
        consume_human_authority(
            store,
            policy,
            obs,
            event_id="human-authority-003",
            approved_action_ref="authority://different-action",
            approved_at="2026-09-27T20:01:00Z",
            provider_actor="Waterfound",
            authority_ref=AUTHORITY_REF,
            core_requirement=requirement,
            core_verification=verification,
        )


def test_transition_policy_forbids_unbounded_exit_from_human_gate():
    with pytest.raises(
        TransitionPolicyError,
        match="transitions from human_gate require preauthorized authority",
    ):
        TransitionRule(
            rule_id="unsafe-exit",
            from_state="human_gate",
            event="verification_passed",
            to_state="complete",
            next_action_ref="action://closed",
            effect="none",
            authority_mode="none",
        )
