import sqlite3

import pytest

from general_execution.cutpoint_matrix import (
    CutPointMatrixIntegrityError,
    assess_reference_cutpoint,
    prepare_reference_cutpoint,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.recovery_context import SQLiteRecoveryContextStore
from general_execution.reference_bridge import register_reference_invocation
from general_execution.reference_registry import (
    ReferenceRegistryIntegrityError,
    SQLiteReferenceJobRegistry,
)


EXPECTED = {
    "context_persisted": "orphan_context",
    "capacity_committed": "active_provider_unknown",
    "provider_registered": "active_provider_running",
    "terminal_persisted": "terminal_pending_reconciliation",
    "reconciliation_committed": "settled_terminal_reconciliation",
}


def paths(tmp_path, suffix):
    return (
        tmp_path / f"{suffix}-capacity.db",
        tmp_path / f"{suffix}-provider.db",
        tmp_path / f"{suffix}-contexts.db",
    )


@pytest.mark.parametrize("cutpoint", tuple(EXPECTED))
def test_each_cutpoint_reconstructs_exact_safe_state(tmp_path, cutpoint):
    store_paths = paths(tmp_path, cutpoint)
    receipt = prepare_reference_cutpoint(
        *store_paths,
        cutpoint=cutpoint,
        terminal_kind="timed_out",
        suffix=cutpoint,
    )
    assessment = assess_reference_cutpoint(*store_paths)
    assert assessment.state == EXPECTED[cutpoint]
    assert assessment.context_id == receipt.context_id
    assert assessment.context_digest == receipt.context_digest
    assert assessment.authorization_id == receipt.authorization_id
    assert assessment.provider_key == receipt.provider_key


def test_context_only_cutpoint_is_safe_orphan(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "orphan")
    prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="context_persisted",
        suffix="orphan",
    )
    assessment = assess_reference_cutpoint(capacity, provider, contexts)
    assert assessment.state == "orphan_context"
    assert assessment.current_head_digest is None
    assert assessment.provider_state == "absent"
    assert SQLiteDurableHeadStore(capacity).load_current(
        SQLiteRecoveryContextStore(contexts).bootstrap_candidates()[0][1]
    ) is None


def test_capacity_commit_without_provider_stays_unknown_and_occupied(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "unknown")
    prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="capacity_committed",
        suffix="unknown",
    )
    assessment = assess_reference_cutpoint(capacity, provider, contexts)
    assert assessment.state == "active_provider_unknown"
    assert assessment.provider_state == "not_found"
    context, runner = SQLiteRecoveryContextStore(contexts).bootstrap_candidates()[0]
    current = SQLiteDurableHeadStore(capacity).load_current(runner)
    assert current is not None
    assert len(current.state.active_leases) == 1
    assert SQLiteReferenceJobRegistry(provider).lookup(
        __import__("general_execution").reattachment_key_from_authorization(
            context.authorization, runner
        )
    ) is None


def test_terminal_persisted_is_recoverable_without_capacity_release(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "terminal")
    receipt = prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="terminal_persisted",
        terminal_kind="completed",
        suffix="terminal",
    )
    assessment = assess_reference_cutpoint(capacity, provider, contexts)
    assert assessment.state == "terminal_pending_reconciliation"
    assert assessment.provider_state == "terminal"
    assert assessment.outcome_digest is not None
    assert assessment.release_digest is None
    assert assessment.current_head_digest == receipt.anchor_head_digest


def test_reconciliation_commit_is_self_identifying_after_lost_ack(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "lost-ack")
    receipt = prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="reconciliation_committed",
        terminal_kind="timed_out",
        suffix="lost-ack",
    )
    # Simulate losing every in-memory reconciliation object and retaining only stores.
    assessment = assess_reference_cutpoint(capacity, provider, contexts)
    assert assessment.state == "settled_terminal_reconciliation"
    assert assessment.provider_state == "terminal"
    assert assessment.outcome_digest is not None
    assert assessment.release_digest is not None
    assert assessment.current_head_digest == receipt.final_head_digest

    context, runner = SQLiteRecoveryContextStore(contexts).bootstrap_candidates()[0]
    current = SQLiteDurableHeadStore(capacity).load_current(runner)
    assert current is not None
    assert current.state.active_leases == ()
    assert any(
        release.lease_id == context.recovered_lease_id
        and release.outcome_digest == assessment.outcome_digest
        for release in current.state.releases
    )


def test_provider_identity_without_capacity_head_fails_closed(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "bad-order")
    prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="context_persisted",
        suffix="bad-order",
    )
    context, runner = SQLiteRecoveryContextStore(contexts).bootstrap_candidates()[0]
    register_reference_invocation(
        SQLiteReferenceJobRegistry(provider), context.authorization, runner
    )
    with pytest.raises(CutPointMatrixIntegrityError):
        assess_reference_cutpoint(capacity, provider, contexts)


def test_terminal_payload_corruption_is_rejected_even_after_reconciliation(tmp_path):
    capacity, provider, contexts = paths(tmp_path, "corrupt-terminal")
    prepare_reference_cutpoint(
        capacity,
        provider,
        contexts,
        cutpoint="reconciliation_committed",
        terminal_kind="timed_out",
        suffix="corrupt-terminal",
    )
    with sqlite3.connect(provider) as connection:
        connection.execute(
            "UPDATE ge_reference_jobs SET terminal_payload_digest = ? WHERE state = 'terminal'",
            ("sha256:" + "0" * 64,),
        )
    with pytest.raises(ReferenceRegistryIntegrityError):
        assess_reference_cutpoint(capacity, provider, contexts)


@pytest.mark.parametrize("cutpoint", tuple(EXPECTED))
def test_cutpoint_assessment_is_deterministic_across_fresh_files(tmp_path, cutpoint):
    a = paths(tmp_path, f"a-{cutpoint}")
    b = paths(tmp_path, f"b-{cutpoint}")
    prepare_reference_cutpoint(*a, cutpoint=cutpoint, suffix=f"det-{cutpoint}")
    prepare_reference_cutpoint(*b, cutpoint=cutpoint, suffix=f"det-{cutpoint}")
    assert assess_reference_cutpoint(*a) == assess_reference_cutpoint(*b)
