import pytest

from general_execution.canonical import sha256_digest
from general_execution.holistic_symbiosis import (
    ExecutorProviderBinding,
    HolisticSymbiosisError,
    build_steward_predictive_bundle,
    compose_symbiotic_route,
    reconcile_independent_assurance,
)
from general_execution.predictive_sovereign_execution import (
    GateCandidate,
    GateKind,
    PredictiveTask,
    VerificationObservation,
    VerificationVerdict,
)
from general_execution.provider_portability import (
    InternalLineageBinding,
    ProviderResource,
    ProviderRoutingAuthority,
    ResourceDisposition,
)
from general_execution.work_sparse_unattended import (
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
)


AUTH="authority://waterfound/hsr"
DIG=lambda x: sha256_digest(x)


def envelope(**overrides):
    data=dict(
        envelope_id="hsr",
        authority_ref=AUTH,
        allowed_repositories=("Waterfound/General-Execution",),
        allowed_actions=("inspect_ci","run_tests"),
        forbidden_actions=("merge_main","release","paid_spend"),
        max_work_invocations=0,
        max_paid_spend_cents=0,
    )
    data.update(overrides)
    return UnattendedAuthorityEnvelope(**data)


def work(**overrides):
    data=dict(
        work_id="HSR-EXEC-1",
        objective="verify holistic composition",
        repository="Waterfound/General-Execution",
        source_revision="candidate",
        authority_ref=AUTH,
        required_capabilities=("repo_read","test_execution"),
        requested_actions=("inspect_ci","run_tests"),
    )
    data.update(overrides)
    return UnattendedWorkItem(**data)


def executor(name, *, work=False, paid=False, cost=1, cents=0, available=True):
    return ExecutorCapability(
        executor_id=name,
        capabilities=("repo_read","test_execution"),
        cost_rank=cost,
        estimated_cost_cents=cents,
        requires_work=work,
        paid=paid,
        available=available,
        evidence_ref=f"evidence://{name}",
    )


def lineage():
    return InternalLineageBinding(
        work_id="internal-hsr",
        portfolio_ref="portfolio://hsr",
        source_revision="candidate",
        authority_ref=AUTH,
        required_capabilities=("repo_read","test_execution"),
        input_artifact_digests=(DIG("input"),),
        output_contract_digest=DIG("output"),
        semantic_context=("holistic-symbiosis",),
    )


def resource(resource_id, disposition=ResourceDisposition.AVAILABLE):
    return ProviderResource(
        resource_id=resource_id,
        provider_id="github",
        disposition=disposition,
        capabilities=("repo_read","test_execution"),
        billing_scope_ref="github-actions://Waterfound/General-Execution",
        authority_ref="authority://provider/existing",
        admission_digest=DIG(resource_id),
        evidence_refs=(f"evidence://{resource_id}",),
    )


def routing():
    return ProviderRoutingAuthority(
        authority_ref="authority://provider-routing/existing",
        allowed_resource_ids=("ga","other"),
        allowed_capabilities=("repo_read","test_execution"),
    )


def test_steward_bundle_composes_precompute_forecast_and_recovery():
    bundle=build_steward_predictive_bundle(
        current_gate_ref="authority://merge",
        tasks=(
            PredictiveTask("prepare-tests","test"),
            PredictiveTask("merge","merge",requires_authority=True),
        ),
        gates=(
            GateCandidate(
                "authority://merge",
                GateKind.HUMAN_AUTHORITY,
                1,
                "merge",
                ("evidence://candidate",),
                True,
            ),
        ),
        capsule_id="hsr-capsule",
        source_refs=("github://repo/commit/candidate",),
        durable_state_digests=(DIG("state"),),
        authority_refs=(AUTH,),
        resource_aliases=("canonical-source","durable-runtime"),
        reconstruction_steps=("checkout","restore","verify"),
        verification_predicates=("state-digest-match",),
    )
    assert bundle.precomputation.selected_task_ids == ("prepare-tests",)
    assert bundle.precomputation.deferred_task_ids == ("merge",)
    assert bundle.gate_forecast.compilation_refs == ("authority://merge",)
    assert bundle.recovery_capsule.secret_material_persisted is False
    assert bundle.authority_created is False
    assert bundle.execution_triggered is False


def test_work_sparse_and_pse_select_same_non_work_zero_cost_executor():
    decision=compose_symbiotic_route(
        envelope=envelope(max_work_invocations=1),
        work=work(),
        executors=(
            executor("work",work=True,cost=0),
            executor("github_actions",cost=10),
        ),
        evidence_predicate="same-verification",
    )
    assert decision.selected_executor_id=="github_actions"
    assert decision.substitution.selected_method_id=="github_actions"
    assert decision.ready_for_existing_admission is True
    assert decision.execution_triggered is False


