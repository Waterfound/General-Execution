from general_execution.cutpoint_matrix import CUT_POINT_ORDER, run_reference_cut_point_matrix


def test_reference_cut_point_matrix_has_canonical_safe_sequence(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="canonical")
    assert tuple(item.cut_point for item in report.observations) == CUT_POINT_ORDER
    assert tuple(item.disposition for item in report.observations) == (
        "orphan_context",
        "remain_unknown",
        "keep_running",
        "terminal_pending_reconciliation",
        "terminal_plan_reproducible",
        "reconciled",
    )


def test_context_only_is_safe_orphan_without_active_capacity(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="orphan")
    item = report.observations[0]
    assert item.provider_state == "absent"
    assert item.capacity_head_digest is None
    assert item.active_binding_count == 0
    assert item.active_lease_count == 0
    assert item.outcome_digest is None


def test_capacity_before_provider_remains_unknown_and_occupied(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="missing-provider")
    item = report.observations[1]
    assert item.provider_state == "not_found"
    assert item.active_binding_count == 1
    assert item.active_lease_count == 1
    assert item.assessment_digest is not None
    assert item.outcome_digest is None
    assert item.reconciliation_plan_digest is None


def test_running_provider_keeps_same_capacity_occupied(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="running")
    item = report.observations[2]
    assert item.provider_state == "running"
    assert item.active_binding_count == 1
    assert item.active_lease_count == 1
    assert item.provider_record_digest is not None
    assert item.status_observation_digest is not None
    assert item.outcome_digest is None


def test_terminal_persistence_does_not_release_capacity(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="terminal")
    item = report.observations[3]
    assert item.provider_state == "terminal"
    assert item.active_binding_count == 1
    assert item.active_lease_count == 1
    assert item.outcome_digest is not None
    assert item.reconciliation_plan_digest is not None


def test_lost_reconciliation_plan_is_rederived_without_durable_mutation(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="plan")
    terminal = report.observations[3]
    planned = report.observations[4]
    assert terminal.capacity_head_digest == planned.capacity_head_digest
    assert terminal.provider_record_digest == planned.provider_record_digest
    assert terminal.outcome_digest == planned.outcome_digest
    assert terminal.reconciliation_plan_digest == planned.reconciliation_plan_digest
    assert planned.active_lease_count == 1


def test_only_reconciliation_cas_frees_capacity(tmp_path):
    report = run_reference_cut_point_matrix(tmp_path / "matrix", suffix="cas")
    before = report.observations[4]
    after = report.observations[5]
    assert before.active_binding_count == 1
    assert before.active_lease_count == 1
    assert after.active_binding_count == 0
    assert after.active_lease_count == 0
    assert after.provider_state == "terminal"
    assert before.capacity_head_digest != after.capacity_head_digest


def test_matrix_is_deterministic_across_fresh_directories(tmp_path):
    first = run_reference_cut_point_matrix(tmp_path / "a", suffix="deterministic")
    second = run_reference_cut_point_matrix(tmp_path / "b", suffix="deterministic")
    assert first == second
    assert first.digest == second.digest
