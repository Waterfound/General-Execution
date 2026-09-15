from dataclasses import replace

import pytest

from general_execution import (
    ReferenceStoreReopenRehearsal,
    SQLiteDurableHeadStore,
    reattachable_reference_runner,
    reattachment_key_from_recovered,
    submit_result,
)
from general_execution.rehearsal import RehearsalError, run_reference_store_reopen_rehearsal
from general_execution.reference_registry import SQLiteReferenceJobRegistry

ZERO = "sha256:" + "0" * 64


def test_timed_out_rehearsal_reopens_stores_and_releases_capacity(tmp_path):
    capacity_path = tmp_path / "capacity.db"
    provider_path = tmp_path / "provider.db"
    rehearsal = run_reference_store_reopen_rehearsal(
        capacity_path,
        provider_path,
        terminal_kind="timed_out",
        suffix="timeout",
    )
    assert rehearsal.report.terminal_kind == "timed_out"
    assert rehearsal.report.context_mode == "caller_retained"
    assert rehearsal.result is None
    assert rehearsal.session.state == "running"
    assert rehearsal.report.session_state_after_reconciliation == "running"
    assert rehearsal.report.initial_head_digest == rehearsal.report.recovered_head_digest
    assert rehearsal.report.running_assessment_digest

    current = SQLiteDurableHeadStore(capacity_path).load_current(reattachable_reference_runner())
    assert current is not None
    assert current.head.digest == rehearsal.report.committed_head_digest
    assert current.state.active_leases == ()


def test_completed_rehearsal_does_not_auto_submit_logical_result(tmp_path):
    rehearsal = run_reference_store_reopen_rehearsal(
        tmp_path / "capacity.db",
        tmp_path / "provider.db",
        terminal_kind="completed",
        suffix="completed",
    )
    assert rehearsal.result is not None
    assert rehearsal.outcome.result == rehearsal.result
    assert rehearsal.session.state == "running"
    assert rehearsal.report.logical_result_digest == rehearsal.result.digest

    submitted = submit_result(rehearsal.session, rehearsal.result)
    assert submitted.state == "result_submitted"
    assert submitted.result_digest == rehearsal.result.digest


def test_provider_registry_is_terminal_after_rehearsal(tmp_path):
    capacity_path = tmp_path / "capacity.db"
    provider_path = tmp_path / "provider.db"
    rehearsal = run_reference_store_reopen_rehearsal(
        capacity_path,
        provider_path,
        terminal_kind="timed_out",
        suffix="provider-terminal",
    )
    runner = reattachable_reference_runner()
    key = reattachment_key_from_recovered(rehearsal.recovered_lease, runner)
    record = SQLiteReferenceJobRegistry(provider_path).lookup(key)
    assert record is not None
    assert record.state == "terminal"
    assert record.job_id == rehearsal.report.provider_job_id


def test_fresh_store_rehearsal_is_deterministic_across_files(tmp_path):
    first = run_reference_store_reopen_rehearsal(
        tmp_path / "a-capacity.db",
        tmp_path / "a-provider.db",
        terminal_kind="timed_out",
        suffix="deterministic",
    )
    second = run_reference_store_reopen_rehearsal(
        tmp_path / "b-capacity.db",
        tmp_path / "b-provider.db",
        terminal_kind="timed_out",
        suffix="deterministic",
    )
    assert first.report == second.report
    assert first.report.digest == second.report.digest
    assert first.outcome.digest == second.outcome.digest


def test_existing_capacity_head_prevents_accidental_reuse(tmp_path):
    capacity_path = tmp_path / "capacity.db"
    provider_path = tmp_path / "provider.db"
    run_reference_store_reopen_rehearsal(
        capacity_path,
        provider_path,
        terminal_kind="timed_out",
        suffix="reuse",
    )
    with pytest.raises(RehearsalError):
        run_reference_store_reopen_rehearsal(
            capacity_path,
            tmp_path / "provider-2.db",
            terminal_kind="timed_out",
            suffix="reuse",
        )


def test_capacity_and_provider_stores_must_be_distinct(tmp_path):
    same = tmp_path / "same.db"
    with pytest.raises(RehearsalError):
        run_reference_store_reopen_rehearsal(same, same)
    assert not same.exists()


def test_invalid_terminal_kind_is_rejected_before_store_mutation(tmp_path):
    with pytest.raises(RehearsalError):
        run_reference_store_reopen_rehearsal(
            tmp_path / "capacity.db",
            tmp_path / "provider.db",
            terminal_kind="unknown",
        )
    assert not (tmp_path / "capacity.db").exists()
    assert not (tmp_path / "provider.db").exists()


def test_rehearsal_object_rejects_report_outcome_substitution(tmp_path):
    rehearsal = run_reference_store_reopen_rehearsal(
        tmp_path / "capacity.db",
        tmp_path / "provider.db",
        terminal_kind="timed_out",
        suffix="report-binding",
    )
    changed_report = replace(rehearsal.report, outcome_digest=ZERO)
    with pytest.raises(ValueError):
        ReferenceStoreReopenRehearsal(
            report=changed_report,
            session=rehearsal.session,
            recovered_lease=rehearsal.recovered_lease,
            outcome=rehearsal.outcome,
            result=rehearsal.result,
            reconciliation_receipt=rehearsal.reconciliation_receipt,
        )
