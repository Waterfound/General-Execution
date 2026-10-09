import os

import pytest

from general_execution.state_boundary import (
    ExecutionSemanticReceipt,
    FilePrivateStateBoundary,
    StateBoundaryError,
    StateTransportBinding,
    compare_semantic_preservation,
    public_state_receipt,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def semantic(**overrides):
    values = dict(
        operation="transition",
        status="committed",
        pre_generation=0,
        post_generation=1,
        pre_state_digest=DIGEST_A,
        post_state_digest=DIGEST_B,
        checkpoint_digest=None,
        human_required=False,
        requested_action_ref=None,
    )
    values.update(overrides)
    return ExecutionSemanticReceipt(**values)


def binding(ref, *, visibility, execution_ref, coupled=False):
    return StateTransportBinding(
        state_ref=ref,
        storage_visibility=visibility,
        execution_resource_ref=execution_ref,
        execution_requires_storage_provider=coupled,
    )


def test_private_boundary_persists_and_restores_without_public_path(tmp_path):
    boundary = FilePrivateStateBoundary(tmp_path / "private")
    receipt = boundary.persist("s_0000000000000001", b"durable-private-state")
    assert boundary.restore(receipt) == b"durable-private-state"
    public = public_state_receipt(receipt)
    assert public["storage_visibility"] == "private"
    assert "path" not in public
    assert "provider" not in public
    assert "content" not in public


def test_private_boundary_detects_tampering(tmp_path):
    root = tmp_path / "private"
    boundary = FilePrivateStateBoundary(root)
    receipt = boundary.persist("s_0000000000000001", b"original")
    (root / "s_0000000000000001.bin").write_bytes(b"tampered")
    with pytest.raises(StateBoundaryError, match="digest mismatch"):
        boundary.restore(receipt)


def test_storage_visibility_does_not_bind_execution_resource():
    baseline = semantic()
    candidate = semantic()
    result = compare_semantic_preservation(
        baseline,
        candidate,
        baseline_binding=binding(
            "s_0000000000000001",
            visibility="public",
            execution_ref="executor://baseline",
        ),
        candidate_binding=binding(
            "s_0000000000000002",
            visibility="private",
            execution_ref="executor://non-actions-local",
        ),
        evidence_predicate_preserved=True,
    )
    assert result.equivalent
    assert result.storage_execution_decoupled


def test_candidate_rejected_if_private_storage_forces_same_provider_execution():
    result = compare_semantic_preservation(
        semantic(),
        semantic(),
        baseline_binding=binding(
            "s_0000000000000001",
            visibility="public",
            execution_ref="executor://baseline",
        ),
        candidate_binding=binding(
            "s_0000000000000002",
            visibility="private",
            execution_ref="executor://private-storage-provider",
            coupled=True,
        ),
        evidence_predicate_preserved=True,
    )
    assert not result.equivalent
    assert "storage_compute_coupled" in result.reasons


def test_authority_or_evidence_regression_fails_closed():
    authority_change = compare_semantic_preservation(
        semantic(),
        semantic(human_required=True, requested_action_ref="authority://new"),
        baseline_binding=binding(
            "s_0000000000000001",
            visibility="public",
            execution_ref="executor://baseline",
        ),
        candidate_binding=binding(
            "s_0000000000000002",
            visibility="private",
            execution_ref="executor://local",
        ),
        evidence_predicate_preserved=True,
    )
    assert not authority_change.equivalent
    assert "authority_semantics_mismatch" in authority_change.reasons

    evidence_change = compare_semantic_preservation(
        semantic(),
        semantic(),
        baseline_binding=binding(
            "s_0000000000000001",
            visibility="public",
            execution_ref="executor://baseline",
        ),
        candidate_binding=binding(
            "s_0000000000000002",
            visibility="private",
            execution_ref="executor://local",
        ),
        evidence_predicate_preserved=False,
    )
    assert not evidence_change.equivalent
    assert "evidence_predicate_weakened" in evidence_change.reasons


def test_opaque_state_reference_required():
    with pytest.raises(StateBoundaryError, match="opaque"):
        binding(
            "fae-mainnet-readiness",
            visibility="private",
            execution_ref="executor://local",
        )