def test_provider_portability_is_composed_after_executor_selection():
    decision=compose_symbiotic_route(
        envelope=envelope(),
        work=work(),
        executors=(executor("github_actions"),),
        evidence_predicate="same-verification",
        provider_lineage=lineage(),
        provider_routing=routing(),
        provider_resources=(resource("ga"),resource("other")),
        executor_provider_bindings=(
            ExecutorProviderBinding("github_actions",("ga",)),
        ),
    )
    assert decision.selected_executor_id=="github_actions"
    assert decision.selected_resource_id=="ga"
    assert decision.provider_route.selected_provider_id=="github"
    assert decision.ready_for_existing_admission is True
    assert decision.provider_route.authority_created is False
    assert decision.provider_route.execution_authorized is False


def test_unavailable_bound_provider_fails_closed_after_valid_substitution():
    decision=compose_symbiotic_route(
        envelope=envelope(),
        work=work(),
        executors=(executor("github_actions"),),
        evidence_predicate="same-verification",
        provider_lineage=lineage(),
        provider_routing=routing(),
        provider_resources=(resource("ga",ResourceDisposition.UNAVAILABLE),),
        executor_provider_bindings=(
            ExecutorProviderBinding("github_actions",("ga",)),
        ),
    )
    assert decision.selected_executor_id=="github_actions"
    assert decision.selected_resource_id is None
    assert decision.ready_for_existing_admission is False
    assert "fail_closed" in decision.reasons


def test_work_sparse_human_gate_short_circuits_pse_and_provider_routing():
    decision=compose_symbiotic_route(
        envelope=envelope(),
        work=work(requested_actions=("merge_main",)),
        executors=(executor("github_actions"),),
        evidence_predicate="same-verification",
        provider_lineage=lineage(),
        provider_routing=routing(),
        provider_resources=(resource("ga"),),
        executor_provider_bindings=(ExecutorProviderBinding("github_actions",("ga",)),),
    )
    assert decision.work_sparse.disposition=="HUMAN_GATE"
    assert decision.substitution is None
    assert decision.provider_route is None
    assert decision.ready_for_existing_admission is False


def test_provider_bound_executor_requires_exact_lineage_capability_binding():
    bad=InternalLineageBinding(
        work_id="internal-hsr",
        portfolio_ref="portfolio://hsr",
        source_revision="candidate",
        authority_ref=AUTH,
        required_capabilities=("repo_read",),
        input_artifact_digests=(DIG("input"),),
        output_contract_digest=DIG("output"),
    )
    with pytest.raises(HolisticSymbiosisError):
        compose_symbiotic_route(
            envelope=envelope(),
            work=work(),
            executors=(executor("github_actions"),),
            evidence_predicate="same-verification",
            provider_lineage=bad,
            provider_routing=routing(),
            provider_resources=(resource("ga"),),
            executor_provider_bindings=(ExecutorProviderBinding("github_actions",("ga",)),),
        )


def test_independent_assurance_is_twin_reconciliation_not_promotion_authority():
    primary=VerificationObservation(
        verifier_id="general-execution",
        materialization_id="ge-run",
        predicate_digest=DIG("same-claim"),
        verdict=VerificationVerdict.PASS,
        evidence_digest=DIG("ge-evidence"),
    )
    twin=VerificationObservation(
        verifier_id="build-colony",
        materialization_id="bc-run",
        predicate_digest=DIG("same-claim"),
        verdict=VerificationVerdict.PASS,
        evidence_digest=DIG("bc-evidence"),
    )
    result=reconcile_independent_assurance(primary,twin)
    assert result.status=="AGREEMENT_PASS"
    assert result.promotable is True
    assert result.authority_created is False


def test_paid_or_work_only_method_does_not_bypass_existing_zero_budget():
    decision=compose_symbiotic_route(
        envelope=envelope(max_work_invocations=0,max_paid_spend_cents=0),
        work=work(),
        executors=(
            executor("work",work=True,cost=0),
            executor("paid",paid=True,cost=0,cents=1),
        ),
        evidence_predicate="same-verification",
        usage=ControllerUsage(),
    )
    assert decision.work_sparse.disposition=="CONDITION_WAIT"
    assert decision.ready_for_existing_admission is False
    assert decision.substitution is None
