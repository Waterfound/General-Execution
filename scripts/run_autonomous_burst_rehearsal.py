#!/usr/bin/env python3
import json

from general_execution import sha256_digest
from general_execution.autonomous_burst import (
    AutonomousBurstObservation,
    AutonomousBurstPolicy,
    AutonomousBurstTransitionReceipt,
    AutonomousBurstTrigger,
    run_autonomous_burst,
)


def d(value):
    return sha256_digest(value)


state = {"generation": 0}

def observe():
    g = state["generation"]
    if g >= 3:
        return AutonomousBurstObservation(
            portfolio_id="ab-001-rehearsal",
            generation=g,
            state_digest=d(f"state-{g}"),
            status="human_gate",
            next_action_ref=None,
            evidence_digest=d(f"evidence-{g}"),
            observed_at=f"2026-10-07T05:0{g}:00Z",
            continuity_verdict="HUMAN_GATE",
        )
    return AutonomousBurstObservation(
        portfolio_id="ab-001-rehearsal",
        generation=g,
        state_digest=d(f"state-{g}"),
        status="admissible",
        next_action_ref=f"action://step-{g + 1}",
        evidence_digest=d(f"evidence-{g}"),
        observed_at=f"2026-10-07T05:0{g}:00Z",
        continuity_verdict="CHECKPOINTED_RESUMABLE",
    )


def execute_one(current):
    post = current.generation + 1
    state["generation"] = post
    return AutonomousBurstTransitionReceipt(
        portfolio_id=current.portfolio_id,
        action_ref=current.next_action_ref,
        pre_generation=current.generation,
        post_generation=post,
        pre_state_digest=current.state_digest,
        post_state_digest=d(f"state-{post}"),
        transition_digest=d(f"transition-{current.generation}-{post}"),
        checkpoint_digest=d(f"checkpoint-{post}"),
    )


trigger = AutonomousBurstTrigger(
    kind="hourly_watchdog",
    source_ref="rehearsal://ab-001/hourly-wake",
    observed_at="2026-10-07T05:00:00Z",
)
result = run_autonomous_burst(
    trigger,
    AutonomousBurstPolicy(max_transitions=8, max_wall_seconds=900),
    observe,
    execute_one,
    clock=lambda: 0.0,
)

assert result.final_generation == 3
assert len(result.transition_receipts) == 3
assert result.stop_reason == "HUMAN_GATE"
assert result.authority_created is False

print(json.dumps({
    "schema": "ge.autonomous-burst-rehearsal.v1",
    "portfolio_id": result.portfolio_id,
    "initial_generation": result.initial_generation,
    "final_generation": result.final_generation,
    "atomic_transitions": len(result.transition_receipts),
    "stop_reason": result.stop_reason,
    "authority_created": result.authority_created,
    "result_digest": result.digest,
}, sort_keys=True))
