import sqlite3

import pytest

from general_execution.lifecycle_settlement import (
    LifecycleSettlementError,
    LifecycleSettlementIntegrityError,
    assess_reference_logical_lifecycle,
    prepare_reference_cold_lifecycle,
    resume_reference_completed_physical_settlement,
    settle_reference_reconciled_result,
)
from general_execution.recovery_context import SQLiteRecoveryContextStore
from general_execution.session_settlement import (
    SessionSettlementConflict,
    SessionSettlementIntegrityError,
    SQLiteSessionSettlementStore,
)

ZERO = "sha256:" + "0" * 64


def paths(tmp_path, prefix="one"):
    return (
        tmp_path / f"{prefix}-sessions.db",
        tmp_path / f"{prefix}-contexts.db",
        tmp_path / f"{prefix}-capacity.db",
        tmp_path / f"{prefix}-provider.db",
    )


def test_prepare_makes_running_session_durable_before_cold_resume(tmp_path):
    store_paths = paths(tmp_path)
    receipt = prepare_reference_cold_lifecycle(*store_paths, suffix="prepare")
    record = SQLiteSessionSettlementStore(store_paths[0]).load(receipt.session_id)
    assert record is not None
    assert record.current_session.state == "running"
    assert record.digest == receipt.running_session_record_digest
    assert receipt.context_id
    assert receipt.provider_job_id


def test_physical_reconciliation_does_not_logically_submit_result(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="physical")
    report, result = resume_reference_completed_physical_settlement(*store_paths)
    assert report.session_id == preparation.session_id
    assert report.result_digest == result.digest
    assert report.durable_session_state == "running"

    record = SQLiteSessionSettlementStore(store_paths[0]).load(preparation.session_id)
    assert record is not None
    assert record.current_session.state == "running"
    assert record.result is None
    assessment = assess_reference_logical_lifecycle(*store_paths)
    assert assessment.state == "physical_settled_session_running"
    assert assessment.result_digest is None


def test_explicit_post_reconciliation_result_settlement_is_durable(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="settle")
    _, result = resume_reference_completed_physical_settlement(*store_paths)
    receipt = settle_reference_reconciled_result(*store_paths)
    assert not receipt.idempotent
    assert receipt.result_digest == result.digest

    record = SQLiteSessionSettlementStore(store_paths[0]).load(preparation.session_id)
    assert record is not None
    assert record.current_session.state == "result_submitted"
    assert record.result == result
    assessment = assess_reference_logical_lifecycle(*store_paths)
    assert assessment.state == "logical_result_submitted"
    assert assessment.result_digest == result.digest


def test_lost_ack_logical_settlement_replay_is_idempotent(tmp_path):
    store_paths = paths(tmp_path)
    prepare_reference_cold_lifecycle(*store_paths, suffix="lost-ack")
    resume_reference_completed_physical_settlement(*store_paths)
    first = settle_reference_reconciled_result(*store_paths)
    second = settle_reference_reconciled_result(*store_paths)
    assert not first.idempotent
    assert second.idempotent
    assert first.result_digest == second.result_digest
    assert (
        first.session_settlement_receipt.committed_record_digest
        == second.session_settlement_receipt.committed_record_digest
    )


def test_settlement_before_physical_reconciliation_is_rejected(tmp_path):
    store_paths = paths(tmp_path)
    prepare_reference_cold_lifecycle(*store_paths, suffix="too-early")
    with pytest.raises(LifecycleSettlementError):
        settle_reference_reconciled_result(*store_paths)
    assessment = assess_reference_logical_lifecycle(*store_paths)
    assert assessment.state == "physical_pending_session_running"


def test_missing_durable_session_record_blocks_physical_resume(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="missing-session")
    with sqlite3.connect(store_paths[0]) as connection:
        connection.execute(
            "DELETE FROM ge_session_settlements WHERE session_id = ?",
            (preparation.session_id,),
        )
    with pytest.raises(LifecycleSettlementIntegrityError):
        resume_reference_completed_physical_settlement(*store_paths)


def test_revoked_session_cannot_accept_recovered_result(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="revoked")
    _, _ = resume_reference_completed_physical_settlement(*store_paths)
    context, _ = SQLiteRecoveryContextStore(store_paths[1]).bootstrap_candidates()[0]
    store = SQLiteSessionSettlementStore(store_paths[0])
    store.revoke(context.session)
    with pytest.raises(SessionSettlementConflict):
        settle_reference_reconciled_result(*store_paths)
    record = store.load(preparation.session_id)
    assert record.current_session.state == "revoked"
    assert assess_reference_logical_lifecycle(*store_paths).state == "logical_revoked"


def test_logical_settlement_row_corruption_is_detected_after_success(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="corrupt")
    resume_reference_completed_physical_settlement(*store_paths)
    settle_reference_reconciled_result(*store_paths)
    with sqlite3.connect(store_paths[0]) as connection:
        connection.execute(
            "UPDATE ge_session_settlements SET record_digest = ? WHERE session_id = ?",
            (ZERO, preparation.session_id),
        )
    with pytest.raises(SessionSettlementIntegrityError):
        assess_reference_logical_lifecycle(*store_paths)


def test_four_lifecycle_stores_must_be_distinct(tmp_path):
    same = tmp_path / "same.db"
    with pytest.raises(LifecycleSettlementError):
        prepare_reference_cold_lifecycle(
            same,
            tmp_path / "contexts.db",
            tmp_path / "capacity.db",
            same,
        )
    assert not same.exists()


def test_full_lifecycle_is_deterministic_across_fresh_paths(tmp_path):
    a = paths(tmp_path, "a")
    b = paths(tmp_path, "b")
    prep_a = prepare_reference_cold_lifecycle(*a, suffix="deterministic")
    prep_b = prepare_reference_cold_lifecycle(*b, suffix="deterministic")
    assert prep_a == prep_b

    physical_a, result_a = resume_reference_completed_physical_settlement(*a)
    physical_b, result_b = resume_reference_completed_physical_settlement(*b)
    assert physical_a == physical_b
    assert result_a == result_b

    logical_a = settle_reference_reconciled_result(*a)
    logical_b = settle_reference_reconciled_result(*b)
    assert logical_a == logical_b
    assert assess_reference_logical_lifecycle(*a) == assess_reference_logical_lifecycle(*b)
