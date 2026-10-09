from __future__ import annotations

import base64
import json
import subprocess

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
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)
from general_execution.external_trigger import ExternalTriggerEvidence, TriggerContract
from general_execution.git_state_plane_transport import GitStatePlaneTransport
from general_execution.persistent_runtime import process_persistent_runtime_event
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import portfolio_state_to_dict
from general_execution.state_plane_host import execute_event_over_state_plane
from general_execution.transition_policy import transition_policy_to_dict


REVISION = "c" * 40


def sh(*args, cwd=None):
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def initial_state():
    return PortfolioState(
        portfolio_id="single-event-private-state",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="preserve current host semantics",
            active_gate="RUN",
            next_action_ref="action://start",
            source_revision=REVISION,
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="remain ready",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision=REVISION,
        ),
        passive=(),
    )


def policy():
    return TransitionPolicy(
        policy_id="single-event-private-state-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-start",
                from_state="ready",
                event="execution_started",
                to_state="running",
                next_action_ref="action://continue",
                required_evidence=("execution_start",),
            ),
        ),
    )


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://single-event-private-state",
        required_verifier_ref="verifier://single-event-private-state",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://single-event-private-state",
        evidence_digest=sha256_digest("single-event-private-state"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-10-09T07:30:00Z",
        passed=True,
        test_count=1,
    )
    assertions = tuple(
        CoreRehearsalAssertion(
            assertion_id=item,
            passed=True,
            evidence_refs=(f"fixture://{item}",),
            evidence_digests=(sha256_digest(item),),
        )
        for item in sorted(REQUIRED_CORE1_ASSERTIONS)
    )
    return requirement, receipt, build_core_rehearsal_report(
        REVISION, receipt.digest, assertions
    )


def transition_event(state):
    p = policy()
    evidence = CheckpointEvidence(
        kind="execution_start",
        locator="fixture://single-event/start",
        digest=sha256_digest("single-event-start"),
    )
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event="execution_started",
        evidence=(evidence,),
        action_ref="fixture://single-event/action",
        observed_at="2026-10-09T07:31:00Z",
        summary="single event private state transition",
        canonical_refs=("fixture://single-event",),
    )
    trigger = ExternalTriggerEvidence(
        source="provider-event",
        event_id="single-event-private-state-001",
        event_kind="durable-transition",
        payload_digest=sha256_digest("single-event-payload"),
        observation_digest=observation.digest,
        admission_ref="provider://single-event-private-state",
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
            "contract": json.loads(canonical_json(contract)),
            "trigger": json.loads(canonical_json(trigger)),
            "observation": json.loads(canonical_json(observation)),
        },
    }


def seed_remote(tmp_path):
    db = tmp_path / "seed.db"
    process_persistent_runtime_event(
        db,
        {
            "schema_version": "ge.persistent-runtime-event.v1",
            "event_id": "single-event-bootstrap",
            "operation": "bootstrap",
            "body": {"portfolio": portfolio_state_to_dict(initial_state())},
        },
    )
    payload = db.read_bytes()

    seed = tmp_path / "seed-repo"
    remote = tmp_path / "remote.git"
    seed.mkdir()
    sh("git", "init", "-q", cwd=seed)
    sh("git", "config", "user.name", "fixture", cwd=seed)
    sh("git", "config", "user.email", "fixture@example.invalid", cwd=seed)
    target = seed / "opaque" / "state"
    target.mkdir(parents=True)
    (target / "state.sqlite.b64").write_text(
        base64.b64encode(payload).decode("ascii") + "\n"
    )
    sh("git", "add", ".", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    sh("git", "branch", "-M", "state", cwd=seed)
    sh("git", "init", "--bare", "-q", str(remote))
    sh("git", "remote", "add", "origin", str(remote), cwd=seed)
    sh("git", "push", "-q", "origin", "state", cwd=seed)
    return remote


def make_transport(remote, workdir):
    return GitStatePlaneTransport(
        remote=str(remote),
        branch="state",
        root="opaque",
        state_ref="s_abcdef0123456789",
        workdir=workdir,
    )


def test_current_single_event_host_preserved_over_git_state_plane(tmp_path):
    remote = seed_remote(tmp_path)
    requirement, receipt, core_report = gate()

    event = transition_event(initial_state())
    execution, host_report = execute_event_over_state_plane(
        make_transport(remote, tmp_path / "run"),
        event,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
        persist_private_ledger=True,
        runtime_source_revision=REVISION,
        trigger_commit="d" * 40,
    )

    assert execution.status == "committed"
    assert execution.post_generation == 1
    assert host_report.execution_report_digest == execution.digest
    assert not host_report.authority_created

    verify_transport = make_transport(remote, tmp_path / "verify")
    _, payload = verify_transport.load()
    root = verify_transport.checkout / "opaque"
    report_file = root / "ledger" / "reports" / f"{event['event_id']}.json"
    processed_file = root / "ledger" / "processed" / f"{event['event_id']}.json"
    manifest_file = root / "state" / "manifest.json"
    assert report_file.is_file()
    assert processed_file.is_file()
    assert manifest_file.is_file()
    private_report = json.loads(report_file.read_text())
    processed = json.loads(processed_file.read_text())
    manifest = json.loads(manifest_file.read_text())
    assert private_report["event_report_digest"] == execution.digest
    assert processed["event_report_digest"] == execution.digest
    assert processed["runtime_source_revision"] == REVISION
    assert manifest["last_event_report_digest"] == execution.digest
    assert manifest["runtime_source_revision"] == REVISION
    assert processed["database_sha256"] == manifest["database_sha256"]

    db = tmp_path / "verify.db"
    db.write_bytes(payload)
    state, checkpoint, report = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db),
        initial_state().portfolio_id,
    )
    assert state.generation == 1
    assert state.active.state == "running"
    assert checkpoint is not None
    assert report.state_digest == execution.post_state_digest
