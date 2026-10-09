import pytest

from general_execution.execution_protocol import (
    CapabilityProjection,
    ExecutionMethodProfile,
    ExecutionProtocolError,
    ExecutionProtocolRequest,
    InvocationMode,
    ProtocolDisposition,
    ResourceCauseKind,
    ResourceObservation,
    decide_execution_protocol,
)
from general_execution.work_sparse_unattended import (
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
)

AUTH = "authority://example/execution-protocol"
REG = "sha256:" + "1" * 64
AUTH_DIGEST = "sha256:" + "2" * 64
PROJ = "projection://ep/example"
PRED = "verification://same-predicate"


def candidate(candidate_id, capabilities, *, cost=1, execution=False):
    return CapabilityProjection(
        candidate_id=candidate_id,
        capability_ids=tuple(capabilities),
        projection_id=PROJ,
        registry_revision_digest=REG,
        authority_ref_digest=AUTH_DIGEST,
        cost_rank=cost,
        execution_capable=execution,
    )


def request(**overrides):
    values = dict(
        request_id="EP-CASE-1",
        objective="Verify candidate without weakening evidence",
        evidence_predicate=PRED,
        required_capability_ids=("cap-select", "exec-compose"),
        repository="example/repo",
        authority_ref=AUTH,
        projection_id=PROJ,
        registry_revision_digest=REG,
        authority_ref_digest=AUTH_DIGEST,
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
        allowed_repositories=("example/repo",),
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


def exhausted_private_runner():
    return ResourceObservation(
        executor_id="private_repo_runner",
        available=False,
        cause_kind=ResourceCauseKind.CAPACITY,
        cause_code="included_minutes_exhausted",
        evidence_ref="billing://private-runner/capacity",
    )


CANDIDATES = (
    candidate("candidate-a", ("cap-select",), cost=0),
    candidate("candidate-b", ("exec-compose",), cost=0, execution=True),
    candidate("candidate-c", ("substitute",), cost=1),
)


def test_no_system_mode_is_explicit():
    decision = decide_execution_protocol(
        request=request(
            required_capability_ids=(),
            required_executor_capabilities=(),
            requested_actions=(),
            requires_observed_evidence=False,
            requires_state_change=False,
        ),
        candidates=CANDIDATES,
        envelope=envelope(),
    )
    assert decision.invocation_mode is InvocationMode.NO_SYSTEM
    assert decision.disposition is ProtocolDisposition.NO_SYSTEM_REQUIRED
    assert decision.selected_candidate_ids == ()
    assert not decision.execution_triggered


def test_advisory_mode_is_distinct_from_real_run():
    decision = decide_execution_protocol(
        request=request(
            required_capability_ids=("cap-select",),
            required_executor_capabilities=(),
            requested_actions=(),
            requires_observed_evidence=False,
            requires_state_change=False,
        ),
        candidates=CANDIDATES,
        envelope=envelope(),
    )
    assert decision.invocation_mode is InvocationMode.ADVISORY
    assert decision.disposition is ProtocolDisposition.ADVISORY_READY
    assert decision.selected_candidate_ids == ("candidate-a",)
    assert decision.selected_executor_id is None


def test_multiple_candidates_produce_composed_real_run():
    decision = decide_execution_protocol(
        request=request(),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(executor("executor-a"),),
        resource_observations=(available("executor-a"),),
        method_profiles=(profile("executor-a"),),
    )
    assert decision.invocation_mode is InvocationMode.COMPOSED_REAL_RUN
    assert decision.selected_candidate_ids == ("candidate-a", "candidate-b")
    assert decision.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    assert decision.selected_executor_id == "executor-a"
    assert decision.evidence_predicate_preserved
    assert not decision.execution_triggered


def test_capacity_exhaustion_selects_equivalent_zero_cost_alternative():
    decision = decide_execution_protocol(
        request=request(
            required_capability_ids=("cap-select", "exec-compose", "substitute"),
        ),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(
            executor("private_repo_runner", cost=0),
            executor("executor-a", cost=1),
        ),
        resource_observations=(
            exhausted_private_runner(),
            available("executor-a"),
        ),
        method_profiles=(
            profile("private_repo_runner"),
            profile("executor-a"),
        ),
    )
    assert decision.invocation_mode is InvocationMode.COMPOSED_REAL_RUN
    assert decision.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    assert decision.selected_executor_id == "executor-a"
    assert (
        "private_repo_runner:capacity:included_minutes_exhausted"
        in decision.resource_findings
    )
    assert any(
        item.startswith("private_repo_runner|")
        and "resource_unavailable:capacity:" in item
        for item in decision.rejected_executors
    )
    assert decision.evidence_predicate_preserved


def test_private_runner_exhaustion_does_not_globalize_to_public_runner():
    decision = decide_execution_protocol(
        request=request(
            required_capability_ids=("cap-select", "exec-compose", "substitute"),
        ),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(
            executor("private_repo_runner", cost=0),
            executor("public_repo_runner", cost=1),
        ),
        resource_observations=(
            exhausted_private_runner(),
            available("public_repo_runner"),
        ),
        method_profiles=(
            profile("private_repo_runner"),
            profile("public_repo_runner"),
        ),
    )
    assert decision.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    assert decision.selected_executor_id == "public_repo_runner"


def test_capacity_waits_only_when_no_equivalent_alternative_exists():
    decision = decide_execution_protocol(
        request=request(
            required_capability_ids=("cap-select", "exec-compose", "substitute"),
        ),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(
            executor("private_repo_runner", cost=0),
            executor("executor-a", cost=1),
        ),
        resource_observations=(
            exhausted_private_runner(),
            available("executor-a"),
        ),
        method_profiles=(
            profile("private_repo_runner"),
            profile("executor-a", predicates=("verification://weaker-predicate",)),
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
            candidates=CANDIDATES,
            envelope=envelope(),
            executors=(executor("executor-a", available=False),),
            resource_observations=(),
            method_profiles=(profile("executor-a"),),
        )


def test_forbidden_action_remains_human_gate_after_routing():
    decision = decide_execution_protocol(
        request=request(requested_actions=("merge_main",)),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(executor("executor-a"),),
        resource_observations=(available("executor-a"),),
        method_profiles=(profile("executor-a"),),
    )
    assert decision.disposition is ProtocolDisposition.HUMAN_GATE
    assert decision.selected_executor_id is None
    assert not decision.authority_created


def test_existing_execution_is_observed_not_redispatched():
    decision = decide_execution_protocol(
        request=request(existing_execution_ref="provider://already-running"),
        candidates=CANDIDATES,
        envelope=envelope(),
        executors=(),
        resource_observations=(),
        method_profiles=(),
    )
    assert decision.disposition is ProtocolDisposition.OBSERVE_EXISTING
    assert decision.selected_executor_id is None
    assert not decision.execution_triggered


def test_uncovered_capability_fails_closed():
    decision = decide_execution_protocol(
        request=request(required_capability_ids=("cap-unknown",)),
        candidates=CANDIDATES,
        envelope=envelope(),
    )
    assert decision.disposition is ProtocolDisposition.CONDITION_WAIT
    assert decision.uncovered_capability_ids == ("cap-unknown",)


def test_public_projection_rejects_internal_identity_disclosure():
    with pytest.raises(ExecutionProtocolError, match="cannot disclose internal identity"):
        CapabilityProjection(
            candidate_id="candidate-a",
            capability_ids=("cap-select",),
            projection_id=PROJ,
            registry_revision_digest=REG,
            authority_ref_digest=AUTH_DIGEST,
            internal_identity_disclosed=True,
        )


def test_candidates_from_mixed_private_registry_projections_fail_closed():
    mixed = (
        candidate("candidate-a", ("cap-select",), cost=0),
        CapabilityProjection(
            candidate_id="candidate-b",
            capability_ids=("exec-compose",),
            projection_id="projection://other",
            registry_revision_digest="sha256:" + "3" * 64,
            authority_ref_digest=AUTH_DIGEST,
            execution_capable=True,
        ),
    )
    with pytest.raises(ExecutionProtocolError, match="one bound projection"):
        decide_execution_protocol(
            request=request(),
            candidates=mixed,
            envelope=envelope(),
        )


def test_request_projection_binding_rejects_consistent_but_wrong_projection():
    wrong = tuple(
        CapabilityProjection(
            candidate_id=item.candidate_id,
            capability_ids=item.capability_ids,
            projection_id="projection://wrong",
            registry_revision_digest="sha256:" + "4" * 64,
            authority_ref_digest=AUTH_DIGEST,
            cost_rank=item.cost_rank,
            execution_capable=item.execution_capable,
        )
        for item in CANDIDATES
    )
    with pytest.raises(ExecutionProtocolError, match="does not match request binding"):
        decide_execution_protocol(
            request=request(),
            candidates=wrong,
            envelope=envelope(),
        )


def test_capability_request_requires_projection_binding():
    with pytest.raises(ExecutionProtocolError, match="projection_id is required"):
        ExecutionProtocolRequest(
            request_id="EP-UNBOUND",
            objective="unbound capability selection",
            evidence_predicate=PRED,
            required_capability_ids=("cap-select",),
            repository="example/repo",
            authority_ref=AUTH,
        )
