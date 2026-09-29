from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from general_execution import (
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    PortfolioEntry,
    PortfolioState,
    sha256_digest,
)
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)
from general_execution.persistent_runtime import (
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import portfolio_state_to_dict
from general_execution.provider_host import provider_watch_contract_from_dict
from general_execution.workstream_result_handoff import (
    ObservedWorkstreamResult,
    WorkstreamResultHandoffError,
    reconcile_workstream_result,
    workstream_result_watch_from_dict,
)

ROOT = Path(__file__).resolve().parents[1]
WATCH = ROOT / "provider-result-watches/fae-a3-r4-control-repair-r1-replay.json"
CONTRACT = ROOT / "provider-contracts/fae-a3-r4-control-repair-r1-replay.json"
RESULT = ROOT / "tests/fixtures/fae_a3_r4_control_repair_r1_provider_result.json"
R1_RESULT_COMMIT = "6181e3d015c40d5075269b3d5fb43fb6442e2901"
AUTHORITY_REF = "github://Waterfound/General-Execution/authority/fae-a3-r4-control-plane-repair"
CORE_REVISION = "c" * 40


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def state(*, generation=7, authority=True):
    return PortfolioState(
        portfolio_id="fae-asic-a3-r4-existing-afi-admission",
        generation=generation,
        active=PortfolioEntry(
            work_id="FAE-A3-R4",
            role="active",
            state="rework",
            objective="Repair control-plane liveness within existing authority",
            active_gate="A3-R4-CONTROL-REPAIR",
            next_action_ref="action://fae-asic/a3/r4/repair-control-plane-liveness",
            source_revision="895c26daa6327c9171e30344a788feff0456b010",
            authority_boundary=(
                "Smallest A3-R4 control-plane repair plus static validation only"
                if authority else None
            ),
            authority_ref=AUTHORITY_REF if authority else None,
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain serialized",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="general-execution",
        ),
        passive=(),
        previous_state_digest=(
            None if generation == 0 else "sha256:" + "1" * 64
        ),
    )


def observed(payload=None, *, source_commit=R1_RESULT_COMMIT):
    raw = RESULT.read_bytes()
    return ObservedWorkstreamResult(
        source_commit=source_commit,
        observed_at="2026-09-28T23:53:00Z",
        content_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        payload=load(RESULT) if payload is None else payload,
    )


def watch():
    return workstream_result_watch_from_dict(load(WATCH))


def contract():
    return provider_watch_contract_from_dict(load(CONTRACT))


def gate():
    requirement = CoreVerificationRequirement(
        required_revision=CORE_REVISION,
        required_suite_ref="tests://workstream-result-handoff",
        required_verifier_ref="verifier://workstream-result-handoff",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=CORE_REVISION,
        suite_ref=requirement.required_suite_ref,
        evidence_ref="artifact://workstream-result-handoff-core",
        evidence_digest=sha256_digest("workstream-result-handoff-core"),
        verifier_ref=requirement.required_verifier_ref,
        executed_at="2026-09-29T01:00:00Z",
        passed=True,
        test_count=1,
    )
    assertions = tuple(
        CoreRehearsalAssertion(
            assertion_id=assertion_id,
            passed=True,
            evidence_refs=(f"fixture://{assertion_id}",),
            evidence_digests=(sha256_digest({"assertion": assertion_id}),),
        )
        for assertion_id in sorted(REQUIRED_CORE1_ASSERTIONS)
    )
    return requirement, receipt, build_core_rehearsal_report(
        CORE_REVISION, receipt.digest, assertions
    )


def test_fae_r1_historical_replay_materializes_explicit_next_frontier():
    handoff = reconcile_workstream_result(state(), watch(), contract(), observed())

    assert handoff.transition_class == "NEXT_FRONTIER_DISPATCHED"
    assert handoff.observed_state == "REFINE_WITHIN_EXISTING_REPAIR_AUTHORITY"
    assert handoff.authority_created is False
    assert handoff.provider_result.status == "event_ready"
    assert handoff.runtime_event["operation"] == "transition"
    assert handoff.runtime_event["body"]["observation"]["expected_generation"] == 7
    rule = handoff.runtime_event["body"]["policy"]["rules"][0]
    assert rule["to_state"] == "rework"
    assert rule["next_action_ref"] == "action://fae-asic/a3/r4/repair-control-plane-liveness"
    assert rule["authority_mode"] == "none"
    refs = handoff.runtime_event["body"]["observation"]["canonical_refs"]
    assert any(R1_RESULT_COMMIT in ref for ref in refs)


def test_same_evidence_replay_is_deterministic_and_idempotency_key_is_stable():
    first = reconcile_workstream_result(state(), watch(), contract(), observed())
    second = reconcile_workstream_result(state(), watch(), contract(), observed())

    assert first.handoff_id == second.handoff_id
    assert first.runtime_event["event_id"] == second.runtime_event["event_id"]
    assert first.runtime_event == second.runtime_event


def test_runtime_generation_rebinds_event_but_not_evidence_handoff_identity():
    a = reconcile_workstream_result(state(generation=7), watch(), contract(), observed())
    b = reconcile_workstream_result(state(generation=8), watch(), contract(), observed())

    assert a.handoff_id == b.handoff_id
    assert a.runtime_event["event_id"] != b.runtime_event["event_id"]


def test_result_commit_change_changes_handoff_identity():
    a = reconcile_workstream_result(state(), watch(), contract(), observed())
    b = reconcile_workstream_result(
        state(), watch(), contract(), observed(source_commit="2" * 40)
    )
    assert a.handoff_id != b.handoff_id


def test_existing_authority_is_required_for_refinement():
    with pytest.raises(WorkstreamResultHandoffError, match="existing authority"):
        reconcile_workstream_result(
            state(authority=False), watch(), contract(), observed()
        )


def test_stale_candidate_revision_fails_closed():
    payload = load(RESULT)
    payload["source_commit"] = "3" * 40
    with pytest.raises(WorkstreamResultHandoffError, match="source revision mismatch"):
        reconcile_workstream_result(state(), watch(), contract(), observed(payload))


def test_unknown_result_disposition_fails_closed_instead_of_silent_noop():
    payload = load(RESULT)
    payload["disposition"] = "SOMETHING_NEW"
    with pytest.raises(WorkstreamResultHandoffError, match="no explicit outcome contract"):
        reconcile_workstream_result(state(), watch(), contract(), observed(payload))


def test_contract_source_binding_substitution_fails_closed():
    raw = load(CONTRACT)
    raw["required_bindings"]["result_path"] = "wrong/result.json"
    bad = provider_watch_contract_from_dict(raw)
    with pytest.raises(WorkstreamResultHandoffError, match="source bindings mismatch"):
        reconcile_workstream_result(state(), watch(), bad, observed())


def test_handoff_event_is_consumed_by_persistent_runtime_without_human_prompt(tmp_path):
    initial = state(generation=0)
    handoff = reconcile_workstream_result(initial, watch(), contract(), observed())
    db = tmp_path / "runtime.db"
    bootstrap = {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": "workstream-result-handoff-bootstrap",
        "operation": "bootstrap",
        "body": {"portfolio": portfolio_state_to_dict(initial)},
    }
    process_persistent_runtime_event(db, bootstrap)
    admission = trigger_digest_from_event(handoff.runtime_event)
    requirement, receipt, report = gate()

    first = process_persistent_runtime_event(
        db,
        handoff.runtime_event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )
    second = process_persistent_runtime_event(
        db,
        handoff.runtime_event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )

    assert first.status == "committed"
    assert first.human_required is False
    assert first.post_generation == 1
    assert second.status == "already_applied"
    durable, checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(db),
        initial.portfolio_id,
    )
    assert durable.generation == 1
    assert durable.active.state == "rework"
    assert durable.active.next_action_ref == "action://fae-asic/a3/r4/repair-control-plane-liveness"
    assert durable.active.authority_ref == AUTHORITY_REF
    assert checkpoint is not None
