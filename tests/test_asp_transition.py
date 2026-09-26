from dataclasses import replace

import pytest

from general_execution import (
    AspTransitionError,
    CheckpointEvidence,
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
    SqlitePortfolioHeadStore,
    TransitionAuthorityGrant,
    TransitionPolicy,
    TransitionRule,
    WakeCondition,
    admit_passive_wake,
    apply_active_transition,
    match_transition_rule,
    recover_portfolio_after_restart,
)

D = "sha256:" + "d" * 64
A = "sha256:" + "a" * 64


def ev(kind, suffix=None):
    name = suffix or kind
    return CheckpointEvidence(
        kind=kind,
        locator=f"artifact://{name}",
        digest=D,
    )


def active(state="ready", **changes):
    values = dict(
        work_id="ACTIVE",
        role="active",
        state=state,
        objective="Advance active frontier",
        active_gate="ACTIVE_GATE",
        next_action_ref="action://active",
        source_revision="src-active",
        evidence_required=("result",),
    )
    if state == "waiting_external":
        values.update(
            blockers=(
                PortfolioBlocker(
                    kind="external_dependency",
                    detail="provider unavailable",
                ),
            ),
            wake_condition=WakeCondition(
                kind="event_received",
                value="provider.available",
            ),
        )
    values.update(changes)
    return PortfolioEntry(**values)


def secondary(work_id="SECONDARY", **changes):
    values = dict(
        work_id=work_id,
        role="secondary",
        state="ready",
        objective=f"Prepare {work_id}",
        active_gate=f"{work_id}_GATE",
        next_action_ref=f"action://{work_id.lower()}",
        source_revision=f"src-{work_id.lower()}",
    )
    values.update(changes)
    return PortfolioEntry(**values)


