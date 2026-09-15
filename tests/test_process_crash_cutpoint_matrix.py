from general_execution.canonical_crash_matrix import (
    EXPECTED_DISPOSITION,
    run_process_crash_cut_point,
    run_process_crash_matrix,
)


def test_context_only_crash_recovers_as_inert_orphan(tmp_path):
    evidence = run_process_crash_cut_point(
        tmp_path,
        "context_only",
        suffix="context-only",
    )
    assert evidence.expected_disposition == "inert_orphan"
    assert evidence.recover.payload["active_binding_count"] == 0
    assert evidence.recover.payload["recovery_action"] is None


def test_prepared_crash_recovers_as_inert_orphan(tmp_path):
    evidence = run_process_crash_cut_point(
        tmp_path,
        "prepared",
        suffix="prepared",
    )
    assert evidence.expected_disposition == "inert_orphan"
    assert evidence.recover.payload["active_binding_count"] == 0
    assert evidence.recover.payload["recovery_action"] is None


def test_capacity_commit_crash_recovers_begin_submission(tmp_path):
    evidence = run_process_crash_cut_point(
        tmp_path,
        "capacity_committed",
        suffix="capacity",
    )
    assert evidence.expected_disposition == "begin_submission"
    assert evidence.recover.payload["active_binding_count"] == 1
    assert evidence.recover.payload["recovery_action"] == "begin_submission"
    assert evidence.cut.payload["context_id"] == evidence.recover.payload["context_id"]
    assert evidence.cut.payload["invocation_id"] == evidence.recover.payload["invocation_id"]


def test_submission_unknown_crash_recovers_reconcile_provider(tmp_path):
    evidence = run_process_crash_cut_point(
        tmp_path,
        "submission_unknown",
        suffix="unknown",
    )
    assert evidence.expected_disposition == "reconcile_provider"
    assert evidence.recover.payload["active_binding_count"] == 1
    assert evidence.recover.payload["recovery_action"] == "reconcile_provider"
    assert evidence.cut.payload["context_id"] == evidence.recover.payload["context_id"]
    assert evidence.cut.payload["invocation_id"] == evidence.recover.payload["invocation_id"]


def test_full_process_crash_matrix_is_ordered_and_process_separated(tmp_path):
    matrix = run_process_crash_matrix(tmp_path)
    assert tuple(item.cut_point for item in matrix) == tuple(EXPECTED_DISPOSITION)
    assert tuple(item.recover.payload["disposition"] for item in matrix) == tuple(
        EXPECTED_DISPOSITION[item.cut_point] for item in matrix
    )
    assert all(item.cut.pid != item.recover.pid for item in matrix)
    assert all(item.cut.process_token != item.recover.process_token for item in matrix)
    assert len({item.semantic_digest for item in matrix}) == len(matrix)
