from __future__ import annotations

from dataclasses import replace

import pytest

from general_execution.canonical import sha256_digest
from general_execution.execution_checkpoint import CheckpointEvidence, ExecutionCheckpoint
from general_execution.human_gate_decision import (
    HumanGateDecision,
    HumanGateDecisionError,
    consume_human_gate_decision,
)
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import (
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
)


BOUNDARY = (
    "Authorize creation, only if absent, of a minimal read-only observer. "
    "No F2 runtime authority."
)
PENDING = "authority://durable/aws-readonly-oidc-observer"


def ready_entry(role: str, work_id: str) -> PortfolioEntry:
    return PortfolioEntry(
        work_id=work_id,
        role=role,
        state="ready",
        objective=f"{work_id} objective",
        active_gate=f"{work_id}-gate",
        next_action_ref=f"action://{work_id.lower()}",
        source_revision="test-source",
    )


def human_gate_store(tmp_path):
    store = SqlitePortfolioHeadStore(tmp_path / "state.db")
    g0 = PortfolioState(
        portfolio_id="terminal",
        generation=0,
        active=ready_entry("active", "ACTIVE"),
        secondary=ready_entry("secondary", "SECONDARY"),
    )
    store.initialize(g0)
    active = replace(
        g0.active,
        state="human_gate",
        next_action_ref=PENDING,
        authority_boundary=BOUNDARY,
        blockers=(
            PortfolioBlocker(
                kind="authority",
                detail="explicit Waterfound authority required",
                evidence_refs=("preflight://observer",),
            ),
        ),
    )
    g1 = PortfolioState(
        portfolio_id=g0.portfolio_id,
        generation=1,
        active=active,
        secondary=g0.secondary,
        passive=(),
        previous_state_digest=g0.digest,
    )
    ev = CheckpointEvidence(
        kind="authority_required",
        locator="preflight://observer",
        digest=sha256_digest({"observer": "required"}),
    )
    cp = ExecutionCheckpoint(
        portfolio_id=g1.portfolio_id,
        portfolio_generation=1,
        portfolio_state_digest=g1.digest,
        work_id=active.work_id,
        role="active",
        state_before="ready",
        state_after="human_gate",
        action_ref=PENDING,
        source_revision=active.source_revision,
        observed_at="2026-09-28T15:00:00Z",
        summary="observer authority gate",
        evidence=(ev,),
        canonical_refs=("preflight://observer",),
        uncertainties=(),
        next_transition_refs=(),
        authority_stop=True,
        authority_boundary=BOUNDARY,
    )
    store.commit(g0.portfolio_id, g0.digest, g1, cp)
    return store, g1


def superseding_evidence():
    return CheckpointEvidence(
        kind="superseding_evidence",
        locator="pilot://no-iam-provider-wake",
        digest=sha256_digest({"pilot": "PASS", "iam_required": False}),
    )


def decision_for(state, **changes):
    data = dict(
        event_id="decision-001",
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        pending_action_ref=PENDING,
        decision="supersede",
        reason="A narrower no-IAM provider wake passed.",
        target_state="rework",
        next_action_ref="action://durable/admit-no-iam-provider-proof",
        observed_at="2026-09-28T16:00:00Z",
        evidence=(superseding_evidence(),),
        canonical_refs=("pilot://no-iam-provider-wake",),
    )
    data.update(changes)
    return HumanGateDecision(**data)


def test_supersede_moves_only_to_rework_and_cold_recovers(tmp_path):
    store, g1 = human_gate_store(tmp_path)
    decision = decision_for(g1)
    result = consume_human_gate_decision(
        store,
        decision,
        provider_actor="Waterfound",
        decision_ref="github://decision/001",
    )
    assert result.state.generation == 2
    assert result.state.active.state == "rework"
    assert result.state.active.next_action_ref == "action://durable/admit-no-iam-provider-proof"
    assert result.state.active.authority_boundary is None
    assert result.state.active.authority_ref is None
    assert result.state.active.blockers == ()
    assert result.state.previous_state_digest == g1.digest
    assert result.checkpoint.state_before == "human_gate"
    assert result.checkpoint.state_after == "rework"
    assert not result.checkpoint.authority_stop
    assert result.checkpoint.authority_boundary is None
    assert result.checkpoint.next_transition_refs == (
        "action://durable/admit-no-iam-provider-proof",
    )
    assert {x.kind for x in result.checkpoint.evidence} == {
        "superseding_evidence",
        "human_gate_decision",
    }
    recovered, checkpoint, report = recover_portfolio_after_restart(store, "terminal")
    assert recovered == result.state
    assert checkpoint == result.checkpoint
    assert report.digest == result.recovery_digest


