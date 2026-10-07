from __future__ import annotations

import pytest

from general_execution.autonomous_burst import (
    AutonomousBurstError,
    AutonomousBurstObservation,
    AutonomousBurstPolicy,
    AutonomousBurstTransitionReceipt,
    AutonomousBurstTrigger,
    plan_async_followup,
    run_autonomous_burst,
)
from general_execution.canonical import sha256_digest


def digest(value: str) -> str:
    return sha256_digest(value)


def obs(generation: int, status: str, action: str | None = None, verdict: str | None = None):
    return AutonomousBurstObservation(
        portfolio_id="ab-test",
        generation=generation,
        state_digest=digest(f"state-{generation}"),
        status=status,
        next_action_ref=action,
        evidence_digest=digest(f"evidence-{generation}-{status}"),
        observed_at=f"2026-10-07T05:{generation:02d}:00Z",
        continuity_verdict=verdict,
    )


def receipt(current: AutonomousBurstObservation):
    return AutonomousBurstTransitionReceipt(
        portfolio_id=current.portfolio_id,
        action_ref=current.next_action_ref,
        pre_generation=current.generation,
        post_generation=current.generation + 1,
        pre_state_digest=current.state_digest,
        post_state_digest=digest(f"state-{current.generation + 1}"),
        transition_digest=digest(f"transition-{current.generation}"),
        checkpoint_digest=digest(f"checkpoint-{current.generation}"),
    )


def trigger(kind="hourly_watchdog"):
    return AutonomousBurstTrigger(
        kind=kind,
        source_ref=f"fixture://{kind}",
        observed_at="2026-10-07T05:00:00Z",
    )


def test_three_atomic_transitions_continue_immediately_then_stop_at_human_gate():
    observations = iter(
        [
            obs(0, "admissible", "action://a"),
            obs(1, "admissible", "action://b"),
            obs(2, "admissible", "action://c"),
            obs(3, "human_gate"),
        ]
    )
    executed = []

    def observe():
        return next(observations)

    def execute_one(current):
        executed.append((current.generation, current.next_action_ref))
        return receipt(current)

    result = run_autonomous_burst(
        trigger(),
        AutonomousBurstPolicy(max_transitions=10),
        observe,
        execute_one,
        clock=lambda: 0.0,
    )

    assert executed == [(0, "action://a"), (1, "action://b"), (2, "action://c")]
    assert result.final_generation == 3
    assert len(result.transition_receipts) == 3
    assert result.stop_reason == "HUMAN_GATE"
    assert result.disposition == "stopped"
    assert not result.authority_created


