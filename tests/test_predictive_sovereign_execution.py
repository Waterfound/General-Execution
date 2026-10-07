from general_execution.canonical import sha256_digest
from general_execution.predictive_sovereign_execution import (
    CapabilityMethod,
    GateCandidate,
    GateKind,
    PredictiveSovereignError,
    PredictiveTask,
    VerificationObservation,
    VerificationVerdict,
    build_precomputation_plan,
    build_recovery_capsule,
    forecast_gates,
    reconcile_verification_twin,
    select_capability_substitute,
)

import pytest


def d(value: str) -> str:
    return sha256_digest(value)


def test_predictive_precomputation_selects_only_reversible_gate_independent_work():
    tasks = (
        PredictiveTask("tests", "predicate:test"),
        PredictiveTask("reconcile", "predicate:reconcile", depends_on=("tests",)),
        PredictiveTask("merge", "predicate:merge", requires_authority=True),
        PredictiveTask("deploy", "predicate:deploy", irreversible=True),
        PredictiveTask(
            "post-merge",
            "predicate:post-merge",
            depends_on=("merge",),
            requires_observed_gate_outcome=True,
        ),
    )
    plan = build_precomputation_plan("authority://merge", tasks)
    assert plan.selected_task_ids == ("tests", "reconcile")
    assert set(plan.deferred_task_ids) == {"merge", "deploy", "post-merge"}
    assert plan.authority_created is False
    assert plan.execution_triggered is False


def test_precomputation_serializes_shared_state_keys():
    tasks = (
        PredictiveTask("a", "p:a", shared_state_keys=("canonical",)),
        PredictiveTask("b", "p:b", shared_state_keys=("canonical",)),
        PredictiveTask("c", "p:c", shared_state_keys=("other",)),
    )
    plan = build_precomputation_plan("gate://x", tasks)
    assert plan.waves[0] == ("a", "c")
    assert plan.waves[1] == ("b",)


def test_precomputation_rejects_unknown_dependency():
    with pytest.raises(PredictiveSovereignError):
        build_precomputation_plan(
            "gate://x",
            (PredictiveTask("a", "p", depends_on=("missing",)),),
        )


def test_recovery_capsule_is_secret_free_and_reconstructible():
    capsule = build_recovery_capsule(
        capsule_id="capsule-001",
        source_refs=("github://repo/commit/abc",),
        durable_state_digests=(d("state"),),
        authority_refs=("authority://waterfound/bounded",),
        resource_aliases=("canonical-source", "durable-runtime"),
        reconstruction_steps=("checkout source", "restore state", "verify digest"),
        verification_predicates=("state digest matches", "authority remains bounded"),
    )
    assert capsule.secret_material_persisted is False
    assert capsule.authority_created is False
    assert capsule.digest.startswith("sha256:")


def test_recovery_capsule_rejects_secret_material():
    with pytest.raises(PredictiveSovereignError):
        build_recovery_capsule(
            capsule_id="capsule-001",
            source_refs=("source",),
            durable_state_digests=(d("state"),),
            authority_refs=(),
            resource_aliases=(),
            reconstruction_steps=("restore",),
            verification_predicates=("verify",),
            secret_material=("token-value",),
        )


def test_gate_forecast_orders_near_human_gates_and_compiles_human_dependencies():
    forecast = forecast_gates(
        (
            GateCandidate(
                "gate://external",
                GateKind.EXTERNAL_EVIDENCE,
                2,
                "frontier-b",
                ("evidence://b",),
            ),
            GateCandidate(
                "authority://merge",
                GateKind.HUMAN_AUTHORITY,
                1,
                "frontier-a",
                ("evidence://a",),
                human_action_likely=True,
            ),
            GateCandidate(
                "gate://capacity",
                GateKind.CAPACITY,
                1,
                "frontier-c",
                ("evidence://c",),
            ),
        )
    )
    assert forecast.gates[0].gate_ref == "authority://merge"
    assert forecast.compilation_refs == ("authority://merge",)
    assert forecast.advisory_only is True


def obs(verifier, materialization, verdict, predicate="claim"):
    return VerificationObservation(
        verifier_id=verifier,
        materialization_id=materialization,
        predicate_digest=d(predicate),
        verdict=verdict,
        evidence_digest=d(f"{verifier}:{materialization}:{verdict.value}"),
    )


def test_independent_verification_twin_requires_two_independent_passes():
    result = reconcile_verification_twin(
        obs("primary", "m1", VerificationVerdict.PASS),
        obs("twin", "m2", VerificationVerdict.PASS),
    )
    assert result.status == "AGREEMENT_PASS"
    assert result.independent is True
    assert result.promotable is True
    assert result.authority_created is False


