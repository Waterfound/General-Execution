import copy

import pytest

from general_execution.work_sparse_unattended import (
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    WorkSparseError,
    decision_to_dict,
    decide_work_sparse_route,
    verify_work_sparse_decision,
)


AUTH = "authority://waterfound/work-sparse-unattended-001"


def envelope(**overrides):
    values = dict(
        envelope_id="work-sparse-unattended-001",
        authority_ref=AUTH,
        allowed_repositories=(
            "Waterfound/General-Execution",
            "Waterfound/Build-Colony",
            "Waterfound/FAE-testnet",
        ),
        allowed_actions=(
            "read_state",
            "inspect_ci",
            "run_tests",
            "open_draft_pr",
            "persist_evidence",
            "bounded_retry",
            "run_diagnostic",
            "run_assurance",
        ),
        forbidden_actions=(
            "merge_main",
            "release",
            "mainnet",
            "consensus_change",
            "economics_change",
            "paid_spend",
            "credential_change",
            "destructive_action",
            "physical_hardware",
        ),
        max_work_invocations=0,
        max_paid_spend_cents=0,
    )
    values.update(overrides)
    return UnattendedAuthorityEnvelope(**values)


def work(**overrides):
    values = dict(
        work_id="WS-001",
        objective="Continue bounded verification",
        repository="Waterfound/General-Execution",
        source_revision="candidate-sha",
        authority_ref=AUTH,
        required_capabilities=("repo_read", "ci_dispatch"),
        requested_actions=("inspect_ci", "run_tests"),
    )
    values.update(overrides)
    return UnattendedWorkItem(**values)


def executor(
    executor_id,
    capabilities,
    cost_rank,
    *,
    requires_work=False,
    paid=False,
    estimated_cost_cents=0,
    available=True,
):
    return ExecutorCapability(
        executor_id=executor_id,
        capabilities=tuple(capabilities),
        cost_rank=cost_rank,
        requires_work=requires_work,
        paid=paid,
        estimated_cost_cents=estimated_cost_cents,
        available=available,
        evidence_ref=f"evidence://{executor_id}",
    )


def test_prefers_non_work_executor_even_when_work_has_lower_cost_rank():
    e = envelope(max_work_invocations=10)
    item = work()
    executors = (
        executor("work", ("repo_read", "ci_dispatch", "browser_ui"), 0, requires_work=True),
        executor("github_actions", ("repo_read", "ci_dispatch"), 10),
    )
    decision = decide_work_sparse_route(e, item, executors)
    assert decision.disposition == "DISPATCH"
    assert decision.selected_executor_id == "github_actions"
    assert not decision.work_required
    assert not decision.execution_triggered
    assert not decision.authority_created


def test_work_is_selected_only_when_capability_requires_it_and_budget_exists():
    e = envelope(max_work_invocations=1)
    item = work(required_capabilities=("browser_ui",))
    executors = (
        executor("github_actions", ("repo_read", "ci_dispatch"), 0),
        executor("work", ("browser_ui", "repo_read"), 20, requires_work=True),
    )
    decision = decide_work_sparse_route(e, item, executors)
    assert decision.disposition == "DISPATCH"
    assert decision.selected_executor_id == "work"
    assert decision.work_required
    assert "work_required_by_capability" in decision.reasons


def test_work_budget_zero_fails_closed_without_fallback_side_effect():
    e = envelope(max_work_invocations=0)
    item = work(required_capabilities=("browser_ui",))
    executors = (
        executor("work", ("browser_ui",), 1, requires_work=True),
    )
    decision = decide_work_sparse_route(e, item, executors)
    assert decision.disposition == "CONDITION_WAIT"
    assert decision.selected_executor_id is None
    assert decision.reasons == ("work:work_budget_exhausted",)
    assert not decision.execution_triggered


