from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Iterable

from .canonical import sha256_digest

MAXIMUM_INFERENCE_SCHEMA = "ge.maximum-inference-envelope.v1"
MAXIMUM_INFERENCE_ASSESSMENT_SCHEMA = "ge.maximum-inference-assessment.v1"


class MaximumInferenceError(ValueError):
    pass


class InferenceDisposition(str, Enum):
    INFERENCE_INSUFFICIENT = "INFERENCE_INSUFFICIENT"
    RETURN_TO_ROBUST_PREMISE_REVIEW = "RETURN_TO_ROBUST_PREMISE_REVIEW"
    PHYSICAL_TEST_REMAINS_JUSTIFIED = "PHYSICAL_TEST_REMAINS_JUSTIFIED"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaximumInferenceError(f"{field} must be a non-empty string")
    return value.strip()


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise MaximumInferenceError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise MaximumInferenceError(f"{field} must not contain duplicates")
    return items


def _basis_points(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise MaximumInferenceError(f"{field} must be an integer from 0 to 10000")
    return value


@dataclass(frozen=True, slots=True)
class PredictionBand:
    metric: str
    low: float
    nominal: float
    high: float
    unit: str
    confidence_basis: str

    def __post_init__(self) -> None:
        _nonempty(self.metric, "metric")
        _nonempty(self.unit, "unit")
        _nonempty(self.confidence_basis, "confidence_basis")
        values = (self.low, self.nominal, self.high)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in values):
            raise MaximumInferenceError("prediction values must be finite numbers")
        if not self.low <= self.nominal <= self.high:
            raise MaximumInferenceError("prediction band must satisfy low <= nominal <= high")


@dataclass(frozen=True, slots=True)
class InterpretationRule:
    rule_id: str
    observed_condition: str
    interpretation: str

    def __post_init__(self) -> None:
        _nonempty(self.rule_id, "rule_id")
        _nonempty(self.observed_condition, "observed_condition")
        _nonempty(self.interpretation, "interpretation")


@dataclass(frozen=True, slots=True)
class MaximumInferenceEnvelope:
    test_ref: str
    target_uncertainty: str
    evidence_predicate: str
    model_ids: tuple[str, ...]
    assumption_refs: tuple[str, ...]
    predictions: tuple[PredictionBand, ...]
    sensitivity_factors: tuple[str, ...]
    counterfactuals: tuple[str, ...]
    failure_signatures: tuple[str, ...]
    discriminating_measurements: tuple[str, ...]
    reality_gap: tuple[str, ...]
    material_reality_gap: bool
    interpretation_rules: tuple[InterpretationRule, ...]
    substrate_refs: tuple[str, ...]
    simulation_evidence_only: bool = True
    empirical_validation_claimed: bool = False
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = MAXIMUM_INFERENCE_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.test_ref, "test_ref")
        _nonempty(self.target_uncertainty, "target_uncertainty")
        _nonempty(self.evidence_predicate, "evidence_predicate")
        _unique(self.model_ids, "model_ids", allow_empty=False)
        _unique(self.assumption_refs, "assumption_refs", allow_empty=False)
        _unique(self.sensitivity_factors, "sensitivity_factors")
        _unique(self.counterfactuals, "counterfactuals")
        _unique(self.failure_signatures, "failure_signatures")
        _unique(self.discriminating_measurements, "discriminating_measurements")
        _unique(self.reality_gap, "reality_gap", allow_empty=False)
        _unique(self.substrate_refs, "substrate_refs", allow_empty=False)

        prediction_metrics = tuple(item.metric for item in self.predictions)
        if not self.predictions:
            raise MaximumInferenceError("predictions cannot be empty")
        if len(prediction_metrics) != len(set(prediction_metrics)):
            raise MaximumInferenceError("prediction metrics must be unique")

        rule_ids = tuple(item.rule_id for item in self.interpretation_rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise MaximumInferenceError("interpretation rule ids must be unique")

        if not isinstance(self.material_reality_gap, bool):
            raise MaximumInferenceError("material_reality_gap must be boolean")
        if not self.simulation_evidence_only:
            raise MaximumInferenceError("Maximum Inference evidence must remain simulation/inference evidence")
        if self.empirical_validation_claimed:
            raise MaximumInferenceError("inference cannot claim empirical validation")
        if self.authority_created or self.execution_triggered:
            raise MaximumInferenceError("Maximum Inference cannot create authority or trigger execution")

    @property
    def strict_ready(self) -> bool:
        return (
            len(self.model_ids) >= 2
            and bool(self.counterfactuals)
            and bool(self.failure_signatures)
            and bool(self.discriminating_measurements)
            and bool(self.interpretation_rules)
        )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class MaximumInferenceAssessment:
    envelope_digest: str
    expected_information_gain_bp: int
    minimum_information_gain_bp: int
    strict_ready: bool
    material_reality_gap: bool
    disposition: InferenceDisposition
    reason: str
    interpretation_precommitted: bool
    empirical_authority_created: bool = False
    physical_execution_triggered: bool = False
    schema_version: str = MAXIMUM_INFERENCE_ASSESSMENT_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.envelope_digest, "envelope_digest")
        _basis_points(self.expected_information_gain_bp, "expected_information_gain_bp")
        _basis_points(self.minimum_information_gain_bp, "minimum_information_gain_bp")
        _nonempty(self.reason, "reason")
        if self.empirical_authority_created or self.physical_execution_triggered:
            raise MaximumInferenceError("assessment cannot create empirical authority or trigger physical execution")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def assess_maximum_inference(
    envelope: MaximumInferenceEnvelope,
    *,
    expected_information_gain_bp: int,
    minimum_information_gain_bp: int = 1_000,
) -> MaximumInferenceAssessment:
    information_gain = _basis_points(expected_information_gain_bp, "expected_information_gain_bp")
    minimum_gain = _basis_points(minimum_information_gain_bp, "minimum_information_gain_bp")

    if not envelope.strict_ready:
        disposition = InferenceDisposition.INFERENCE_INSUFFICIENT
        reason = "maximum-inference package has not reached the strict pre-empirical readiness floor"
    elif not envelope.material_reality_gap:
        disposition = InferenceDisposition.RETURN_TO_ROBUST_PREMISE_REVIEW
        reason = "no material reality gap remains after inference; physical necessity must be reconsidered"
    elif information_gain < minimum_gain:
        disposition = InferenceDisposition.RETURN_TO_ROBUST_PREMISE_REVIEW
        reason = "residual physical information gain is below the precommitted threshold"
    else:
        disposition = InferenceDisposition.PHYSICAL_TEST_REMAINS_JUSTIFIED
        reason = "a material reality gap remains and expected physical information gain meets the threshold"

    return MaximumInferenceAssessment(
        envelope_digest=envelope.digest,
        expected_information_gain_bp=information_gain,
        minimum_information_gain_bp=minimum_gain,
        strict_ready=envelope.strict_ready,
        material_reality_gap=envelope.material_reality_gap,
        disposition=disposition,
        reason=reason,
        interpretation_precommitted=bool(envelope.interpretation_rules),
    )
