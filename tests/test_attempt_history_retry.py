import pytest

from general_execution.attempt_history import assess_attempt_history
from general_execution.lifecycle_settlement import (
    prepare_reference_cold_lifecycle,
    resume_reference_completed_physical_settlement,
)
from general_execution.recovery_context import SQLiteRecoveryContextStore
from general_execution.retry_lifecycle import (
    RetryLifecycleError,
    prepare_retry_from_durable_failure,
    settle_active_reference_failure,
    settle_latest_completed_result,
)
from general_execution.session_settlement import SQLiteSessionSettlementStore


def paths(tmp_path, prefix="one"):
    return (
        tmp_path / f"{prefix}-sessions.db",
        tmp_path / f"{prefix}-contexts.db",
        tmp_path / f"{prefix}-capacity.db",
        tmp_path / f"{prefix}-provider.db",
    )


def physical_paths(store_paths):
    session, contexts, capacity, provider = store_paths
    return capacity, provider, contexts


def test_settled_failure_is_reconstructed_from_durable_history(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="failure")
    failure = settle_active_reference_failure(*store_paths)
    assert failure.session_id == preparation.session_id
    assert failure.physical_attempt == 1
    assert failure.transport_status == "timed_out"

    history = assess_attempt_history(*physical_paths(store_paths))
    entries = history.for_session(preparation.session_id)
    assert len(entries) == 1
    assert entries[0].state == "settled_failure"
    assert entries[0].retry_eligible
    assert entries[0].outcome_digest == failure.outcome_digest
    assert entries[0].receipt_digest == failure.physical_receipt_digest


def test_retry_preparation_creates_attempt_two_with_exact_predecessor(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="retry")
    failure = settle_active_reference_failure(*store_paths)
    retry = prepare_retry_from_durable_failure(*store_paths)
    assert retry.session_id == preparation.session_id
    assert retry.prior_physical_attempt == 1
    assert retry.retry_physical_attempt == 2
    assert retry.prior_outcome_digest == failure.outcome_digest
    assert retry.prior_receipt_digest == failure.physical_receipt_digest
    assert not retry.idempotent

    contexts = {
        context.authorization.authorization_id: context
        for context, _ in SQLiteRecoveryContextStore(store_paths[1]).bootstrap_candidates()
    }
    context = contexts[retry.retry_authorization_id]
    assert context.authorization.physical_attempt == 2
    assert context.authorization.previous_receipt_digest == failure.physical_receipt_digest

    history = assess_attempt_history(*physical_paths(store_paths))
    entries = history.for_session(preparation.session_id)
    assert [(entry.physical_attempt, entry.state) for entry in entries] == [
        (1, "settled_failure"),
        (2, "active_provider_running"),
    ]


def test_retry_preparation_replay_is_idempotent_while_retry_active(tmp_path):
    store_paths = paths(tmp_path)
    prepare_reference_cold_lifecycle(*store_paths, suffix="retry-idempotent")
    settle_active_reference_failure(*store_paths)
    first = prepare_retry_from_durable_failure(*store_paths)
    second = prepare_retry_from_durable_failure(*store_paths)
    assert not first.idempotent
    assert second.idempotent
    assert first.retry_authorization_id == second.retry_authorization_id
    assert first.retry_context_digest == second.retry_context_digest
    assert first.provider_job_id == second.provider_job_id


def test_retry_can_complete_and_logical_result_settles_from_multi_context_history(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="retry-success")
    settle_active_reference_failure(*store_paths)
    retry = prepare_retry_from_durable_failure(*store_paths)
    physical_report, result = resume_reference_completed_physical_settlement(*store_paths)
    assert physical_report.session_id == preparation.session_id
    assert result is not None

    history = assess_attempt_history(*physical_paths(store_paths))
    entries = history.for_session(preparation.session_id)
    assert [(entry.physical_attempt, entry.state) for entry in entries] == [
        (1, "settled_failure"),
        (2, "settled_completed"),
    ]
    assert entries[-1].authorization_id == retry.retry_authorization_id

    logical = settle_latest_completed_result(*store_paths)
    assert not logical.idempotent
    assert logical.result_digest == result.digest
    record = SQLiteSessionSettlementStore(store_paths[0]).load(preparation.session_id)
    assert record.current_session.state == "result_submitted"
    assert record.result == result