def passive(work_id="PASSIVE", **changes):
    values = dict(
        work_id=work_id,
        role="passive",
        state="passive",
        objective=f"Wait for {work_id}",
        active_gate=f"{work_id}_GATE",
        next_action_ref=f"action://{work_id.lower()}",
        source_revision=f"src-{work_id.lower()}",
        blockers=(
            PortfolioBlocker(
                kind="external_dependency",
                detail=f"{work_id} blocked",
            ),
        ),
        wake_condition=WakeCondition(
            kind="event_received",
            value=f"{work_id.lower()}.ready",
        ),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def portfolio(active_state="ready", **changes):
    values = dict(
        portfolio_id="durable-asp",
        generation=0,
        active=active(active_state),
        secondary=secondary(),
        passive=(passive(),),
    )
    values.update(changes)
    return PortfolioState(**values)


def policy():
    rules = (
        TransitionRule(
            rule_id="01-start",
            from_state="ready",
            event="execution_started",
            to_state="running",
            next_action_ref="action://observe-run",
            required_evidence=("dispatch_admitted",),
        ),
        TransitionRule(
            rule_id="02-promote",
            from_state="verifying",
            event="verification_passed",
            to_state="complete",
            next_action_ref="action://promote-secondary",
            effect="promote_secondary",
            required_evidence=("verifier_pass",),
        ),
        TransitionRule(
            rule_id="03-park",
            from_state="waiting_external",
            event="external_blocker",
            to_state="passive",
            next_action_ref="wake://active-external-blocker",
            effect="park_active",
            required_evidence=("external_blocker", "no_internal_work"),
        ),
        TransitionRule(
            rule_id="04-di",
            from_state="running",
            event="diagnosis_required",
            to_state="di_required",
            next_action_ref="diagnose://active",
            effect="request_di",
            required_evidence=("failure_evidence",),
        ),
        TransitionRule(
            rule_id="05-human",
            from_state="running",
            event="authority_required",
            to_state="human_gate",
            next_action_ref="authority://human-decision",
            effect="stop_human_gate",
            required_evidence=("authority_boundary_reached",),
            authority_mode="human_required",
            authority_boundary="release approval",
        ),
        TransitionRule(
            rule_id="06-preauthorized",
            from_state="running",
            event="execution_completed",
            to_state="verifying",
            next_action_ref="verify://active",
            required_evidence=("execution_result",),
            authority_mode="preauthorized_required",
            authority_boundary="bounded execution scope",
        ),
        TransitionRule(
            rule_id="07-wake",
            from_state="passive",
            event="wake_satisfied",
            to_state="ready",
            next_action_ref="action://woken-passive",
            effect="wake_passive",
            required_evidence=("wake_condition_satisfied",),
        ),
    )
    return TransitionPolicy(
        policy_id="durable-asp-v1",
        revision="1",
        rules=rules,
    )


def apply(state, event, evidence, **kwargs):
    return apply_active_transition(
        state,
        policy(),
        event,
        evidence,
        action_ref=kwargs.pop("action_ref", "action://observed"),
        observed_at=kwargs.pop("observed_at", "2026-09-23T16:00:00Z"),
        summary=kwargs.pop("summary", "Observed deterministic transition"),
        canonical_refs=kwargs.pop("canonical_refs", ("artifact://canonical",)),
        **kwargs,
    )


def test_nonrotating_transition_advances_generation_and_binds_checkpoint():
    state = portfolio("ready")
    result = apply(state, "execution_started", (ev("dispatch_admitted"),))

    assert state.generation == 0
    assert state.active.state == "ready"
    assert result.new_state.generation == 1
    assert result.new_state.previous_state_digest == state.digest
    assert result.new_state.active.state == "running"
    assert result.new_state.secondary == state.secondary
    assert result.new_state.passive == state.passive
    assert result.checkpoint.portfolio_state_digest == result.new_state.digest
    assert result.checkpoint.state_before == "ready"
    assert result.checkpoint.state_after == "running"
    assert result.checkpoint.next_transition_refs == ("action://observe-run",)


def test_missing_policy_evidence_fails_closed():
    state = portfolio("ready")
    with pytest.raises(AspTransitionError, match="policy-required evidence"):
        apply(state, "execution_started", (ev("wrong"),))


def test_unmatched_transition_fails_closed():
    state = portfolio("ready")
    with pytest.raises(AspTransitionError, match="no unique admissible transition"):
        apply(state, "fatal_failure", (ev("failure"),))


def test_verified_completion_promotes_secondary_from_woken_passive():
    state = portfolio(
        "verifying",
        passive=(passive("PASSIVE-A"), passive("PASSIVE-B")),
    )
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE-A",
        (ev("wake_condition_satisfied"),),
    )

    result = apply_active_transition(
        state,
        p,
        "verification_passed",
        (ev("verifier_pass"),),
        action_ref="verify://active",
        observed_at="2026-09-23T16:00:00Z",
        summary="Verifier passed",
        canonical_refs=("artifact://canonical",),
        wake_admission=admission,
    )

    assert result.effect == "promote_secondary"
    assert result.new_state.active.work_id == "SECONDARY"
    assert result.new_state.active.role == "active"
    assert result.new_state.active.state == "ready"
    assert result.new_state.secondary.work_id == "PASSIVE-A"
    assert tuple(item.work_id for item in result.new_state.passive) == ("PASSIVE-B",)
    assert result.replacement_secondary_work_id == "PASSIVE-A"
    assert result.checkpoint.work_id == "ACTIVE"
    assert result.checkpoint.state_after == "complete"
    assert result.checkpoint.next_transition_refs == ()
    all_ids = {
        result.new_state.active.work_id,
        result.new_state.secondary.work_id,
        *(item.work_id for item in result.new_state.passive),
    }
    assert "ACTIVE" not in all_ids


def test_rotating_transition_never_invents_replacement_secondary():
    state = portfolio("verifying")
    with pytest.raises(
        AspTransitionError,
        match="requires a valid passive wake admission",
    ):
        apply(state, "verification_passed", (ev("verifier_pass"),))


def test_external_replacement_selection_is_not_authorized_in_core():
    state = portfolio("verifying")
    with pytest.raises(
        AspTransitionError,
        match="external replacement selection is not authorized",
    ):
        apply(
            state,
            "verification_passed",
            (ev("verifier_pass"),),
            replacement_secondary=secondary("NEXT"),
        )


