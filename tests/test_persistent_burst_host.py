from __future__ import annotations

import hashlib
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
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)
from general_execution.external_trigger import ExternalTriggerEvidence, TriggerContract
from general_execution.persistent_burst_host import (
    PersistentBurstEventRef,
    PersistentBurstHostError,
    PersistentBurstManifest,
    execute_persistent_burst,
)
from general_execution.persistent_runtime import process_persistent_runtime_event
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import portfolio_state_to_dict
from general_execution.transition_policy import transition_policy_to_dict

REVISION = "b" * 40


def digest(value):
    return sha256_digest(value)


def raw_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def encoded(value):
    return json.loads(canonical_json(value))


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://native-burst-host",
        required_verifier_ref="verifier://native-burst-host",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://native-burst-host-core",
        evidence_digest=digest("native-burst-host-core"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-10-07T06:30:00Z",
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
    return requirement, receipt, build_core_rehearsal_report(
        REVISION, receipt.digest, assertions
    )


def initial_portfolio():
    return PortfolioState(
        portfolio_id="native-burst-test",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="Exercise native Autonomous Burst host",
            active_gate="AB-NRA-001",
            next_action_ref="action://start",
            source_revision="native-burst-test",
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain available",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="native-burst-test",
        ),
        passive=(),
    )


def policy():
    return TransitionPolicy(
        policy_id="native-burst-test-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-start",
                from_state="ready",
                event="execution_started",
                to_state="running",
                next_action_ref="action://finish-work",
                required_evidence=("execution_start",),
            ),
            TransitionRule(
                rule_id="02-finish",
                from_state="running",
                event="execution_completed",
                to_state="verifying",
                next_action_ref="action://verify",
                required_evidence=("execution_complete",),
            ),
            TransitionRule(
                rule_id="03-human-stop",
                from_state="verifying",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://native-burst/final-promotion",
                effect="stop_human_gate",
                required_evidence=("promotion_boundary",),
                authority_mode="human_required",
                authority_boundary="native burst promotion requires Waterfound authority",
            ),
        ),
    )


def bootstrap(db):
    event = {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": "bootstrap-native-burst",
        "operation": "bootstrap",
        "body": {"portfolio": portfolio_state_to_dict(initial_portfolio())},
    }
    process_persistent_runtime_event(db, event)


def make_event(state, p, *, event_id, transition_event, evidence_kind, action_ref):
    evidence = CheckpointEvidence(
        kind=evidence_kind,
        locator=f"fixture://native-burst/{event_id}",
        digest=digest({"event": event_id, "kind": evidence_kind}),
    )
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event=transition_event,
        evidence=(evidence,),
        action_ref=action_ref,
        observed_at=f"2026-10-07T06:{state.generation + 31:02d}:00Z",
        summary=f"Native burst fixture {event_id}",
        canonical_refs=(f"fixture://native-burst/{event_id}",),
    )
    trigger = ExternalTriggerEvidence(
        source="github-push",
        event_id=event_id,
        event_kind="durable-transition",
        payload_digest=digest({"payload": event_id}),
        observation_digest=observation.digest,
        admission_ref=f"github://native-burst/{event_id}",
    )
    contract = TriggerContract(
        source=trigger.source,
        event_kind=trigger.event_kind,
        portfolio_id=state.portfolio_id,
        policy_digest=p.digest,
        transition_event=transition_event,
    )
    return {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": event_id,
        "operation": "transition",
        "body": {
            "policy": transition_policy_to_dict(p),
            "contract": encoded(contract),
            "trigger": encoded(trigger),
            "observation": encoded(observation),
        },
    }


def build_three_events(tmp_path):
    requirement, receipt, core_report = gate()
    builder_db = tmp_path / "builder.db"
    bootstrap(builder_db)
    p = policy()
    specs = [
        ("native-burst-step-1", "execution_started", "execution_start", "fixture://start"),
        ("native-burst-step-2", "execution_completed", "execution_complete", "fixture://finish"),
        ("native-burst-step-3", "authority_required", "promotion_boundary", "fixture://gate"),
    ]
    events = {}
    for event_id, transition_event, evidence_kind, action_ref in specs:
        state, _, _ = recover_portfolio_after_restart(
            SqlitePortfolioHeadStore(builder_db), initial_portfolio().portfolio_id
        )
        event = make_event(
            state,
            p,
            event_id=event_id,
            transition_event=transition_event,
            evidence_kind=evidence_kind,
            action_ref=action_ref,
        )
        events[event_id] = event
        from general_execution.persistent_runtime import trigger_digest_from_event
        process_persistent_runtime_event(
            builder_db,
            event,
            authenticated_trigger_digest=trigger_digest_from_event(event),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )
    return events, requirement, receipt, core_report