def test_retry_logical_settlement_replay_is_idempotent(tmp_path):
    store_paths = paths(tmp_path)
    prepare_reference_cold_lifecycle(*store_paths, suffix="retry-logical-ack")
    settle_active_reference_failure(*store_paths)
    prepare_retry_from_durable_failure(*store_paths)
    resume_reference_completed_physical_settlement(*store_paths)
    first = settle_latest_completed_result(*store_paths)
    second = settle_latest_completed_result(*store_paths)
    assert not first.idempotent
    assert second.idempotent
    assert first.result_digest == second.result_digest


def test_two_failures_produce_attempt_three_with_attempt_two_receipt_predecessor(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="attempt-three")
    failure_one = settle_active_reference_failure(*store_paths)
    retry_two = prepare_retry_from_durable_failure(*store_paths)
    failure_two = settle_active_reference_failure(*store_paths)
    assert failure_two.physical_attempt == 2
    assert failure_two.authorization_id == retry_two.retry_authorization_id

    retry_three = prepare_retry_from_durable_failure(*store_paths)
    assert retry_three.prior_physical_attempt == 2
    assert retry_three.retry_physical_attempt == 3
    assert retry_three.prior_outcome_digest == failure_two.outcome_digest
    assert retry_three.prior_receipt_digest == failure_two.physical_receipt_digest

    contexts = {
        context.authorization.authorization_id: context
        for context, _ in SQLiteRecoveryContextStore(store_paths[1]).bootstrap_candidates()
    }
    third = contexts[retry_three.retry_authorization_id]
    assert third.authorization.physical_attempt == 3
    assert third.authorization.previous_receipt_digest == failure_two.physical_receipt_digest

    history = assess_attempt_history(*physical_paths(store_paths)).for_session(preparation.session_id)
    assert [(entry.physical_attempt, entry.state) for entry in history] == [
        (1, "settled_failure"),
        (2, "settled_failure"),
        (3, "active_provider_running"),
    ]


def test_retry_is_rejected_if_logical_session_is_revoked(tmp_path):
    store_paths = paths(tmp_path)
    preparation = prepare_reference_cold_lifecycle(*store_paths, suffix="revoked-retry")
    settle_active_reference_failure(*store_paths)
    context, _ = SQLiteRecoveryContextStore(store_paths[1]).bootstrap_candidates()[0]
    SQLiteSessionSettlementStore(store_paths[0]).revoke(context.session)
    with pytest.raises(RetryLifecycleError):
        prepare_retry_from_durable_failure(*store_paths)
    assert SQLiteSessionSettlementStore(store_paths[0]).load(preparation.session_id).current_session.state == "revoked"


def test_no_retry_after_latest_completed_attempt(tmp_path):
    store_paths = paths(tmp_path)
    prepare_reference_cold_lifecycle(*store_paths, suffix="completed-no-retry")
    resume_reference_completed_physical_settlement(*store_paths)
    with pytest.raises(RetryLifecycleError):
        prepare_retry_from_durable_failure(*store_paths)


def test_attempt_history_is_deterministic_across_fresh_retry_lifecycles(tmp_path):
    a = paths(tmp_path, "a")
    b = paths(tmp_path, "b")
    for store_paths in (a, b):
        prepare_reference_cold_lifecycle(*store_paths, suffix="history-deterministic")
        settle_active_reference_failure(*store_paths)
        prepare_retry_from_durable_failure(*store_paths)
    assert assess_attempt_history(*physical_paths(a)) == assess_attempt_history(*physical_paths(b))