def test_external_blocker_parks_active_only_with_no_internal_work_evidence():
    state = portfolio("waiting_external")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )

    result = apply_active_transition(
        state,
        p,
        "external_blocker",
        (
            ev("external_blocker"),
            ev("no_internal_work"),
        ),
        action_ref="action://observed",
        observed_at="2026-09-23T16:00:00Z",
        summary="Active externally blocked",
        canonical_refs=("artifact://canonical",),
        wake_admission=admission,
    )

    assert result.effect == "park_active"
    assert result.new_state.active.work_id == "SECONDARY"
    assert result.new_state.active.state == "ready"
    assert result.new_state.secondary.work_id == "PASSIVE"
    parked = {item.work_id: item for item in result.new_state.passive}["ACTIVE"]
    assert parked.role == "passive"
    assert parked.state == "passive"
    assert parked.blockers
    assert parked.wake_condition is not None
    assert result.checkpoint.state_after == "passive"


def test_park_active_rejects_missing_no_internal_work_proof():
    state = portfolio("waiting_external")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    with pytest.raises(AspTransitionError, match="policy-required evidence"):
        apply_active_transition(
            state,
            p,
            "external_blocker",
            (ev("external_blocker"),),
            action_ref="action://observed",
            observed_at="2026-09-23T16:00:00Z",
            summary="Active externally blocked",
            canonical_refs=("artifact://canonical",),
            wake_admission=admission,
        )


def test_human_authority_rule_stops_without_granting_authority():
    state = portfolio("running")
    result = apply(
        state,
        "authority_required",
        (ev("authority_boundary_reached"),),
    )

    assert result.new_state.active.state == "human_gate"
    assert result.new_state.active.authority_boundary == "release approval"
    assert result.new_state.active.authority_ref is None
    assert result.new_state.active.blockers[0].kind == "authority"
    assert result.checkpoint.authority_stop
    assert result.checkpoint.authority_boundary == "release approval"
    assert result.checkpoint.next_transition_refs == ()
    assert result.authority_grant_digest is None


def test_human_required_transition_rejects_premature_authority_grant():
    state = portfolio("running")
    p = policy()
    rule = match_transition_rule(p, "running", "authority_required")
    grant = TransitionAuthorityGrant(
        policy_digest=p.digest,
        rule_digest=rule.digest,
        authority_boundary="release approval",
        authority_ref="artifact://approval",
        authority_digest=A,
    )
    with pytest.raises(
        AspTransitionError,
        match="stops before authority is granted",
    ):
        apply_active_transition(
            state,
            p,
            "authority_required",
            (ev("authority_boundary_reached"),),
            action_ref="action://observed",
            observed_at="2026-09-23T16:00:00Z",
            summary="Reached authority gate",
            canonical_refs=("artifact://canonical",),
            authority_grant=grant,
        )


def test_preauthorized_transition_requires_exact_bounded_grant():
    state = portfolio("running")
    p = policy()
    rule = match_transition_rule(p, "running", "execution_completed")

    with pytest.raises(
        AspTransitionError,
        match="requires bounded authority grant",
    ):
        apply_active_transition(
            state,
            p,
            "execution_completed",
            (ev("execution_result"),),
            action_ref="action://execute",
            observed_at="2026-09-23T16:00:00Z",
            summary="Execution completed",
            canonical_refs=("artifact://canonical",),
        )

    grant = TransitionAuthorityGrant(
        policy_digest=p.digest,
        rule_digest=rule.digest,
        authority_boundary="bounded execution scope",
        authority_ref="artifact://bounded-authority",
        authority_digest=A,
    )
    result = apply_active_transition(
        state,
        p,
        "execution_completed",
        (ev("execution_result"),),
        action_ref="action://execute",
        observed_at="2026-09-23T16:00:00Z",
        summary="Execution completed",
        canonical_refs=("artifact://canonical",),
        authority_grant=grant,
    )
    assert result.new_state.active.state == "verifying"
    assert result.authority_grant_digest == grant.digest
    assert "artifact://bounded-authority" in result.checkpoint.canonical_refs


