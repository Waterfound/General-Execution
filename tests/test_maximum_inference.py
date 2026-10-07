import pytest

from general_execution.maximum_inference import (
    InferenceDisposition,
    InterpretationRule,
    MaximumInferenceEnvelope,
    MaximumInferenceError,
    PredictionBand,
    assess_maximum_inference,
)


def envelope(**overrides):
    values = {
        "test_ref": "physical://fae/device-class/mobile-arm",
        "target_uncertainty": "sustained throughput and thermal coexistence under ordinary use",
        "evidence_predicate": "device remains inside the predicted throughput/thermal envelope",
        "model_ids": ("analytic-v1", "simulation-v2"),
        "assumption_refs": ("assumption://power-envelope", "assumption://thermal-transfer"),
        "predictions": (
            PredictionBand(
                metric="throughput_hps",
                low=90.0,
                nominal=100.0,
                high=115.0,
                unit="H/s",
                confidence_basis="analytic plus simulated envelope",
            ),
        ),
        "sensitivity_factors": ("ambient-temperature", "scheduler-contention"),
        "counterfactuals": ("memory-bound hypothesis false",),
        "failure_signatures": ("throughput below lower envelope with sustained power headroom",),
        "discriminating_measurements": ("wall power", "device temperature", "sustained throughput"),
        "reality_gap": ("real-device thermal throttling and OS scheduling interaction",),
        "material_reality_gap": True,
        "interpretation_rules": (
            InterpretationRule(
                rule_id="within-envelope",
                observed_condition="all primary measurements remain within precommitted bands",
                interpretation="premise strengthened but still only empirically validated by the physical observation",
            ),
            InterpretationRule(
                rule_id="outside-envelope",
                observed_condition="one or more primary measurements fall outside precommitted bands",
                interpretation="inference model requires reconciliation before further promotion",
            ),
        ),
        "substrate_refs": ("pse://predictive-precomputation", "pse://independent-verification-twin"),
    }
    values.update(overrides)
    return MaximumInferenceEnvelope(**values)


def test_physical_test_remains_justified_only_after_strict_inference():
    result = assess_maximum_inference(
        envelope(),
        expected_information_gain_bp=4_000,
        minimum_information_gain_bp=1_000,
    )
    assert result.disposition is InferenceDisposition.PHYSICAL_TEST_REMAINS_JUSTIFIED
    assert result.strict_ready
    assert result.interpretation_precommitted
    assert not result.empirical_authority_created
    assert not result.physical_execution_triggered


def test_low_information_gain_returns_to_robust_premise():
    result = assess_maximum_inference(
        envelope(),
        expected_information_gain_bp=500,
        minimum_information_gain_bp=1_000,
    )
    assert result.disposition is InferenceDisposition.RETURN_TO_ROBUST_PREMISE_REVIEW


def test_no_material_reality_gap_returns_to_robust_premise():
    result = assess_maximum_inference(
        envelope(material_reality_gap=False),
        expected_information_gain_bp=8_000,
    )
    assert result.disposition is InferenceDisposition.RETURN_TO_ROBUST_PREMISE_REVIEW


def test_single_model_is_not_maximum_inference_ready():
    result = assess_maximum_inference(
        envelope(model_ids=("analytic-v1",)),
        expected_information_gain_bp=8_000,
    )
    assert result.disposition is InferenceDisposition.INFERENCE_INSUFFICIENT
    assert not result.strict_ready


def test_missing_precommitted_interpretation_is_not_ready():
    result = assess_maximum_inference(
        envelope(interpretation_rules=()),
        expected_information_gain_bp=8_000,
    )
    assert result.disposition is InferenceDisposition.INFERENCE_INSUFFICIENT


def test_inference_cannot_claim_empirical_validation():
    with pytest.raises(MaximumInferenceError, match="cannot claim empirical validation"):
        envelope(empirical_validation_claimed=True)


def test_inference_cannot_trigger_physical_execution_or_create_authority():
    with pytest.raises(MaximumInferenceError, match="cannot create authority or trigger execution"):
        envelope(authority_created=True)
    with pytest.raises(MaximumInferenceError, match="cannot create authority or trigger execution"):
        envelope(execution_triggered=True)


def test_prediction_band_is_ordered():
    with pytest.raises(MaximumInferenceError, match="low <= nominal <= high"):
        PredictionBand(
            metric="power",
            low=10.0,
            nominal=5.0,
            high=8.0,
            unit="W",
            confidence_basis="invalid fixture",
        )


def test_digest_is_deterministic():
    assert envelope().digest == envelope().digest