def test_reject_can_fail_closed_but_cannot_resume_execution(tmp_path):
    store, g1 = human_gate_store(tmp_path)
    decision = decision_for(
        g1,
        decision="reject",
        reason="Waterfound rejects this authority request.",
        target_state="failed",
        next_action_ref="action://none",
        evidence=(
            CheckpointEvidence(
                kind="human_rejection_context",
                locator="decision://reject",
                digest=sha256_digest({"reject": True}),
            ),
        ),
    )
    result = consume_human_gate_decision(
        store,
        decision,
        provider_actor="Waterfound",
        decision_ref="github://decision/reject",
    )
    assert result.state.active.state == "failed"
    assert result.checkpoint.next_transition_refs == ()
    assert not result.checkpoint.authority_stop


@pytest.mark.parametrize("actor", ["github-actions[bot]", "attacker", ""])
def test_only_waterfound_can_decide_human_gate(tmp_path, actor):
    store, g1 = human_gate_store(tmp_path)
    with pytest.raises(HumanGateDecisionError, match="actor is not trusted"):
        consume_human_gate_decision(
            store,
            decision_for(g1),
            provider_actor=actor,
            decision_ref="github://decision/unauthorized",
        )


def test_stale_decision_fails_closed(tmp_path):
    store, g1 = human_gate_store(tmp_path)
    stale = decision_for(g1, expected_generation=2)
    with pytest.raises(HumanGateDecisionError, match="stale"):
        consume_human_gate_decision(
            store,
            stale,
            provider_actor="Waterfound",
            decision_ref="github://decision/stale",
        )


def test_wrong_pending_action_fails_closed(tmp_path):
    store, g1 = human_gate_store(tmp_path)
    wrong = decision_for(g1, pending_action_ref="authority://other")
    with pytest.raises(HumanGateDecisionError, match="pending action"):
        consume_human_gate_decision(
            store,
            wrong,
            provider_actor="Waterfound",
            decision_ref="github://decision/wrong",
        )


@pytest.mark.parametrize("target", ["ready", "running", "verifying", "complete", "human_gate"])
def test_decision_cannot_target_resumed_or_complete_state(tmp_path, target):
    _, g1 = human_gate_store(tmp_path)
    with pytest.raises(HumanGateDecisionError, match="target must be rework or failed"):
        decision_for(g1, target_state=target)


def test_supersede_requires_superseding_evidence(tmp_path):
    _, g1 = human_gate_store(tmp_path)
    with pytest.raises(HumanGateDecisionError, match="requires superseding_evidence"):
        decision_for(
            g1,
            evidence=(
                CheckpointEvidence(
                    kind="other",
                    locator="evidence://other",
                    digest=sha256_digest({"other": True}),
                ),
            ),
        )


def test_replay_after_commit_cannot_apply_second_transition(tmp_path):
    store, g1 = human_gate_store(tmp_path)
    decision = decision_for(g1)
    consume_human_gate_decision(
        store,
        decision,
        provider_actor="Waterfound",
        decision_ref="github://decision/001",
    )
    with pytest.raises(HumanGateDecisionError, match="only from human_gate"):
        consume_human_gate_decision(
            store,
            decision,
            provider_actor="Waterfound",
            decision_ref="github://decision/001",
        )


def test_decision_digest_is_state_and_evidence_bound(tmp_path):
    _, g1 = human_gate_store(tmp_path)
    a = decision_for(g1)
    b = decision_for(
        g1,
        evidence=(
            CheckpointEvidence(
                kind="superseding_evidence",
                locator="pilot://different",
                digest=sha256_digest({"pilot": "different"}),
            ),
        ),
        canonical_refs=("pilot://different",),
    )
    assert a.digest != b.digest
