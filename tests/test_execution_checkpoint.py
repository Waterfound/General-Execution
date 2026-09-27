import json
from dataclasses import replace

import pytest

from general_execution import (
    CheckpointEvidence,
    ExecutionCheckpoint,
    ExecutionCheckpointError,
    checkpoint_from_dict,
    checkpoint_to_dict,
    deserialize_checkpoint,
    serialize_checkpoint,
)

D = "sha256:" + "b" * 64


def evidence(kind="test", locator="artifact://tests"):
    return CheckpointEvidence(kind=kind, locator=locator, digest=D)


def checkpoint(**changes):
    values = dict(
        portfolio_id="fae-mainnet-critical",
        portfolio_generation=3,
        portfolio_state_digest=D,
        work_id="FAE-BE-04",
        role="active",
        state_before="running",
        state_after="verifying",
        action_ref="action://deploy-prebind",
        source_revision="abc123",
        observed_at="2026-09-23T12:30:00-03:00",
        summary="Deployment fragment completed and is ready for independent verification.",
        evidence=(evidence(),),
        canonical_refs=("commit:abc123",),
        uncertainties=("public reachability not yet independently verified",),
        next_transition_refs=("transition://verify-deployment",),
    )
    values.update(changes)
    return ExecutionCheckpoint(**values)


def test_checkpoint_identity_is_deterministic():
    a = checkpoint()
    b = checkpoint()
    assert a.digest == b.digest
    assert a.checkpoint_id == b.checkpoint_id


def test_checkpoint_round_trip_is_canonical():
    original = checkpoint()
    encoded = serialize_checkpoint(original)
    decoded = deserialize_checkpoint(encoded)
    assert decoded == original
    assert decoded.digest == original.digest
    assert serialize_checkpoint(decoded) == encoded


def test_checkpoint_dict_round_trip():
    original = checkpoint()
    decoded = checkpoint_from_dict(json.loads(json.dumps(checkpoint_to_dict(original))))
    assert decoded == original


def test_checkpoint_requires_evidence():
    with pytest.raises(ExecutionCheckpointError, match="requires admitted evidence"):
        checkpoint(evidence=())


def test_checkpoint_requires_canonical_ref():
    with pytest.raises(ExecutionCheckpointError, match="at least one canonical_ref"):
        checkpoint(canonical_refs=())


def test_duplicate_evidence_is_rejected():
    item = evidence()
    with pytest.raises(ExecutionCheckpointError, match="must not contain duplicates"):
        checkpoint(evidence=(item, item))


def test_duplicate_uncertainty_is_rejected():
    with pytest.raises(ExecutionCheckpointError, match="must not contain duplicates"):
        checkpoint(uncertainties=("same", "same"))


def test_nonterminal_checkpoint_requires_next_transition():
    with pytest.raises(ExecutionCheckpointError, match="nonterminal checkpoint requires"):
        checkpoint(next_transition_refs=())


def test_complete_checkpoint_may_have_no_next_transition():
    item = checkpoint(state_before="verifying", state_after="complete", next_transition_refs=())
    assert item.state_after == "complete"


def test_failed_checkpoint_may_have_no_next_transition():
    item = checkpoint(state_after="failed", next_transition_refs=())
    assert item.state_after == "failed"


def test_authority_stop_requires_boundary():
    with pytest.raises(ExecutionCheckpointError, match="requires authority_boundary"):
        checkpoint(
            state_after="human_gate",
            authority_stop=True,
            authority_boundary=None,
            next_transition_refs=(),
        )


def test_authority_stop_requires_human_gate():
    with pytest.raises(ExecutionCheckpointError, match="state_after=human_gate"):
        checkpoint(
            authority_stop=True,
            authority_boundary="spend ceiling exceeded",
            next_transition_refs=(),
        )


def test_authority_stop_cannot_claim_automatic_next_transition():
    with pytest.raises(ExecutionCheckpointError, match="cannot declare automatic"):
        checkpoint(
            state_after="human_gate",
            authority_stop=True,
            authority_boundary="release approval",
        )


def test_authority_boundary_invalid_without_stop():
    with pytest.raises(ExecutionCheckpointError, match="valid only for authority_stop"):
        checkpoint(authority_boundary="release approval")


def test_valid_authority_stop_records_no_automatic_transition():
    item = checkpoint(
        state_after="human_gate",
        authority_stop=True,
        authority_boundary="spend above authorized ceiling",
        next_transition_refs=(),
    )
    assert item.authority_stop
    assert item.next_transition_refs == ()


def test_passive_checkpoint_cannot_claim_non_passive_state():
    with pytest.raises(ExecutionCheckpointError, match="passive checkpoint"):
        checkpoint(role="passive", state_before="passive", state_after="ready")


def test_passive_checkpoint_can_remain_passive():
    item = checkpoint(
        role="passive",
        state_before="passive",
        state_after="passive",
        next_transition_refs=("transition://await-wake",),
    )
    assert item.role == "passive"


def test_unknown_checkpoint_field_fails_closed():
    data = checkpoint_to_dict(checkpoint())
    data["unexpected"] = True
    with pytest.raises(ExecutionCheckpointError, match="fields mismatch"):
        checkpoint_from_dict(data)


def test_nested_evidence_unknown_field_fails_closed():
    data = checkpoint_to_dict(checkpoint())
    data["evidence"][0]["unexpected"] = True
    with pytest.raises(ExecutionCheckpointError, match="checkpoint evidence fields mismatch"):
        checkpoint_from_dict(data)


def test_schema_tamper_fails_closed():
    data = checkpoint_to_dict(checkpoint())
    data["schema_version"] = "ge.execution-checkpoint.v999"
    with pytest.raises(ExecutionCheckpointError, match="unsupported execution checkpoint schema"):
        checkpoint_from_dict(data)


def test_bad_portfolio_digest_fails_closed():
    with pytest.raises(ExecutionCheckpointError, match="portfolio_state_digest"):
        checkpoint(portfolio_state_digest="bad")


def test_bad_evidence_digest_fails_closed():
    with pytest.raises(ExecutionCheckpointError, match="evidence.digest"):
        evidence(locator="artifact://bad").__class__(
            kind="test",
            locator="artifact://bad",
            digest="not-a-digest",
        )


def test_malformed_json_fails_closed():
    with pytest.raises(ExecutionCheckpointError, match="not valid JSON"):
        deserialize_checkpoint("{broken")


def test_boolean_generation_is_rejected():
    with pytest.raises(ExecutionCheckpointError, match="must be an integer"):
        checkpoint(portfolio_generation=True)
