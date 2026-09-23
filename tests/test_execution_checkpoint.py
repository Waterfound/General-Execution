import json
from dataclasses import replace

import pytest

from general_execution import (
    AdmittedEvidence,
    CheckpointCanonicalRef,
    ExecutionCheckpoint,
    ExecutionCheckpointError,
    PortfolioEntry,
    PortfolioState,
    TransitionPolicy,
    TransitionRequest,
    TransitionRule,
    deserialize_execution_checkpoint,
    evaluate_transition,
    execution_checkpoint_from_dict,
    execution_checkpoint_to_dict,
    serialize_execution_checkpoint,
    verify_execution_checkpoint,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64


def active(**changes):
    values = dict(
        work_id="FAE-BE-04",
        role="active",
        state="running",
        objective="Bind explorer",
        active_gate="PUBLIC_NODE_BINDING",
        next_action_ref="action://deploy",
        source_revision="abc123",
        evidence_required=("execution_report",),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def secondary():
    return PortfolioEntry(
        work_id="FAE-WALLET-UX",
        role="secondary",
        state="ready",
        objective="Wallet UX",
        active_gate="WALLET_TX_DISCOVERABILITY",
        next_action_ref="action://inspect",
        source_revision="def456",
    )


def portfolio(**changes):
    values = dict(
        portfolio_id="fae-mainnet-critical",
        generation=0,
        active=active(),
        secondary=secondary(),
    )
    values.update(changes)
    return PortfolioState(**values)


def evidence(kind="execution_report", digest=D1):
    return AdmittedEvidence(
        kind=kind,
        locator=f"artifact://{kind}",
        content_digest=digest,
    )


def canonical_ref(name="source_revision", digest=D2):
    return CheckpointCanonicalRef(
        name=name,
        locator=f"git://general-execution/{name}",
        content_digest=digest,
    )


def policy():
    return TransitionPolicy(
        policy_id="durable-asp-v1",
        policy_revision="rev-001",
        rules=(
            TransitionRule(
                rule_id="010-running-completed",
                from_role="active",
                from_state="running",
                signal="execution_completed",
                target_role="active",
                target_state="verifying",
                action_ref="action://verify",
                required_evidence=("execution_report",),
            ),
        ),
    )


def decision(state=None):
    state = state or portfolio()
    req = TransitionRequest(
        work_id=state.active.work_id,
        entry_digest=state.active.digest,
        from_role=state.active.role,
        from_state=state.active.state,
        signal="execution_completed",
        admitted_evidence=(evidence(),),
    )
    return evaluate_transition(policy(), req)


def checkpoint(**changes):
    state = portfolio()
    values = dict(
        portfolio_id=state.portfolio_id,
        portfolio_generation=state.generation,
        portfolio_state_digest=state.digest,
        work_id=state.active.work_id,
        entry_digest=state.active.digest,
        entry_role=state.active.role,
        entry_state=state.active.state,
        source_revision=state.active.source_revision,
        observed_signal="execution_completed",
        summary="Deployment fragment completed and is ready for verification.",
        evidence=(evidence(),),
        canonical_refs=(canonical_ref(),),
        uncertainties=("public reachability not yet independently verified",),
        next_transition=decision(state),
    )
    values.update(changes)
    return ExecutionCheckpoint(**values)


def test_checkpoint_round_trip_is_canonical():
    cp = checkpoint()
    encoded = serialize_execution_checkpoint(cp)
    decoded = deserialize_execution_checkpoint(encoded)
    assert decoded == cp
    assert decoded.digest == cp.digest
    assert encoded == serialize_execution_checkpoint(decoded)


def test_checkpoint_binds_exact_portfolio_and_entry():
    state = portfolio()
    cp = checkpoint()
    assert verify_execution_checkpoint(cp, state)


def test_checkpoint_rejects_different_portfolio_generation():
    state = portfolio()
    cp = checkpoint()
    later = replace(
        state,
        generation=1,
        previous_state_digest=state.digest,
    )
    assert not verify_execution_checkpoint(cp, later)


def test_checkpoint_rejects_different_portfolio_digest():
    state = portfolio()
    changed = replace(
        state,
        active=replace(state.active, objective="Changed objective"),
    )
    assert not verify_execution_checkpoint(checkpoint(), changed)


def test_checkpoint_requires_exactly_one_next_transition_or_stop_reason():
    with pytest.raises(ExecutionCheckpointError, match="exactly one"):
        checkpoint(next_transition=None, stop_reason=None)
    with pytest.raises(ExecutionCheckpointError, match="exactly one"):
        checkpoint(stop_reason="stop", next_transition=decision())


def test_checkpoint_can_record_fail_closed_stop_without_transition():
    cp = checkpoint(
        next_transition=None,
        stop_reason="authority_required_before_next_transition",
    )
    assert cp.next_transition is None
    assert cp.stop_reason == "authority_required_before_next_transition"


def test_checkpoint_transition_must_match_work_identity():
    d = replace(decision(), work_id="OTHER")
    with pytest.raises(ExecutionCheckpointError, match="work_id mismatch"):
        checkpoint(next_transition=d)


def test_checkpoint_transition_must_match_entry_digest():
    d = replace(decision(), entry_digest=D3)
    with pytest.raises(ExecutionCheckpointError, match="entry_digest mismatch"):
        checkpoint(next_transition=d)


def test_checkpoint_transition_must_match_role_state_and_signal():
    d = replace(decision(), from_role="secondary")
    with pytest.raises(ExecutionCheckpointError, match="role mismatch"):
        checkpoint(next_transition=d)

    d = replace(decision(), from_state="ready")
    with pytest.raises(ExecutionCheckpointError, match="state mismatch"):
        checkpoint(next_transition=d)

    d = replace(decision(), signal="failure_confirmed")
    with pytest.raises(ExecutionCheckpointError, match="signal mismatch"):
        checkpoint(next_transition=d)


def test_checkpoint_preserves_evidence_used_by_transition():
    d = decision()
    with pytest.raises(ExecutionCheckpointError, match="evidence not preserved"):
        checkpoint(
            evidence=(evidence("other", D3),),
            next_transition=d,
        )


def test_checkpoint_requires_admitted_evidence():
    with pytest.raises(ExecutionCheckpointError, match="requires admitted evidence"):
        checkpoint(evidence=())


def test_checkpoint_requires_canonical_reference():
    with pytest.raises(ExecutionCheckpointError, match="canonical reference"):
        checkpoint(canonical_refs=())


def test_checkpoint_rejects_duplicate_evidence_kinds():
    with pytest.raises(ExecutionCheckpointError, match="evidence kinds must be unique"):
        checkpoint(evidence=(evidence("execution_report", D1), evidence("execution_report", D2)))


def test_checkpoint_rejects_duplicate_canonical_names():
    with pytest.raises(ExecutionCheckpointError, match="reference names must be unique"):
        checkpoint(canonical_refs=(canonical_ref("source", D1), canonical_ref("source", D2)))


def test_checkpoint_rejects_duplicate_uncertainties():
    with pytest.raises(ExecutionCheckpointError, match="must not contain duplicates"):
        checkpoint(uncertainties=("unknown", "unknown"))


def test_checkpoint_rejects_unknown_observed_signal():
    with pytest.raises(ExecutionCheckpointError, match="unsupported checkpoint observed_signal"):
        checkpoint(observed_signal="magic")


def test_checkpoint_rejects_invalid_role_state_combination():
    with pytest.raises(ExecutionCheckpointError, match="secondary role/state"):
        checkpoint(entry_role="secondary", entry_state="running")


def test_checkpoint_unknown_fields_fail_closed():
    data = execution_checkpoint_to_dict(checkpoint())
    data["unexpected"] = True
    with pytest.raises(ExecutionCheckpointError, match="fields mismatch"):
        execution_checkpoint_from_dict(data)


def test_checkpoint_nested_unknown_fields_fail_closed():
    data = execution_checkpoint_to_dict(checkpoint())
    data["canonical_refs"][0]["unexpected"] = True
    with pytest.raises(ExecutionCheckpointError, match="canonical ref fields mismatch"):
        execution_checkpoint_from_dict(data)


def test_checkpoint_malformed_json_fails_closed():
    with pytest.raises(ExecutionCheckpointError, match="not valid JSON"):
        deserialize_execution_checkpoint("{broken")


def test_checkpoint_can_be_reconstructed_without_chat_context():
    original = checkpoint()
    artifact = json.loads(serialize_execution_checkpoint(original))
    restored = execution_checkpoint_from_dict(artifact)
    assert restored.portfolio_id == "fae-mainnet-critical"
    assert restored.work_id == "FAE-BE-04"
    assert restored.next_transition.action_ref == "action://verify"
    assert restored.uncertainties == (
        "public reachability not yet independently verified",
    )