def test_verification_twin_disagreement_fails_closed():
    result = reconcile_verification_twin(
        obs("primary", "m1", VerificationVerdict.PASS),
        obs("twin", "m2", VerificationVerdict.FAIL),
    )
    assert result.status == "DISAGREEMENT"
    assert result.promotable is False


def test_verification_twin_same_materialization_is_not_independent():
    result = reconcile_verification_twin(
        obs("primary", "m1", VerificationVerdict.PASS),
        obs("twin", "m1", VerificationVerdict.PASS),
    )
    assert result.status == "NOT_INDEPENDENT"
    assert result.promotable is False


def test_verification_twin_predicate_mismatch_is_rejected():
    with pytest.raises(PredictiveSovereignError):
        reconcile_verification_twin(
            obs("primary", "m1", VerificationVerdict.PASS, "a"),
            obs("twin", "m2", VerificationVerdict.PASS, "b"),
        )


def method(
    method_id,
    predicates=("same-proof",),
    authorities=("authority://bounded",),
    cost=10,
    spend=0,
    available=True,
    quality=2,
):
    return CapabilityMethod(
        method_id=method_id,
        evidence_predicates=predicates,
        authority_refs=authorities,
        cost_rank=cost,
        paid_spend_cents=spend,
        available=available,
        evidence_quality_rank=quality,
    )


def test_capability_substitution_prefers_cheapest_equivalent_authorized_method():
    decision = select_capability_substitute(
        predicate="same-proof",
        methods=(
            method("browser-ui", cost=50),
            method("api", cost=5),
            method("paid-cloud", cost=1, spend=10),
        ),
        allowed_method_ids=("browser-ui", "api", "paid-cloud"),
        active_authority_refs=("authority://bounded",),
        max_paid_spend_cents=0,
        minimum_evidence_quality_rank=2,
    )
    assert decision.selected_method_id == "api"
    assert decision.evidence_predicate_preserved is True
    assert decision.execution_triggered is False


def test_capability_substitution_rejects_weaker_evidence():
    decision = select_capability_substitute(
        predicate="same-proof",
        methods=(method("cheap-but-weak", cost=1, quality=1),),
        allowed_method_ids=("cheap-but-weak",),
        active_authority_refs=("authority://bounded",),
        minimum_evidence_quality_rank=2,
    )
    assert decision.deferred is True
    assert decision.selected_method_id is None
    assert dict(decision.rejected)["cheap-but-weak"] == ("evidence_quality_insufficient",)


def test_capability_substitution_rejects_authority_widening():
    decision = select_capability_substitute(
        predicate="same-proof",
        methods=(
            method("needs-other-authority", authorities=("authority://other",)),
        ),
        allowed_method_ids=("needs-other-authority",),
        active_authority_refs=("authority://bounded",),
    )
    assert decision.deferred is True
    assert "authority_ref_not_active" in dict(decision.rejected)["needs-other-authority"]


def test_capability_substitution_rejects_non_equivalent_method():
    decision = select_capability_substitute(
        predicate="same-proof",
        methods=(method("different", predicates=("other-proof",)),),
        allowed_method_ids=("different",),
        active_authority_refs=("authority://bounded",),
    )
    assert decision.deferred is True
    assert "predicate_not_covered" in dict(decision.rejected)["different"]


def test_full_wave_properties_compose_without_authority_creation():
    plan = build_precomputation_plan(
        "authority://next",
        (
            PredictiveTask("prepare-tests", "predicate:test"),
            PredictiveTask("merge", "predicate:merge", requires_authority=True),
        ),
    )
    capsule = build_recovery_capsule(
        capsule_id="capsule",
        source_refs=("source://canonical",),
        durable_state_digests=(d("state"),),
        authority_refs=("authority://bounded",),
        resource_aliases=("canonical-source",),
        reconstruction_steps=("restore",),
        verification_predicates=("digest-match",),
    )
    forecast = forecast_gates(
        (
            GateCandidate(
                "authority://next",
                GateKind.HUMAN_AUTHORITY,
                1,
                "merge",
                ("evidence://candidate",),
                True,
            ),
        )
    )
    twin = reconcile_verification_twin(
        obs("primary", "m1", VerificationVerdict.PASS),
        obs("twin", "m2", VerificationVerdict.PASS),
    )
    substitution = select_capability_substitute(
        predicate="same-proof",
        methods=(method("local"),),
        allowed_method_ids=("local",),
        active_authority_refs=("authority://bounded",),
    )
    assert plan.authority_created is False
    assert capsule.authority_created is False
    assert forecast.authority_created is False
    assert twin.authority_created is False
    assert substitution.authority_created is False
