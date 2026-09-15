from dataclasses import replace

import pytest

from general_execution import submit_result
from general_execution.cold_bootstrap import bootstrap_active_recovery_contexts
from general_execution.cold_rehearsal import (
    ColdRehearsalError,
    ReferenceColdRestartRehearsal,
    prepare_reference_cold_restart,
    resume_reference_cold_restart,
    run_reference_cold_restart_rehearsal,
)
from general_execution.persistence import SQLiteDurableHeadStore
from general_execution.recovery_context import RecoveryContextIntegrityError, SQLiteRecoveryContextStore
from general_execution.reference_registry import SQLiteReferenceJobRegistry

ZERO = "sha256:" + "0" * 64


def paths(tmp_path, prefix="one"):
    return (
        tmp_path / f"{prefix}-capacity.db",
        tmp_path / f"{prefix}-provider.db",
        tmp_path / f"{prefix}-contexts.db",
    )


def test_prepare_then_resume_uses_only_durable_stores(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    preparation = prepare_reference_cold_restart(
        capacity, provider, contexts, suffix="stores-only"
    )
    assert preparation.context_id
    assert preparation.provider_job_id

    # The resume API receives no live Spec, Registry, Plan, Session, runner, or authorization.
    del preparation
    rehearsal = resume_reference_cold_restart(
        capacity, provider, contexts, terminal_kind="timed_out"
    )
    assert rehearsal.report.context_mode == "cold_reconstructed"
    assert rehearsal.report.terminal_kind == "timed_out"
    assert rehearsal.result is None
    assert rehearsal.binding.context.session.state == "running"
    assert rehearsal.binding.current_snapshot.state.active_leases

    current = SQLiteDurableHeadStore(capacity).load_current(rehearsal.binding.runner)
    assert current is not None
    assert current.head.digest == rehearsal.report.committed_head_digest
    assert current.state.active_leases == ()


def test_completed_cold_restart_keeps_logical_submission_separate(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    prepare_reference_cold_restart(capacity, provider, contexts, suffix="completed")
    rehearsal = resume_reference_cold_restart(
        capacity, provider, contexts, terminal_kind="completed"
    )
    assert rehearsal.result is not None
    assert rehearsal.outcome.result == rehearsal.result
    assert rehearsal.binding.context.session.state == "running"
    assert rehearsal.report.logical_result_digest == rehearsal.result.digest

    submitted = submit_result(rehearsal.binding.context.session, rehearsal.result)
    assert submitted.state == "result_submitted"
    assert submitted.result_digest == rehearsal.result.digest


def test_cold_bootstrap_reconstructs_provider_identity_before_terminal(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    preparation = prepare_reference_cold_restart(
        capacity, provider, contexts, suffix="identity"
    )
    bindings = bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(contexts),
        SQLiteDurableHeadStore(capacity),
    )
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.context.context_id == preparation.context_id
    record = SQLiteReferenceJobRegistry(provider).lookup(
        __import__("general_execution").reattachment_key_from_authorization(
            binding.context.authorization, binding.runner
        )
    )
    assert record is not None
    assert record.state == "running"
    assert record.job_id == preparation.provider_job_id


def test_full_cold_rehearsal_is_deterministic_across_fresh_files(tmp_path):
    a = paths(tmp_path, "a")
    b = paths(tmp_path, "b")
    prep_a, run_a = run_reference_cold_restart_rehearsal(
        *a, terminal_kind="timed_out", suffix="deterministic"
    )
    prep_b, run_b = run_reference_cold_restart_rehearsal(
        *b, terminal_kind="timed_out", suffix="deterministic"
    )
    assert prep_a == prep_b
    assert prep_a.digest == prep_b.digest
    assert run_a.report == run_b.report
    assert run_a.report.digest == run_b.report.digest
    assert run_a.outcome.digest == run_b.outcome.digest


def test_context_metadata_tamper_blocks_cold_resume(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    prepare_reference_cold_restart(capacity, provider, contexts, suffix="tamper")

    import sqlite3

    with sqlite3.connect(contexts) as connection:
        connection.execute(
            "UPDATE ge_recovery_contexts SET context_digest = ?",
            (ZERO,),
        )
    with pytest.raises(RecoveryContextIntegrityError):
        resume_reference_cold_restart(capacity, provider, contexts)


def test_three_durable_stores_must_be_distinct(tmp_path):
    same = tmp_path / "same.db"
    with pytest.raises(ColdRehearsalError):
        prepare_reference_cold_restart(same, same, tmp_path / "contexts.db")
    assert not same.exists()


def test_invalid_resume_mode_does_not_terminalize_provider(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    prepare_reference_cold_restart(capacity, provider, contexts, suffix="invalid-mode")
    with pytest.raises(ColdRehearsalError):
        resume_reference_cold_restart(
            capacity, provider, contexts, terminal_kind="unknown"
        )

    binding = bootstrap_active_recovery_contexts(
        SQLiteRecoveryContextStore(contexts),
        SQLiteDurableHeadStore(capacity),
    )[0]
    key = __import__("general_execution").reattachment_key_from_authorization(
        binding.context.authorization, binding.runner
    )
    assert SQLiteReferenceJobRegistry(provider).lookup(key).state == "running"


def test_cold_rehearsal_object_rejects_report_outcome_substitution(tmp_path):
    capacity, provider, contexts = paths(tmp_path)
    _, rehearsal = run_reference_cold_restart_rehearsal(
        capacity, provider, contexts, terminal_kind="timed_out", suffix="binding"
    )
    changed_report = replace(rehearsal.report, outcome_digest=ZERO)
    with pytest.raises(ValueError):
        ReferenceColdRestartRehearsal(
            report=changed_report,
            binding=rehearsal.binding,
            outcome=rehearsal.outcome,
            result=rehearsal.result,
            reconciliation_receipt=rehearsal.reconciliation_receipt,
        )