def test_existing_execution_is_observed_not_redispatched():
    item = work(existing_execution_ref="github-actions://Waterfound/General-Execution/actions/runs/1")
    decision = decide_work_sparse_route(
        envelope(),
        item,
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "OBSERVE_EXISTING"
    assert decision.selected_executor_id is None
    assert decision.reasons[0].startswith("existing_execution:")


@pytest.mark.parametrize(
    "requested_action",
    [
        "merge_main",
        "release",
        "mainnet",
        "consensus_change",
        "economics_change",
        "credential_change",
        "destructive_action",
        "physical_hardware",
    ],
)
def test_forbidden_actions_stop_at_human_gate(requested_action):
    item = work(requested_actions=(requested_action,))
    decision = decide_work_sparse_route(
        envelope(),
        item,
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "HUMAN_GATE"
    assert decision.selected_executor_id is None
    assert decision.reasons == (f"forbidden_action:{requested_action}",)


def test_unknown_action_does_not_become_implicit_authority():
    item = work(requested_actions=("invent_new_authority",))
    decision = decide_work_sparse_route(
        envelope(),
        item,
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "HUMAN_GATE"
    assert decision.reasons == ("action_not_authorized:invent_new_authority",)


def test_authority_ref_mismatch_stops_before_executor_selection():
    item = work(authority_ref="authority://other")
    decision = decide_work_sparse_route(
        envelope(),
        item,
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "HUMAN_GATE"
    assert decision.reasons == ("authority_ref_mismatch",)


def test_repository_scope_mismatch_stops_before_executor_selection():
    item = work(repository="Other/private")
    decision = decide_work_sparse_route(
        envelope(),
        item,
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "HUMAN_GATE"
    assert decision.reasons == ("repository_outside_authority_envelope",)


def test_paid_executor_is_blocked_by_zero_spend_envelope():
    item = work(required_capabilities=("special_compute",))
    decision = decide_work_sparse_route(
        envelope(max_paid_spend_cents=0),
        item,
        (
            executor(
                "paid_provider",
                ("special_compute",),
                1,
                paid=True,
                estimated_cost_cents=1,
            ),
        ),
    )
    assert decision.disposition == "CONDITION_WAIT"
    assert decision.reasons == ("paid_provider:paid_budget_exhausted",)


def test_free_executor_beats_paid_executor_regardless_of_cost_rank():
    item = work()
    decision = decide_work_sparse_route(
        envelope(max_paid_spend_cents=10000),
        item,
        (
            executor(
                "paid_provider",
                ("repo_read", "ci_dispatch"),
                0,
                paid=True,
                estimated_cost_cents=1,
            ),
            executor("github_actions", ("repo_read", "ci_dispatch"), 10),
        ),
    )
    assert decision.selected_executor_id == "github_actions"


def test_matching_but_unavailable_executor_waits():
    decision = decide_work_sparse_route(
        envelope(),
        work(),
        (
            executor(
                "github_actions",
                ("repo_read", "ci_dispatch"),
                1,
                available=False,
            ),
        ),
    )
    assert decision.disposition == "CONDITION_WAIT"
    assert decision.reasons == ("matching_executors_unavailable",)


def test_no_capability_match_waits_without_widening():
    decision = decide_work_sparse_route(
        envelope(),
        work(required_capabilities=("browser_ui",)),
        (executor("github_actions", ("repo_read", "ci_dispatch"), 1),),
    )
    assert decision.disposition == "CONDITION_WAIT"
    assert decision.reasons == ("no_executor_matches_required_capabilities",)


def test_decision_replay_detects_executor_substitution():
    e = envelope()
    item = work()
    executors = (
        executor("github_actions", ("repo_read", "ci_dispatch"), 1),
        executor("connector_api", ("repo_read", "ci_dispatch"), 2),
    )
    usage = ControllerUsage()
    decision = decision_to_dict(decide_work_sparse_route(e, item, executors, usage))
    assert verify_work_sparse_decision(e, item, executors, usage, decision)

    tampered = copy.deepcopy(decision)
    tampered["selected_executor_id"] = "connector_api"
    assert not verify_work_sparse_decision(e, item, executors, usage, tampered)


def test_decision_replay_detects_authority_or_execution_claim_tampering():
    e = envelope()
    item = work()
    executors = (executor("github_actions", ("repo_read", "ci_dispatch"), 1),)
    usage = ControllerUsage()
    decision = decision_to_dict(decide_work_sparse_route(e, item, executors, usage))

    authority_tamper = copy.deepcopy(decision)
    authority_tamper["authority_created"] = True
    assert not verify_work_sparse_decision(e, item, executors, usage, authority_tamper)

    execution_tamper = copy.deepcopy(decision)
    execution_tamper["execution_triggered"] = True
    assert not verify_work_sparse_decision(e, item, executors, usage, execution_tamper)


def test_work_invocation_usage_is_enforced_exactly_at_boundary():
    e = envelope(max_work_invocations=1)
    item = work(required_capabilities=("browser_ui",))
    executors = (executor("work", ("browser_ui",), 1, requires_work=True),)

    allowed = decide_work_sparse_route(
        e, item, executors, ControllerUsage(work_invocations_used=0)
    )
    blocked = decide_work_sparse_route(
        e, item, executors, ControllerUsage(work_invocations_used=1)
    )
    assert allowed.disposition == "DISPATCH"
    assert blocked.disposition == "CONDITION_WAIT"


def test_invalid_authority_envelope_cannot_overlap_allowed_and_forbidden_actions():
    with pytest.raises(WorkSparseError):
        envelope(
            allowed_actions=("read_state", "merge_main"),
            forbidden_actions=("merge_main",),
        )
