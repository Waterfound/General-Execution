from general_execution.autonomous_burst import (
    AutonomousBurstObservation,
    AutonomousBurstTransitionReceipt,
    AutonomousBurstTrigger,
)
from general_execution.autonomous_burst_host import (
    NativeBurstHostError,
    NativeBurstHostPolicy,
    run_native_autonomous_burst_host,
)


D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
E = "sha256:" + "4" * 64
T = "sha256:" + "5" * 64
C = "sha256:" + "6" * 64


def obs(generation, digest, status="admissible", action="action://next"):
    return AutonomousBurstObservation(
        portfolio_id="p",
        generation=generation,
        state_digest=digest,
        status=status,
        next_action_ref=action if status == "admissible" else None,
        evidence_digest=E,
        observed_at="2026-10-07T00:00:00Z",
    )


def receipt(pre, post, action="action://next"):
    return AutonomousBurstTransitionReceipt(
        portfolio_id="p",
        action_ref=action,
        pre_generation=pre,
        post_generation=post,
        pre_state_digest=D1 if pre == 0 else D2,
        post_state_digest=D2 if post == 1 else D3,
        transition_digest=T,
        checkpoint_digest=C,
    )


def trigger():
    return AutonomousBurstTrigger(
        kind="hourly_watchdog",
        source_ref="watchdog://hourly",
        observed_at="2026-10-07T00:00:00Z",
    )


def test_host_persists_every_atomic_receipt_before_fresh_successor():
    observations = iter([obs(0, D1), obs(1, D2), obs(2, D3, "done")])
    persisted = []
    executions = []

    def execute(o):
        executions.append(o.generation)
        return receipt(o.generation, o.generation + 1)

    def persist(r):
        persisted.append(r.post_generation)
        return f"receipt://{r.post_generation}"

    result = run_native_autonomous_burst_host(
        trigger=trigger(),
        observe_fresh=lambda: next(observations),
        execute_atomic=execute,
        persist_receipt=persist,
    )
    assert executions == [0, 1]
    assert persisted == [1, 2]
    assert result.final_generation == 2
    assert result.stop_reason == "CEILING_REACHED"


def test_host_stops_before_executor_on_human_gate():
    called = []
    result = run_native_autonomous_burst_host(
        trigger=trigger(),
        observe_fresh=lambda: obs(0, D1, "human_gate"),
        execute_atomic=lambda o: called.append(o),
        persist_receipt=lambda r: "never",
    )
    assert called == []
    assert result.stop_reason == "HUMAN_GATE"


def test_host_refuses_to_continue_when_receipt_is_not_persisted():
    observations = iter([obs(0, D1)])
    try:
        run_native_autonomous_burst_host(
            trigger=trigger(),
            observe_fresh=lambda: next(observations),
            execute_atomic=lambda o: receipt(0, 1),
            persist_receipt=lambda r: "",
        )
    except NativeBurstHostError as exc:
        assert "durably persisted" in str(exc)
    else:
        raise AssertionError("expected NativeBurstHostError")


def test_host_cannot_exceed_watchdog_safety_bounds():
    for transitions, seconds in ((9, 900), (8, 901)):
        try:
            NativeBurstHostPolicy(max_transitions=transitions, max_wall_seconds=seconds)
        except NativeBurstHostError:
            pass
        else:
            raise AssertionError("expected NativeBurstHostError")