def test_passive_wake_requires_explicit_satisfaction_evidence():
    state = portfolio("verifying")
    with pytest.raises(AspTransitionError, match="policy-required evidence"):
        admit_passive_wake(
            state,
            policy(),
            "PASSIVE",
            (ev("wrong"),),
        )

    admission = admit_passive_wake(
        state,
        policy(),
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    assert admission.work_id == "PASSIVE"
    assert admission.portfolio_state_digest == state.digest
    assert admission.wake_condition_digest == state.passive[0].wake_condition.digest


def test_woken_passive_can_fill_secondary_slot_during_verified_rotation():
    state = portfolio("verifying")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )

    result = apply_active_transition(
        state,
        p,
        "verification_passed",
        (ev("verifier_pass"),),
        action_ref="verify://active",
        observed_at="2026-09-23T16:00:00Z",
        summary="Verifier passed",
        canonical_refs=("artifact://canonical",),
        wake_admission=admission,
    )

    assert result.new_state.active.work_id == "SECONDARY"
    assert result.new_state.secondary.work_id == "PASSIVE"
    assert result.new_state.secondary.role == "secondary"
    assert result.new_state.secondary.state == "ready"
    assert result.new_state.passive == ()
    assert result.wake_admission_digest == admission.digest




def test_wake_admission_evidence_is_revalidated_when_consumed():
    state = portfolio("verifying")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    forged = replace(
        admission,
        evidence=(ev("wrong"),),
    )
    with pytest.raises(
        AspTransitionError,
        match="policy-required evidence",
    ):
        apply_active_transition(
            state,
            p,
            "verification_passed",
            (ev("verifier_pass"),),
            action_ref="verify://active",
            observed_at="2026-09-23T16:00:00Z",
            summary="Verifier passed",
            canonical_refs=("artifact://canonical",),
            wake_admission=forged,
        )


def test_wake_admission_authority_is_revalidated_when_consumed():
    state = portfolio("verifying")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    wake_rule = match_transition_rule(p, "passive", "wake_satisfied")
    forged_grant = TransitionAuthorityGrant(
        policy_digest=p.digest,
        rule_digest=wake_rule.digest,
        authority_boundary="not-authorized",
        authority_ref="artifact://forged-authority",
        authority_digest=A,
    )
    forged = replace(admission, authority_grant=forged_grant)
    with pytest.raises(
        AspTransitionError,
        match="ordinary transition cannot consume an authority grant",
    ):
        apply_active_transition(
            state,
            p,
            "verification_passed",
            (ev("verifier_pass"),),
            action_ref="verify://active",
            observed_at="2026-09-23T16:00:00Z",
            summary="Verifier passed",
            canonical_refs=("artifact://canonical",),
            wake_admission=forged,
        )


def test_stale_wake_admission_is_rejected():
    state = portfolio("verifying")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    newer = PortfolioState(
        portfolio_id=state.portfolio_id,
        generation=1,
        active=state.active,
        secondary=state.secondary,
        passive=state.passive,
        previous_state_digest=state.digest,
    )

    with pytest.raises(AspTransitionError, match="stale"):
        apply_active_transition(
            newer,
            p,
            "verification_passed",
            (ev("verifier_pass"),),
            action_ref="verify://active",
            observed_at="2026-09-23T16:00:00Z",
            summary="Verifier passed",
            canonical_refs=("artifact://canonical",),
            wake_admission=admission,
        )


def test_transition_result_commits_atomically_with_checkpoint_and_recovers(tmp_path):
    state = portfolio("ready")
    result = apply(state, "execution_started", (ev("dispatch_admitted"),))

    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    head = store.commit(
        state.portfolio_id,
        state.digest,
        result.new_state,
        result.checkpoint,
    )
    recovered, checkpoint, report = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(tmp_path / "portfolio.db"),
        state.portfolio_id,
    )

    assert recovered == result.new_state
    assert checkpoint == result.checkpoint
    assert head.latest_checkpoint_digest == result.checkpoint.digest
    assert report.checkpoint_present
    assert not report.fabricated_state
    assert not report.fabricated_checkpoint


def test_input_state_is_immutable_after_rotation():
    state = portfolio("verifying")
    p = policy()
    admission = admit_passive_wake(
        state,
        p,
        "PASSIVE",
        (ev("wake_condition_satisfied"),),
    )
    before = state
    _ = apply_active_transition(
        state,
        p,
        "verification_passed",
        (ev("verifier_pass"),),
        action_ref="verify://active",
        observed_at="2026-09-23T16:00:00Z",
        summary="Verifier passed",
        canonical_refs=("artifact://canonical",),
        wake_admission=admission,
    )
    assert state == before
    assert state.active.work_id == "ACTIVE"
    assert state.secondary.work_id == "SECONDARY"