def materialize_events(tmp_path, events):
    root = tmp_path / "bundle"
    (root / "burst-events").mkdir(parents=True)
    refs = []
    for event_id, event in events.items():
        raw = (json.dumps(event, sort_keys=True, indent=2) + "\n").encode()
        rel = f"burst-events/{event_id}.json"
        (root / rel).write_bytes(raw)
        refs.append(PersistentBurstEventRef(path=rel, content_digest=raw_digest(raw)))
    return root, tuple(refs)


def manifest(refs, *, generation=0, state_digest=None, max_transitions=8):
    return PersistentBurstManifest(
        burst_id="native-burst-fixture-001",
        portfolio_id=initial_portfolio().portfolio_id,
        source_kind="hourly_watchdog",
        expected_start_generation=generation,
        expected_start_state_digest=state_digest or initial_portfolio().digest,
        max_transitions=max_transitions,
        event_refs=refs,
        created_at="2026-10-07T06:30:00Z",
    )


def loader(root):
    return lambda path: (root / path).read_bytes()


def test_native_host_executes_three_atomic_events_and_stops_at_human_gate(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)

    result = execute_persistent_burst(
        db,
        manifest(refs),
        loader(root),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )

    assert result.disposition == "stopped"
    assert result.stop_reason == "HUMAN_GATE"
    assert result.initial_generation == 0
    assert result.final_generation == 3
    assert [step.status for step in result.steps] == ["committed"] * 3
    assert [step.post_generation for step in result.steps] == [1, 2, 3]
    assert not result.authority_created

    state, checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db), initial_portfolio().portfolio_id
    )
    assert state.active.state == "human_gate"
    assert checkpoint is not None and checkpoint.authority_stop


def test_start_state_mismatch_mutates_nothing(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)

    result = execute_persistent_burst(
        db,
        manifest(refs, generation=1),
        loader(root),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )
    assert result.disposition == "start_state_mismatch"
    assert result.steps == ()
    assert result.final_generation == 0


def test_content_digest_mismatch_is_rejected_before_transition(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)
    bad = list(refs)
    bad[0] = PersistentBurstEventRef(
        path=bad[0].path,
        content_digest=digest("wrong-raw-content"),
    )

    with pytest.raises(PersistentBurstHostError, match="content digest mismatch"):
        execute_persistent_burst(
            db,
            manifest(tuple(bad)),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )
    state, _, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db), initial_portfolio().portfolio_id
    )
    assert state.generation == 0


def test_manifest_rejects_path_traversal_duplicate_paths_and_authority_creation():
    with pytest.raises(PersistentBurstHostError, match="safe and relative"):
        PersistentBurstEventRef(
            path="../events/x.json",
            content_digest=digest("x"),
        )
    ref = PersistentBurstEventRef(
        path="burst-events/x.json",
        content_digest=digest("x"),
    )
    with pytest.raises(PersistentBurstHostError, match="unique"):
        manifest((ref, ref))
    with pytest.raises(PersistentBurstHostError, match="cannot create authority"):
        PersistentBurstManifest(
            burst_id="x",
            portfolio_id="native-burst-test",
            source_kind="manual",
            expected_start_generation=0,
            expected_start_state_digest=initial_portfolio().digest,
            max_transitions=1,
            event_refs=(ref,),
            created_at="2026-10-07T06:30:00Z",
            authority_created=True,
        )


def test_credential_shaped_event_is_rejected(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    first_id = next(iter(events))
    events[first_id]["body"]["credential_hint"] = "forbidden"
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)

    with pytest.raises(PersistentBurstHostError, match="credential-shaped"):
        execute_persistent_burst(
            db,
            manifest(refs),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )


def test_manifest_exhaustion_requires_fresh_evidence_instead_of_synthesizing_next(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)

    result = execute_persistent_burst(
        db,
        manifest(refs[:1]),
        loader(root),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )
    assert result.stop_reason == "MANIFEST_EXHAUSTED_REQUIRES_FRESH_EVIDENCE"
    assert result.final_generation == 1
    assert len(result.steps) == 1


def test_non_transition_event_is_rejected(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    event_id = next(iter(events))
    events[event_id]["operation"] = "bootstrap"
    events[event_id]["body"] = {"portfolio": portfolio_state_to_dict(initial_portfolio())}
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)

    with pytest.raises(PersistentBurstHostError, match="transition events only"):
        execute_persistent_burst(
            db,
            manifest(refs),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )


def test_event_filename_must_match_identity(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    db = tmp_path / "runtime.db"
    bootstrap(db)
    first = refs[0]
    renamed = root / "burst-events/renamed.json"
    renamed.write_bytes((root / first.path).read_bytes())
    wrong = PersistentBurstEventRef(
        path="burst-events/renamed.json",
        content_digest=first.content_digest,
    )

    with pytest.raises(PersistentBurstHostError, match="filename must match event_id"):
        execute_persistent_burst(
            db,
            manifest((wrong,)),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )
