import pytest

from general_execution.execution_protocol import (
    ExecutionMethodProfile,
    ExecutionProtocolError,
    ExecutionProtocolRequest,
    InvocationMode,
    ProtocolDisposition,
    ResourceCauseKind,
    ResourceObservation,
    SystemCapability,
    decide_execution_protocol,
)
from general_execution.work_sparse_unattended import (
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
)

AUTH = "authority://waterfound/execution-protocol-001"
PRED = "verification://same-predicate"


def system(system_id, capabilities, *, cost=1, execution=False):
    return SystemCapability(
        system_id=system_id,
        capabilities=tuple(capabilities),
        cost_rank=cost,
        execution_capable=execution,
    )


def request(**overrides):
    values = dict(
        request_id="EP-CASE-1",
        objective="Verify candidate without weakening evidence",
        evidence_predicate=PRED,
        required_system_capabilities=("system_selection", "execution_composition"),
        repository="Waterfound/General-Execution",
        authority_ref=AUTH,
        required_executor_capabilities=("repo_read", "test_execution"),
        requested_actions=("inspect_ci", "run_tests"),
        requires_observed_evidence=True,
        requires_state_change=False,
        advisory_allowed=True,
    )
    values.update(overrides)
    return ExecutionProtocolRequest(**values)


def envelope():
    return UnattendedAuthorityEnvelope(
        envelope_id="ep-001",
        authority_ref=AUTH,
        allowed_repositories=("Waterfound/General-Execution",),
        allowed_actions=("inspect_ci", "run_tests"),
        forbidden_actions=("merge_main", "paid_spend", "credential_change"),
        max_work_invocations=0,
        max_paid_spend_cents=0,
    )


def executor(executor_id, *, cost=1, available=True):
    return ExecutorCapability(
        executor_id=executor_id,
        capabilities=("repo_read", "test_execution"),
        cost_rank=cost,
        available=available,
        evidence_ref=f"evidence://{executor_id}",
    )


def profile(executor_id, predicates=(PRED,), quality=2):
    return ExecutionMethodProfile(
        executor_id=executor_id,
        evidence_predicates=tuple(predicates),
        evidence_quality_rank=quality,
    )


def available(executor_id):
    return ResourceObservation(
        executor_id=executor_id,
        available=True,
        cause_kind=ResourceCauseKind.NONE,
        cause_code="available",
        evidence_ref=f"resource://{executor_id}/available",
    )


def exhausted_actions():
    return ResourceObservation(
        executor_id="github_actions",
        available=False,
        cause_kind=ResourceCauseKind.CAPACITY,
        cause_code="included_minutes_exhausted_2000_of_2000",
        evidence_ref="billing://github-actions/2026-10/2000-of-2000",
    )


SYSTEMS = (
    system("total-systems-steward", ("system_selection",), cost=0),
    system("general-execution", ("execution_composition",), cost=0, execution=True),
    system("pse", ("capability_substitution",), cost=1),
)


def test_no_system_mode_is_explicit():
    decision = decide_execution_protocol(
        request=request(
            required_system_capabilities=(),
            required_executor_capabilities=(),
            requested_actions=(),
            requires_observed_evidence=False,
            requires_state_change=False,
        ),
        systems=SYSTEMS,
        envelope=envelope(),
    )
    assert decision.invocation_mode is InvocationMode.NO_SYSTEM
    assert decision.disposition is ProtocolDisposition.NO_SYSTEM_REQUIRED
    assert decision.selected_system_ids == ()
    assert not decision.execution_triggered


def test_advisory_mode_is_distinct_from_real_run():
    decision = decide_execution_protocol(
        request=request(
            required_system_capabilities=("system_selection",),
            required_executor_capabilities=(),
            requested_actions=(),
            requires_observed_evidence=False,
            requires_state_change=False,
        ),
        systems=SYSTEMS,
        envelope=envelope(),
    )
    assert decision.invocation_mode is InvocationMode.ADVISORY
    assert decision.disposition is ProtocolDisposition.ADVISORY_READY
    assert decision.selected_system_ids == ("total-systems-steward",)
    assert decision.selected_executor_id is None


def test_multiple_systems_produce_composed_real_run():
    decision = decide_execution_protocol(
        request=request(),
        systems=SYSTEMS,
        envelope=envelope(),
        executors=(executor("connector_api"),),
        resource_observations=(available("connector_api"),),
        method_profiles=(profile("connector_api"),),
    )
    assert decision.invocation_mode is InvocationMode.COMPOSED_REAL_RUN
    assert decision.selected_system_ids == ("general-execution", "total-systems-steward")
    assert decision.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    assert decision.selected_executor_id == "connector_api"
    assert decision.evidence_predicate_preserved
    assert not decision.execution_triggered


def test_actions_capacity_exhaustion_selects_equivalent_zero_cost_alternative():
    decision = decide_execution_protocol(
        request=request(
            required_system_capabilities=(
                "system_selection",
                "execution_composition",
                "capability_substitution",
            ),
        ),
        systems=SYSTEMS,
        envelope=envelope(),
        executors=(
            executor("github_actions", cost=0),
            executor("connector_api", cost=1),
        ),
        resource_observations=(
            exhausted_actions(),
            available("connector_api"),
        ),
        method_profiles=(
            profile("github_actions"),
            profile("connector_api"),
        ),
    )
    assert decision.invocation_mode is InvocationMode.COMPOSED_REAL_RUN
    assert decision.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    assert decision.selected_executor_id == "connector_api"
    assert "github_actions:capacity:included_minutes_exhausted_2000_of_2000" in decision.resource_findings
    assert any(
        item.startswith("github_actions|") and "resource_unavailable:capacity:" in item
        for item in decision.rejected_executors
    )
    assert decision.evidence_predicate_preserved
    assert not decision.authority_created
    assert not decision.execution_triggered


def test_actions_capacity_exhaustion_waits_only_when_no_equivalent_alternative_exists():
    decision = decide_execution_protocol(
        request=request(
            required_system_capabilities=(
                "system_selection",
                "execution_composition",
                "capability_substitution",
            ),
        ),
        systems=SYSTEMS,
        envelope=envelope(),
        executors=(
            executor("github_actions", cost=0),
            executor("connector_api", cost=1),
        ),
        resource_observations=(
            exhausted_actions(),
            available("connector_api"),
        ),
        method_profiles=(
            profile("github_actions"),
            profile("connector_api", predicates=("verification://weaker-predicate",)),
        ),
    )
    assert decision.disposition is ProtocolDisposition.CONDITION_WAIT
    assert decision.selected_executor_id is None
    assert "no_evidence_equivalent_available_executor" in decision.reasons
    assert any("predicate_not_covered" in item for item in decision.rejected_executors)


def test_unavailable_executor_without_resolved_cause_is_rejected():
    with pytest.raises(ExecutionProtocolError, match="no resolved resource cause"):
        decide_execution_protocol(
            request=request(),
            systems=SYSTEMS,
            envelope=envelope(),
            executors=(executor("github_actions", available=False),),
            resource_observations=(),
            method_profiles=(profile("github_actions"),),
        )


def test_forbidden_action_remains_human_gate_after_routing():
    decision = decide_execution_protocol(
        request=request(requested_actions=("merge_main",)),
        systems=SYSTEMS,
        envelope=envelope(),
        executors=(executor("connector_api"),),
        resource_observations=(available("connector_api"),),
        method_profiles=(profile("connector_api"),),
    )
    assert decision.disposition is ProtocolDisposition.HUMAN_GATE
    assert decision.selected_executor_id is None
    assert not decision.authority_created


def test_existing_execution_is_observed_not_redispatched_even_if_new_capacity_is_unavailable():
    decision = decide_execution_protocol(
        request=request(existing_execution_ref="provider://already-running"),
        systems=SYSTEMS,
        envelope=envelope(),
        executors=(),
        resource_observations=(),
        method_profiles=(),
    )
    assert decision.disposition is ProtocolDisposition.OBSERVE_EXISTING
    assert decision.selected_executor_id is None
    assert not decision.execution_triggered


def test_uncovered_system_capability_fails_closed():
    decision = decide_execution_protocol(
        request=request(required_system_capabilities=("unknown_system_capability",)),
        systems=SYSTEMS,
        envelope=envelope(),
    )
    assert decision.disposition is ProtocolDisposition.CONDITION_WAIT
    assert decision.uncovered_system_capabilities == ("unknown_system_capability",)
