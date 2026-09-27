#!/usr/bin/env python3
"""Offline preflight harness for the final unattended pilot.

Each state-changing step runs in a fresh process and consumes exactly one
provider-neutral trigger. No live webhook/cron/provider trigger is activated.
The harness proves durable continuation through rework and an exact human
authority stop before any real unattended activation is authorized.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from general_execution import (
    CheckpointEvidence,
    CoreRehearsalAssertion,
    CoreRehearsalReport,
    PortfolioEntry,
    PortfolioState,
    ResumeTickObservation,
    ResumeTickResult,
    SqlitePortfolioHeadStore,
    TransitionPolicy,
    TransitionRule,
    canonical_json,
    recover_portfolio_after_restart,
    resume_tick,
    sha256_digest,
)
from general_execution.external_trigger import (
    ExternalTriggerEvidence,
    TriggerContract,
    consume_external_trigger,
)
from general_execution.verification_escalation import (
    IndependentVerificationResponse,
    admit_independent_verification,
    build_verification_observation,
    prepare_independent_verification,
)
from run_core1_rehearsal import admit as admit_core_verification

ROOT = Path(__file__).resolve().parents[1]
WAVE5 = ROOT / "evidence/durable-execution/2026-09-27/wave5-verification.json"
CORE1 = ROOT / "evidence/durable-execution/2026-09-27/core1-run-002/core1-receipt.json"
PORTFOLIO_ID = "durable-unattended-pilot"


def encode(value):
    return json.loads(canonical_json(value))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def gate():
    requirement, receipt = admit_core_verification(WAVE5)
    data = json.loads(CORE1.read_text(encoding="utf-8"))
    data["assertions"] = tuple(
        CoreRehearsalAssertion(
            **dict(
                item,
                evidence_refs=tuple(item["evidence_refs"]),
                evidence_digests=tuple(item["evidence_digests"]),
            )
        )
        for item in data["assertions"]
    )
    report = CoreRehearsalReport(**data)
    assert report.all_passed
    assert report.core_verification_receipt_digest == receipt.digest
    return requirement, receipt, report


def policy() -> TransitionPolicy:
    return TransitionPolicy(
        policy_id="unattended-pilot-v1",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-start",
                from_state="ready",
                event="execution_started",
                to_state="running",
                next_action_ref="action://observe-execution",
                required_evidence=("dispatch_admitted",),
            ),
            TransitionRule(
                rule_id="02-complete",
                from_state="running",
                event="execution_completed",
                to_state="verifying",
                next_action_ref="action://independent-verification",
                required_evidence=("execution_result",),
            ),
            TransitionRule(
                rule_id="03-reject",
                from_state="verifying",
                event="verification_failed",
                to_state="rework",
                next_action_ref="action://rework",
                required_evidence=("verifier_reject",),
            ),
            TransitionRule(
                rule_id="04-rework-start",
                from_state="rework",
                event="execution_started",
                to_state="running",
                next_action_ref="action://observe-rework",
                required_evidence=("rework_admitted",),
            ),
            TransitionRule(
                rule_id="05-authority-stop",
                from_state="running",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://release-approval",
                effect="stop_human_gate",
                required_evidence=("authority_boundary_reached",),
                authority_mode="human_required",
                authority_boundary="release approval",
            ),
        ),
    )


def genesis() -> PortfolioState:
    return PortfolioState(
        portfolio_id=PORTFOLIO_ID,
        generation=0,
        active=PortfolioEntry(
            work_id="PILOT-ACTIVE",
            role="active",
            state="ready",
            objective="Prove bounded unattended continuation",
            active_gate="PILOT",
            next_action_ref="action://execute",
            source_revision="unattended-pilot-preflight",
            evidence_required=("result",),
        ),
        secondary=PortfolioEntry(
            work_id="PILOT-SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain ready without competing for execution",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="unattended-pilot-preflight",
        ),
        passive=(),
    )


def evidence(kind: str, step: str) -> CheckpointEvidence:
    return CheckpointEvidence(
        kind=kind,
        locator=f"pilot://{step}/{kind}",
        digest=sha256_digest({"pilot": "unattended-preflight-v1", "step": step, "kind": kind}),
    )


def observation(state: PortfolioState, transition_event: str, kind: str, step: str) -> ResumeTickObservation:
    p = policy()
    return ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event=transition_event,
        evidence=(evidence(kind, step),),
        action_ref=f"pilot://{step}",
        observed_at="2026-09-27T15:15:00Z",
        summary=f"Unattended pilot preflight step {step}",
        canonical_refs=(f"pilot://artifact/{step}",),
    )


def consume(out: Path, step: str, obs: ResumeTickObservation) -> ResumeTickResult:
    requirement, receipt, report = gate()
    p = policy()
    event = ExternalTriggerEvidence(
        source="pilot-offline-host",
        event_id=f"{step}-{obs.expected_generation}",
        event_kind=step,
        payload_digest=sha256_digest(
            {"step": step, "generation": obs.expected_generation, "observation": obs.digest}
        ),
        observation_digest=obs.digest,
        admission_ref=f"pilot-admission://{step}/{obs.expected_generation}",
    )
    contract = TriggerContract(
        source=event.source,
        event_kind=event.event_kind,
        portfolio_id=obs.portfolio_id,
        policy_digest=p.digest,
        transition_event=obs.event,
    )
    return consume_external_trigger(
        out / "pilot.db",
        contract,
        event,
        obs,
        p,
        authenticated_admission_digest=event.digest,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )


def load_state(out: Path):
    return SqlitePortfolioHeadStore(out / "pilot.db").load(PORTFOLIO_ID)[0]


def load_tick(path: Path) -> ResumeTickResult:
    return ResumeTickResult(**json.loads(path.read_text(encoding="utf-8"))["tick"])


def decode_verification_observation(data) -> ResumeTickObservation:
    values = dict(data)
    values["evidence"] = tuple(CheckpointEvidence(**item) for item in data["evidence"])
    return ResumeTickObservation(**values)


def worker(mode: str, out: Path) -> None:
    if mode == "init":
        state = genesis()
        SqlitePortfolioHeadStore(out / "pilot.db").initialize(state)
        write(out / "00-init.json", {"pid": os.getpid(), "state": encode(state)})
        return

    if mode == "execution-start":
        state = load_state(out)
        tick = consume(out, mode, observation(state, "execution_started", "dispatch_admitted", mode))
        assert tick.disposition == "committed" and tick.post_generation == 1
        write(out / "01-execution-start.json", {"pid": os.getpid(), "tick": encode(tick)})
        return

    if mode == "execution-complete":
        state = load_state(out)
        tick = consume(out, mode, observation(state, "execution_completed", "execution_result", mode))
        assert tick.disposition == "committed" and tick.post_generation == 2
        write(out / "02-execution-complete.json", {"pid": os.getpid(), "tick": encode(tick)})
        return

    if mode == "project-assurance-reject":
        p = policy()
        tick = load_tick(out / "02-execution-complete.json")
        store = SqlitePortfolioHeadStore(out / "pilot.db")
        state, _ = store.load(PORTFOLIO_ID)
        checkpoint = store.latest_checkpoint(PORTFOLIO_ID)
        assert checkpoint is not None
        assert state.active.state == "verifying"
        request = prepare_independent_verification(
            tick,
            checkpoint,
            policy_digest=p.digest,
            executor_id="pilot-executor",
            worker_id="pilot-worker",
            subject_digest=sha256_digest({"pilot-subject": "v1"}),
            evidence_digest=sha256_digest({"execution-evidence": checkpoint.digest}),
        )
        response = IndependentVerificationResponse(
            request_digest=request.digest,
            verifier_system="project_assurance",
            verifier_id="project-assurance-pilot",
            subject_digest=request.subject_digest,
            evidence_digest=sha256_digest({"project-assurance": "rejected"}),
            outcome="reject",
            findings=("bounded-rework-required",),
            red_team_recommended=False,
        )
        admission = admit_independent_verification(
            request,
            response,
            authenticated_response_digest=response.digest,
        )
        obs = build_verification_observation(
            request,
            response,
            admission,
            observed_at="2026-09-27T15:16:00Z",
            summary="Independent Project Assurance rejection requires bounded rework",
        )
        write(
            out / "03-project-assurance.json",
            {
                "pid": os.getpid(),
                "request": encode(request),
                "response": encode(response),
                "admission": encode(admission),
                "observation": encode(obs),
            },
        )
        return

    if mode == "verification-reject":
        data = json.loads((out / "03-project-assurance.json").read_text(encoding="utf-8"))
        obs = decode_verification_observation(data["observation"])
        tick = consume(out, mode, obs)
        assert tick.disposition == "committed" and tick.post_generation == 3
        state = load_state(out)
        assert state.active.state == "rework"
        write(out / "04-verification-reject.json", {"pid": os.getpid(), "tick": encode(tick)})
        return

    if mode == "rework-start":
        state = load_state(out)
        tick = consume(out, mode, observation(state, "execution_started", "rework_admitted", mode))
        assert tick.disposition == "committed" and tick.post_generation == 4
        write(out / "05-rework-start.json", {"pid": os.getpid(), "tick": encode(tick)})
        return

    if mode == "authority-stop":
        state = load_state(out)
        tick = consume(out, mode, observation(state, "authority_required", "authority_boundary_reached", mode))
        assert tick.disposition == "committed" and tick.post_generation == 5
        final = load_state(out)
        checkpoint = SqlitePortfolioHeadStore(out / "pilot.db").latest_checkpoint(PORTFOLIO_ID)
        assert final.active.state == "human_gate"
        assert final.active.authority_ref is None
        assert checkpoint is not None and checkpoint.authority_stop
        assert checkpoint.next_transition_refs == ()
        write(
            out / "06-authority-stop.json",
            {"pid": os.getpid(), "tick": encode(tick), "state": encode(final), "checkpoint": encode(checkpoint)},
        )
        return

    if mode == "recover":
        requirement, receipt, _ = gate()
        p = policy()
        store = SqlitePortfolioHeadStore(out / "pilot.db")
        state, checkpoint, recovery = recover_portfolio_after_restart(store, PORTFOLIO_ID)
        assert state.generation == 5 and state.active.state == "human_gate"
        assert checkpoint is not None and checkpoint.authority_stop
        request = resume_tick(
            store,
            PORTFOLIO_ID,
            p,
            None,
            core_requirement=requirement,
            core_verification=receipt,
        )
        assert request.disposition == "external_input_required"
        assert request.human_required
        assert request.requested_action_ref == "authority://release-approval"
        write(
            out / "07-recovery.json",
            {
                "pid": os.getpid(),
                "state": encode(state),
                "checkpoint": encode(checkpoint),
                "recovery": encode(recovery),
                "request": encode(request),
            },
        )
        return

    raise ValueError(f"unknown worker mode: {mode}")


def orchestrate(out: Path) -> None:
    if out.exists():
        raise AssertionError("Refusing to overwrite unattended pilot evidence")
    out.mkdir(parents=True)
    modes = (
        "init",
        "execution-start",
        "execution-complete",
        "project-assurance-reject",
        "verification-reject",
        "rework-start",
        "authority-stop",
        "recover",
    )
    for mode in modes:
        subprocess.run(
            [sys.executable, __file__, "--worker", mode, "--output", str(out)],
            cwd=ROOT,
            check=True,
        )
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(out.glob("[0-9][0-9]-*.json"))
    ]
    final = json.loads((out / "07-recovery.json").read_text(encoding="utf-8"))
    proof = {
        "schema_version": "ge.unattended-pilot-preflight.v1",
        "status": "PASS_NOT_ACTIVATED",
        "process_invocations": len(records),
        "state_transitions": 5,
        "final_generation": final["state"]["generation"],
        "final_state": final["state"]["active"]["state"],
        "authority_stop": final["checkpoint"]["authority_stop"],
        "human_required": final["request"]["human_required"],
        "chat_context_required": False,
        "provider_trigger_enabled": False,
        "unattended_runtime_enabled": False,
        "real_activation_authorized": False,
        "worker_pids": [record["pid"] for record in records],
    }
    assert proof["process_invocations"] == 8
    assert proof["final_generation"] == 5
    assert proof["final_state"] == "human_gate"
    assert proof["authority_stop"] and proof["human_required"]
    write(out / "pilot-preflight-report.json", proof)
    print(json.dumps(proof, sort_keys=True))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker")
    args = parser.parse_args(argv)
    if args.worker:
        worker(args.worker, args.output)
    else:
        orchestrate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
