import os

from general_execution.process_harness import run_process_separated_cold_recovery


def test_prepare_and_resume_use_separate_python_workers(tmp_path):
    report = run_process_separated_cold_recovery(
        tmp_path / "process-recovery",
        terminal_kind="timed_out",
        suffix="process-boundary",
    )
    assert report.prepare.process_token != report.resume.process_token
    assert report.prepare.pid != os.getpid()
    assert report.resume.pid != os.getpid()
    assert report.prepare.ppid == os.getpid()
    assert report.resume.ppid == os.getpid()
    assert report.resume.payload["report"]["context_mode"] == "cold_reconstructed"


def test_resume_process_reconstructs_same_context_persisted_by_prepare(tmp_path):
    report = run_process_separated_cold_recovery(
        tmp_path / "context-binding",
        terminal_kind="timed_out",
        suffix="context-binding",
    )
    assert report.prepare.payload["context_digest"] == report.context_digest
    assert report.resume.payload["context_digest"] == report.context_digest
    assert report.prepare.payload["authorization_id"] == report.resume.payload["report"]["authorization_id"]


def test_process_separated_completion_keeps_logical_session_unsubmitted(tmp_path):
    report = run_process_separated_cold_recovery(
        tmp_path / "completed",
        terminal_kind="completed",
        suffix="completed",
    )
    assert report.result_digest is not None
    assert report.resume.payload["reconstructed_session_state"] == "running"
    assert report.resume.payload["report"]["logical_result_digest"] == report.result_digest


def test_process_separated_timeout_has_no_logical_result(tmp_path):
    report = run_process_separated_cold_recovery(
        tmp_path / "timeout",
        terminal_kind="timed_out",
        suffix="timeout",
    )
    assert report.result_digest is None
    assert report.resume.payload["report"]["logical_result_digest"] is None
    assert report.resume.payload["reconstructed_session_state"] == "running"


def test_protocol_report_is_deterministic_even_when_process_evidence_is_not(tmp_path):
    first = run_process_separated_cold_recovery(
        tmp_path / "first",
        terminal_kind="timed_out",
        suffix="deterministic-protocol",
    )
    second = run_process_separated_cold_recovery(
        tmp_path / "second",
        terminal_kind="timed_out",
        suffix="deterministic-protocol",
    )
    assert first.cold_report_digest == second.cold_report_digest
    assert first.context_digest == second.context_digest
    assert first.outcome_digest == second.outcome_digest
    assert first.prepare.process_token != second.prepare.process_token
    assert first.resume.process_token != second.resume.process_token
