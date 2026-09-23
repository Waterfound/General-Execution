from dataclasses import replace

import pytest

from general_execution import (
    AspTransitionError,
    CheckpointEvidence,
    PassiveWakeSignal,
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
    TransitionPolicy,
    TransitionRule,
    WakeCondition,
    admit_passive_wake,
    apply_asp_transition,
)

D = "sha256:" + "a" * 64


def ev(kind, locator=None):
    return CheckpointEvidence(
        kind=kind,
        locator=locator or f"artifact://{kind}",
        digest=D,
    )


def active(state="running", **changes):
    values = dict(
        work_id="ACTIVE",
        role="active",
        state=state,
        objective="active objective",
        active_gate="ACTIVE_GATE",
        next_action_ref="action://active-fragment",
        source_revision="src-active",
        evidence_required=("proof",),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def secondary():
    return PortfolioEntry(
        work_id="SECONDARY",
        role="secondary",
        state="ready",
        objective="secondary objective",
        active_gate="SECONDARY_GATE",
        next_action_ref="action://secondary-first",
        source_revision="src-secondary",
    )


def passive(work_id, wake_value):
    return PortfolioEntry(
        work_id=work_id,
        role="passive",
        state="passive",
        objective=f"passive {work_id}",
        active_gate=f"{work_id}_GATE",
        next_action_ref=f"action://{work_id.lower()}",
        source_revision=f"src-{work_id.lower()}",
        blockers=(
            PortfolioBlocker(
                kind="external_dependency",
                detail="execution lane unavailable",
            ),
        ),
        wake_condition=WakeCondition(
            kind="event_received",
            value=wake_value,
        ),
    )


def portfolio(state="running"):
    return PortfolioState(
        portfolio_id="portfolio-1",
        generation=0,
        active=active(state),
        secondary=secondary(),
        passive=(
            passive("PASSIVE-A", "secondary_slot.available"),
            passive("PASSIVE-B", "external.ready"),
        ),
    )


def policy():
    rules = (
        TransitionRule(
            rule_id="01-start",
            from_state="ready",
            event="execution_started",
            to_state="running",
            next_action_ref="action://execute",
            required_evidence=("execution_authorization",),
        ),
        TransitionRule(
            rule_id="02-complete-fragment",
            from_state="running",
            event="execution_completed",
            to_state="verifying",
            next_action_ref="action://verify",
            required_evidence=("execution_result",),
        ),
        TransitionRule(
            rule_id="03-promote",
            from_state="verifying",
            event="verification_passed",
            to_state="complete",
            next_action_ref="action://promote-secondary",
            effect="promote_secondary",
            required_evidence=("verifier_pass", "wake_evidence"),
        ),
        TransitionRule(
            rule_id="04-park",
            from_state="running",
            event="external_blocker",
            to_state="passive",
            next_action_ref="action://park-active",
            effect="park_active",
            required_evidence=(
                "blocker_evidence",
                "no_internal_work",
                "wake_evidence",
            ),
        ),
        TransitionRule(
            rule_id="05-di",
            from_state="running",
            event="diagnosis_required",
            to_state="di_required",
            next_action_ref="action://invoke-di",
            effect="request_di",
            required_evidence=("failure_evidence",),
        ),
        TransitionRule(
            rule_id="06-human",
            from_state="running",
            event="authority_required",
            to_state="human_gate",
            next_action_ref="authority://request-human-decision",
            effect="stop_human_gate",
            required_evidence=("authority_evidence",),
            authority_mode="human_required",
            authority_boundary="release approval required",
        ),
        TransitionRule(
            rule_id="07-wake",
            from_state="passive",
            event="wake_satisfied",
            to_state="ready",
            next_action_ref="action://enter-secondary",
            effect="wake_passive",
            required_evidence=("wake_evidence",),
        ),
    )
    return TransitionPolicy(
        policy_id="asp-v1",
        revision="1",
        rules=rules,
    )


def wake_admission(state, p, work_id="PASSIVE-A"):
    entry = next(item for item in state.passive if item.work_id == work_id)
    evidence = ev("wake_evidence", "event://secondary-slot")
    signal = PassiveWakeSignal(
        work_id=entry.work_id,
        condition_digest=entry.wake_condition.digest,
        evidence_digest=evidence.evidence_digest,
    )
    return admit_passive_wake(p, entry, signal, (evidence,)), evidence


def test_passive_wake_requires_exact_condition_and_admitted_evidence():
    state = portfolio()
    p = policy()
    entry = state.passive[0]
    evidence = ev("wake_evidence")
    with pytest.raises(AspTransitionError, match="condition does not match"):
        admit_passive_wake(
            p,
            entry,
            PassiveWakeSignal(
                work_id=entry.work_id,
                condition_digest="sha256:" + "f" * 64,
                evidence_digest=evidence.evidence_digest,
            ),
            (evidence,),
        )
    with pytest.raises(AspTransitionError, match="evidence is not admitted"):
        admit_passive_wake(
            p,
            entry,
            PassiveWakeSignal(
                work_id=entry.work_id,
                condition_digest=entry.wake_condition.digest,
                evidence_digest="sha256:" + "e" * 64,
            ),
            (evidence,),
        )


def test_passive_wake_produces_ready_secondary_candidate_only():
    state = portfolio()
    p = policy()
    admission, evidence = wake_admission(state, p)
    assert admission.candidate_secondary.role == "secondary"
    assert admission.candidate_secondary.state == "ready"
    assert admission.candidate_secondary.blockers == ()
    assert admission.candidate_secondary.wake_condition is None
    assert admission.evidence_digest == evidence.evidence_digest


def test_generic_transition_constructs_next_generation_and_checkpoint():
    state = portfolio("running")
    p = policy()
    result = apply_asp_transition(
        state,
        p,
        "execution_completed",
        (ev("execution_result"),),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="fragment completed",
        canonical_refs=("commit:abc",),
    )
    assert result.next_state.generation == 1
    assert result.next_state.previous_state_digest == state.digest
    assert result.next_state.active.state == "verifying"
    assert result.next_state.active.next_action_ref == "action://verify"
    assert result.next_state.secondary == state.secondary
    assert result.next_state.passive == state.passive
    assert result.checkpoint.portfolio_state_digest == result.next_state.digest
    assert result.checkpoint.state_before == "running"
    assert result.checkpoint.state_after == "verifying"


def test_missing_required_evidence_fails_closed():
    state = portfolio("running")
    with pytest.raises(AspTransitionError, match="requirements not satisfied"):
        apply_asp_transition(
            state,
            policy(),
            "execution_completed",
            (ev("wrong"),),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="fragment completed",
            canonical_refs=("commit:abc",),
        )


def test_unmatched_transition_fails_closed():
    with pytest.raises(AspTransitionError, match="not policy-admissible"):
        apply_asp_transition(
            portfolio("running"),
            policy(),
            "fatal_failure",
            (ev("failure_evidence"),),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="fatal",
            canonical_refs=("artifact:fatal",),
        )


def test_diagnosis_transition_does_not_invoke_or_repair_di():
    result = apply_asp_transition(
        portfolio("running"),
        policy(),
        "diagnosis_required",
        (ev("failure_evidence"),),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="diagnosis required",
        canonical_refs=("artifact:failure",),
    )
    assert result.effect == "request_di"
    assert result.next_state.active.state == "di_required"
    assert result.next_state.active.next_action_ref == "action://invoke-di"
    assert result.checkpoint.next_transition_refs == ("action://invoke-di",)


def test_human_gate_stops_without_automatic_next_transition():
    evidence = ev("authority_evidence", "artifact://authority")
    result = apply_asp_transition(
        portfolio("running"),
        policy(),
        "authority_required",
        (evidence,),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="authority required",
        canonical_refs=("artifact:authority",),
    )
    assert result.effect == "stop_human_gate"
    assert result.next_state.active.state == "human_gate"
    assert result.next_state.active.authority_boundary == "release approval required"
    assert result.next_state.active.blockers[0].kind == "authority"
    assert result.checkpoint.authority_stop
    assert result.checkpoint.next_transition_refs == ()


def test_verified_completion_promotes_secondary_and_consumes_woken_passive():
    state = portfolio("verifying")
    p = policy()
    admission, wake_evidence = wake_admission(state, p)
    result = apply_asp_transition(
        state,
        p,
        "verification_passed",
        (ev("verifier_pass"), wake_evidence),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="active verified complete",
        canonical_refs=("artifact:verifier",),
        wake_admission=admission,
    )
    assert result.effect == "promote_secondary"
    assert result.next_state.active.work_id == "SECONDARY"
    assert result.next_state.active.role == "active"
    assert result.next_state.active.state == "ready"
    assert result.next_state.secondary.work_id == "PASSIVE-A"
    assert result.next_state.secondary.role == "secondary"
    assert [item.work_id for item in result.next_state.passive] == ["PASSIVE-B"]
    assert result.checkpoint.work_id == "ACTIVE"
    assert result.checkpoint.state_after == "complete"
    assert result.checkpoint.next_transition_refs == ("action://secondary-first",)
    assert result.wake_admission_digest == admission.digest


def test_verified_completion_without_replacement_secondary_fails_closed():
    with pytest.raises(AspTransitionError, match="replacement secondary"):
        apply_asp_transition(
            portfolio("verifying"),
            policy(),
            "verification_passed",
            (ev("verifier_pass"), ev("wake_evidence")),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="verified",
            canonical_refs=("artifact:verifier",),
        )


def test_promotion_requires_active_verifying_even_if_policy_were_looser():
    p = policy()
    state = portfolio("running")
    # A matching promotion rule from running is structurally valid in TransitionPolicy,
    # but the ASP engine must enforce the frozen verified-completion invariant.
    loose_rules = tuple(
        replace(rule, from_state="running")
        if rule.rule_id == "03-promote"
        else rule
        for rule in p.rules
    )
    loose = TransitionPolicy(policy_id="loose", revision="1", rules=loose_rules)
    admission, wake_evidence = wake_admission(state, loose)
    with pytest.raises(AspTransitionError, match="requires active state verifying"):
        apply_asp_transition(
            state,
            loose,
            "verification_passed",
            (ev("verifier_pass"), wake_evidence),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="invalid promotion",
            canonical_refs=("artifact:verifier",),
            wake_admission=admission,
        )


def test_external_blocker_parks_active_promotes_secondary_and_preserves_wake():
    state = portfolio("running")
    p = policy()
    admission, wake_evidence = wake_admission(state, p)
    blockers = (
        PortfolioBlocker(
            kind="external_dependency",
            detail="Render unavailable",
            evidence_refs=("artifact://blocker",),
        ),
    )
    parked_wake = WakeCondition(
        kind="event_received",
        value="render.unsuspended",
    )
    result = apply_asp_transition(
        state,
        p,
        "external_blocker",
        (
            ev("blocker_evidence", "artifact://blocker"),
            ev("no_internal_work"),
            wake_evidence,
        ),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="active parked on external dependency",
        canonical_refs=("artifact:blocker",),
        wake_admission=admission,
        park_blockers=blockers,
        park_wake_condition=parked_wake,
    )
    assert result.effect == "park_active"
    assert result.next_state.active.work_id == "SECONDARY"
    assert result.next_state.secondary.work_id == "PASSIVE-A"
    assert [item.work_id for item in result.next_state.passive] == [
        "ACTIVE",
        "PASSIVE-B",
    ]
    parked = result.next_state.passive[0]
    assert parked.role == "passive"
    assert parked.state == "passive"
    assert parked.blockers == blockers
    assert parked.wake_condition == parked_wake
    assert result.checkpoint.work_id == "ACTIVE"
    assert result.checkpoint.state_after == "passive"


def test_parking_requires_blockers_and_wake_condition():
    state = portfolio("running")
    p = policy()
    admission, wake_evidence = wake_admission(state, p)
    evidence = (
        ev("blocker_evidence"),
        ev("no_internal_work"),
        wake_evidence,
    )
    with pytest.raises(AspTransitionError, match="requires explicit blockers"):
        apply_asp_transition(
            state,
            p,
            "external_blocker",
            evidence,
            observed_at="2026-09-23T13:00:00-03:00",
            summary="blocked",
            canonical_refs=("artifact:blocker",),
            wake_admission=admission,
            park_wake_condition=WakeCondition(
                "event_received",
                "provider.ready",
            ),
        )
    with pytest.raises(AspTransitionError, match="requires explicit wake condition"):
        apply_asp_transition(
            state,
            p,
            "external_blocker",
            evidence,
            observed_at="2026-09-23T13:00:00-03:00",
            summary="blocked",
            canonical_refs=("artifact:blocker",),
            wake_admission=admission,
            park_blockers=(PortfolioBlocker("external_dependency", "blocked"),),
        )


def test_wake_admission_from_another_policy_is_rejected():
    state = portfolio("verifying")
    p = policy()
    admission, wake_evidence = wake_admission(state, p)
    other = replace(p, policy_id="other")
    with pytest.raises(AspTransitionError, match="policy digest mismatch"):
        apply_asp_transition(
            state,
            other,
            "verification_passed",
            (ev("verifier_pass"), wake_evidence),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="verified",
            canonical_refs=("artifact:verifier",),
            wake_admission=admission,
        )


def test_lane_inputs_are_rejected_for_non_lane_transition():
    state = portfolio("running")
    p = policy()
    admission, _ = wake_admission(state, p)
    with pytest.raises(AspTransitionError, match="lane-management inputs"):
        apply_asp_transition(
            state,
            p,
            "execution_completed",
            (ev("execution_result"),),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="fragment",
            canonical_refs=("artifact:result",),
            wake_admission=admission,
        )


def test_application_identity_is_deterministic():
    state = portfolio("running")
    kwargs = dict(
        observed_at="2026-09-23T13:00:00-03:00",
        summary="fragment completed",
        canonical_refs=("commit:abc",),
    )
    left = apply_asp_transition(
        state,
        policy(),
        "execution_completed",
        (ev("execution_result"),),
        **kwargs,
    )
    right = apply_asp_transition(
        state,
        policy(),
        "execution_completed",
        (ev("execution_result"),),
        **kwargs,
    )
    assert left == right
    assert left.digest == right.digest


def test_preauthorized_transition_requires_evidence_bound_authority_reference():
    base = policy()
    extra = TransitionRule(
        rule_id="00-preauth",
        from_state="ready",
        event="execution_started",
        to_state="running",
        next_action_ref="action://authorized-run",
        required_evidence=("authority",),
        authority_mode="preauthorized_required",
        authority_boundary="bounded preauthorized execution",
    )
    rules = tuple(sorted((extra, *base.rules[1:]), key=lambda rule: rule.rule_id))
    p = TransitionPolicy(policy_id="preauth", revision="1", rules=rules)
    state = portfolio("ready")
    authority = ev("authority", "artifact://bounded-authority")
    with pytest.raises(AspTransitionError, match="requires authority reference"):
        apply_asp_transition(
            state,
            p,
            "execution_started",
            (authority,),
            observed_at="2026-09-23T13:00:00-03:00",
            summary="authorized run",
            canonical_refs=("artifact:authority",),
        )
    result = apply_asp_transition(
        state,
        p,
        "execution_started",
        (authority,),
        observed_at="2026-09-23T13:00:00-03:00",
        summary="authorized run",
        canonical_refs=("artifact:authority",),
        preauthorized_authority_ref="artifact://bounded-authority",
    )
    assert result.next_state.active.state == "running"
    assert result.next_state.active.authority_ref == "artifact://bounded-authority"
    assert result.next_state.active.authority_boundary == "bounded preauthorized execution"