def test_progressing_work_is_observed_not_redispatched():
    calls = []

    result = run_autonomous_burst(
        trigger("provider_event"),
        AutonomousBurstPolicy(),
        lambda: obs(4, "progressing"),
        lambda current: calls.append(current),
        clock=lambda: 0.0,
    )

    assert calls == []
    assert result.stop_reason == "ACTIVE_EXECUTION_OBSERVED"
    assert result.final_generation == 4


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("external_evidence_gate", "EXTERNAL_EVIDENCE_GATE"),
        ("condition_wait", "CONDITION_WAIT"),
        ("scheduled_wait", "SCHEDULED_WAIT"),
        ("done", "CEILING_REACHED"),
        ("failed", "FAILED"),
        ("stalled", "DEVELOPMENT_STALLED"),
        ("insufficient_evidence", "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_terminal_and_wait_statuses_fail_closed_without_execution(status, reason):
    called = []
    result = run_autonomous_burst(
        trigger(),
        AutonomousBurstPolicy(),
        lambda: obs(0, status),
        lambda current: called.append(current),
        clock=lambda: 0.0,
    )
    assert called == []
    assert result.stop_reason == reason


def test_constitution_authority_spend_and_credential_gates_stop_before_execution():
    base = dict(
        portfolio_id="ab-test",
        generation=0,
        state_digest=digest("state-0"),
        status="admissible",
        next_action_ref="action://a",
        evidence_digest=digest("evidence"),
        observed_at="2026-10-07T05:00:00Z",
    )
    variants = [
        ({"constitutional_gate_passed": False}, "CONSTITUTIONAL_GATE_CLOSED"),
        ({"authority_satisfied": False}, "AUTHORITY_REQUIRED"),
        ({"paid_spend_required": True}, "PAID_SPEND_GATE"),
        ({"credential_gate_satisfied": False}, "CREDENTIAL_GATE"),
    ]
    for override, reason in variants:
        called = []
        observation = AutonomousBurstObservation(**base, **override)
        result = run_autonomous_burst(
            trigger(),
            AutonomousBurstPolicy(),
            lambda observation=observation: observation,
            lambda current: called.append(current),
            clock=lambda: 0.0,
        )
        assert called == []
        assert result.stop_reason == reason


def test_every_successor_must_bind_exact_post_transition_state():
    observations = iter(
        [
            obs(0, "admissible", "action://a"),
            AutonomousBurstObservation(
                portfolio_id="ab-test",
                generation=1,
                state_digest=digest("wrong-state"),
                status="done",
                next_action_ref=None,
                evidence_digest=digest("evidence-wrong"),
                observed_at="2026-10-07T05:01:00Z",
            ),
        ]
    )
    with pytest.raises(AutonomousBurstError, match="exact post-transition state"):
        run_autonomous_burst(
            trigger(),
            AutonomousBurstPolicy(),
            lambda: next(observations),
            receipt,
            clock=lambda: 0.0,
        )


def test_transition_receipt_cannot_create_authority_or_paid_spend():
    with pytest.raises(AutonomousBurstError, match="cannot create authority"):
        AutonomousBurstTransitionReceipt(
            portfolio_id="ab-test",
            action_ref="action://a",
            pre_generation=0,
            post_generation=1,
            pre_state_digest=digest("a"),
            post_state_digest=digest("b"),
            transition_digest=digest("t"),
            checkpoint_digest=digest("c"),
            authority_created=True,
        )
    with pytest.raises(AutonomousBurstError, match="cannot create paid spend"):
        AutonomousBurstTransitionReceipt(
            portfolio_id="ab-test",
            action_ref="action://a",
            pre_generation=0,
            post_generation=1,
            pre_state_digest=digest("a"),
            post_state_digest=digest("b"),
            transition_digest=digest("t"),
            checkpoint_digest=digest("c"),
            paid_spend_created=True,
        )


def test_transition_budget_forces_full_reconciliation_without_batching_forever():
    state = {"generation": 0}

    def observe():
        g = state["generation"]
        return obs(g, "admissible", f"action://{g}")

    def execute_one(current):
        state["generation"] += 1
        return receipt(current)

    result = run_autonomous_burst(
        trigger(),
        AutonomousBurstPolicy(max_transitions=2),
        observe,
        execute_one,
        clock=lambda: 0.0,
    )
    assert result.disposition == "transition_budget_exhausted"
    assert result.stop_reason == "MAX_TRANSITIONS_REACHED"
    assert result.final_generation == 2
    assert len(result.transition_receipts) == 2


def test_wall_clock_lease_bounds_burst():
    times = iter([0.0, 0.0, 5.0, 11.0])
    state = {"generation": 0}

    def clock():
        return next(times)

    def observe():
        g = state["generation"]
        return obs(g, "admissible", f"action://{g}")

    def execute_one(current):
        state["generation"] += 1
        return receipt(current)

    result = run_autonomous_burst(
        trigger(),
        AutonomousBurstPolicy(max_wall_seconds=10),
        observe,
        execute_one,
        clock=clock,
    )
    assert result.disposition == "lease_exhausted"
    assert result.stop_reason == "BURST_WALL_CLOCK_LEASE_EXHAUSTED"
    assert result.final_generation == 2
    assert len(result.transition_receipts) == 2


def test_continuity_check_is_input_only_and_must_agree_with_normalized_status():
    observation = AutonomousBurstObservation.from_continuity(
        portfolio_id="ab-test",
        generation=0,
        state_digest=digest("state-0"),
        continuity_verdict="CHECKPOINTED_RESUMABLE",
        next_action_ref="action://resume",
        evidence_digest=digest("cc"),
        observed_at="2026-10-07T05:00:00Z",
    )
    assert observation.status == "admissible"

    with pytest.raises(AutonomousBurstError, match="disagrees"):
        AutonomousBurstObservation(
            portfolio_id="ab-test",
            generation=0,
            state_digest=digest("state-0"),
            status="progressing",
            next_action_ref=None,
            evidence_digest=digest("cc"),
            observed_at="2026-10-07T05:00:00Z",
            continuity_verdict="CHECKPOINTED_RESUMABLE",
        )


def test_provider_event_is_preferred_and_heartbeat_is_fallback_only():
    current = obs(2, "progressing")
    policy = AutonomousBurstPolicy(heartbeat_fallback_seconds=900)

    native = plan_async_followup(
        current,
        provider_completion_event_available=True,
        expected_long_running=True,
        policy=policy,
    )
    assert native.kind == "provider_event"
    assert native.delay_seconds is None

    fallback = plan_async_followup(
        current,
        provider_completion_event_available=False,
        expected_long_running=True,
        policy=policy,
    )
    assert fallback.kind == "heartbeat"
    assert fallback.delay_seconds == 900

    with pytest.raises(AutonomousBurstError, match=">= 900"):
        AutonomousBurstPolicy(heartbeat_fallback_seconds=899)
