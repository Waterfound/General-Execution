from general_execution.canonical_process_harness import run_process_separated_canonical_cold_recovery


def test_prepare_and_resume_run_in_distinct_child_processes(tmp_path):
    evidence = run_process_separated_canonical_cold_recovery(tmp_path, suffix="distinct")

    assert evidence.prepare.pid != evidence.resume.pid
    assert evidence.prepare.process_token != evidence.resume.process_token
    assert evidence.prepare.ppid == evidence.parent_pid
    assert evidence.resume.ppid == evidence.parent_pid
    assert evidence.prepare.pid != evidence.parent_pid
    assert evidence.resume.pid != evidence.parent_pid


def test_process_separated_resume_preserves_cold_ambiguity_boundary(tmp_path):
    evidence = run_process_separated_canonical_cold_recovery(tmp_path, suffix="boundary")
    report = evidence.resume.payload["report"]

    assert report["context_mode"] == "cold_reconstructed"
    assert report["recovery_action"] == "reconcile_provider"
    assert report["blind_resubmissions_authorized"] == 0
    assert report["provider_outcomes_inferred"] == 0
    assert evidence.recovery_action == "reconcile_provider"


def test_process_boundary_reconstructs_same_context_and_invocation(tmp_path):
    evidence = run_process_separated_canonical_cold_recovery(tmp_path, suffix="identity")
    receipt = evidence.prepare.payload["receipt"]
    report = evidence.resume.payload["report"]

    assert receipt["context_id"] == report["context_id"] == evidence.context_id
    assert receipt["invocation_id"] == report["invocation_id"] == evidence.invocation_id
    assert evidence.preparation_digest == evidence.prepare.payload["receipt_digest"]
    assert evidence.recovery_digest == evidence.resume.payload["report_digest"]


def test_fresh_directories_reproduce_semantics_not_process_evidence(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = run_process_separated_canonical_cold_recovery(first_root, suffix="same")
    second = run_process_separated_canonical_cold_recovery(second_root, suffix="same")

    assert first.semantic_digest == second.semantic_digest
    assert first.preparation_digest == second.preparation_digest
    assert first.recovery_digest == second.recovery_digest
    assert first.context_id == second.context_id
    assert first.invocation_id == second.invocation_id
    assert (first.prepare.process_token, first.resume.process_token) != (
        second.prepare.process_token,
        second.resume.process_token,
    )
    assert first.evidence_digest != second.evidence_digest


def test_replaying_same_stores_from_new_processes_is_semantically_exact(tmp_path):
    first = run_process_separated_canonical_cold_recovery(tmp_path, suffix="replay")
    second = run_process_separated_canonical_cold_recovery(tmp_path, suffix="replay")

    assert first.semantic_digest == second.semantic_digest
    assert first.preparation_digest == second.preparation_digest
    assert first.recovery_digest == second.recovery_digest
    assert first.context_id == second.context_id
    assert first.invocation_id == second.invocation_id
    assert first.prepare.process_token != second.prepare.process_token
    assert first.resume.process_token != second.resume.process_token
