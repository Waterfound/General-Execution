import pytest

from general_execution import SQLiteDurableHeadStore, submit_result
from general_execution.cold_rehearsal import (
    COLD_CONTEXT_MODE,
    ColdRehearsalError,
    prepare_reference_cold_restart,
    resume_reference_cold_restart,
)
from general_execution.reference_bridge import reattachable_reference_runner


def paths(tmp_path, prefix="one"):
    return (
        tmp_path / f"{prefix}-capacity.db",
        tmp_path / f"{prefix}-context.db",
        tmp_path / f"{prefix}-provider.db",
    )


def test_timed_out_resume_reconstructs_context_from_stores_only(tmp_path):
    capacity, context, provider = paths(tmp_path, "timeout")
    preparation = prepare_reference_cold_restart(
        capacity, context, provider, suffix="timeout"
    )
    expected_context_digest = preparation.context_digest
    del preparation

    rehearsal = resume_reference_cold_restart(
        capacity, context, provider, terminal_kind="timed_out"
    )
    assert rehearsal.report.context_mode == COLD_CONTEXT_MODE
    assert rehearsal.report.context_digest == expected_context_digest
    assert rehearsal.result is None
    assert rehearsal.reconstructed_session == rehearsal.context.session
    assert rehearsal.reconstructed_session.state == "running"

    current = SQLiteDurableHeadStore(capacity).load_current(reattachable_reference_runner())
    assert current is not None
    assert current.state.active_leases == ()
    assert current.head.digest == rehearsal.report.committed_head_digest


def test_completed_resume_keeps_logical_submission_separate(tmp_path):
    capacity, context, provider = paths(tmp_path, "completed")
    prepare_reference_cold_restart(capacity, context, provider, suffix="completed")
    rehearsal = resume_reference_cold_restart(
        capacity, context, provider, terminal_kind="completed"
    )
    assert rehearsal.result is not None
    assert rehearsal.outcome.result == rehearsal.result
    assert rehearsal.reconstructed_session.state == "running"
    assert rehearsal.report.logical_result_digest == rehearsal.result.digest

    submitted = submit_result(rehearsal.reconstructed_session, rehearsal.result)
    assert submitted.state == "result_submitted"
    assert submitted.result_digest == rehearsal.result.digest


def test_preparation_receipt_binds_all_three_durable_layers(tmp_path):
    capacity, context, provider = paths(tmp_path, "receipt")
    receipt = prepare_reference_cold_restart(
        capacity, context, provider, suffix="receipt"
    )
    assert receipt.context_id
    assert receipt.context_digest.startswith("sha256:")
    assert receipt.context_commit_digest.startswith("sha256:")
    assert receipt.capacity_commit_digest.startswith("sha256:")
    assert receipt.provider_registration_digest.startswith("sha256:")
    assert receipt.provider_key
    assert receipt.provider_job_id


def test_cold_rehearsal_is_deterministic_across_fresh_stores(tmp_path):
    a_capacity, a_context, a_provider = paths(tmp_path, "a")
    b_capacity, b_context, b_provider = paths(tmp_path, "b")
    prepare_reference_cold_restart(
        a_capacity, a_context, a_provider, suffix="deterministic"
    )
    prepare_reference_cold_restart(
        b_capacity, b_context, b_provider, suffix="deterministic"
    )
    first = resume_reference_cold_restart(
        a_capacity, a_context, a_provider, terminal_kind="timed_out"
    )
    second = resume_reference_cold_restart(
        b_capacity, b_context, b_provider, terminal_kind="timed_out"
    )
    assert first.report == second.report
    assert first.report.digest == second.report.digest
    assert first.context == second.context
    assert first.outcome.digest == second.outcome.digest


def test_prepare_requires_three_distinct_store_files(tmp_path):
    same = tmp_path / "same.db"
    with pytest.raises(ColdRehearsalError):
        prepare_reference_cold_restart(same, same, tmp_path / "provider.db")
    assert not same.exists()


def test_resume_rejects_invalid_terminal_kind_before_provider_mutation(tmp_path):
    capacity, context, provider = paths(tmp_path, "invalid")
    prepare_reference_cold_restart(capacity, context, provider, suffix="invalid")
    with pytest.raises(ColdRehearsalError):
        resume_reference_cold_restart(
            capacity, context, provider, terminal_kind="unknown"
        )


def test_second_resume_has_no_active_recoverable_context(tmp_path):
    capacity, context, provider = paths(tmp_path, "second")
    prepare_reference_cold_restart(capacity, context, provider, suffix="second")
    resume_reference_cold_restart(
        capacity, context, provider, terminal_kind="timed_out"
    )
    with pytest.raises(ColdRehearsalError):
        resume_reference_cold_restart(
            capacity, context, provider, terminal_kind="timed_out"
        )
