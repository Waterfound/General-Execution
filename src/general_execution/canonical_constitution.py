from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id
from .execution_launch_admission import (
    ExecutionLaunchOrder,
    ExecutionLaunchReceipt,
    LaunchAdmissionResult,
    admit_or_replay_execution_launch,
)

ASSESSMENT_SCHEMA = "ge.canonical-constitution-assessment.v1"
ADMISSION_SCHEMA = "ge.canonical-constitution-admission.v1"

CANONICAL_CONSTITUTION_ID = "catechism-catholic-church-john-paul-ii"
CANONICAL_CONSTITUTION_REPOSITORY = "Waterfound/Systems"
CANONICAL_CONSTITUTION_REVISION = "83cf114d080c0bdb14f51b69efd753fa685ea434"
CANONICAL_CONSTITUTION_ARTIFACT_PATH = "constitution/canonical-constitution.v1.json"

ConstitutionalDisposition = Literal[
    "OUT_OF_SCOPE",
    "COMPATIBLE",
    "INTERPRETATION_REQUIRED",
    "INCOMPATIBLE",
]
ConstitutionalAdmissionDisposition = Literal[
    "ADMITTED",
    "INTERPRETATION_GATE",
    "REJECTED",
]

VALID_CONSTITUTIONAL_DISPOSITIONS = {
    "OUT_OF_SCOPE",
    "COMPATIBLE",
    "INTERPRETATION_REQUIRED",
    "INCOMPATIBLE",
}
VALID_ADMISSION_DISPOSITIONS = {
    "ADMITTED",
    "INTERPRETATION_GATE",
    "REJECTED",
}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


class CanonicalConstitutionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalConstitutionError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise CanonicalConstitutionError(f"{name} must be sha256:<64-hex>")


def _unique_sorted(name: str, values: tuple[str, ...]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise CanonicalConstitutionError(f"{name} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise CanonicalConstitutionError(f"{name} must not contain duplicates")
    if values != tuple(sorted(values)):
        raise CanonicalConstitutionError(f"{name} must be canonical-sorted")


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CanonicalConstitutionError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise CanonicalConstitutionError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class ConstitutionalAssessment:
    workstream_id: str
    subject_digest: str
    disposition: ConstitutionalDisposition
    basis_refs: tuple[str, ...]
    reason: str
    assessor: str
    assessment_ref: str
    constitution_id: str = CANONICAL_CONSTITUTION_ID
    constitution_repository: str = CANONICAL_CONSTITUTION_REPOSITORY
    constitution_revision: str = CANONICAL_CONSTITUTION_REVISION
    constitution_artifact_path: str = CANONICAL_CONSTITUTION_ARTIFACT_PATH
    schema_version: str = ASSESSMENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ASSESSMENT_SCHEMA:
            raise CanonicalConstitutionError("unsupported constitutional assessment schema")
        for name in ("workstream_id", "reason", "assessor", "assessment_ref"):
            _nonempty(name, getattr(self, name))
        _digest("subject_digest", self.subject_digest)
        if self.disposition not in VALID_CONSTITUTIONAL_DISPOSITIONS:
            raise CanonicalConstitutionError("unsupported constitutional disposition")
        _unique_sorted("basis_refs", self.basis_refs)

        if self.constitution_id != CANONICAL_CONSTITUTION_ID:
            raise CanonicalConstitutionError("constitutional identity mismatch")
        if self.constitution_repository != CANONICAL_CONSTITUTION_REPOSITORY:
            raise CanonicalConstitutionError("constitutional repository mismatch")
        if not REVISION_RE.fullmatch(self.constitution_revision):
            raise CanonicalConstitutionError("constitution_revision must be a commit SHA")
        if self.constitution_revision != CANONICAL_CONSTITUTION_REVISION:
            raise CanonicalConstitutionError("constitutional revision mismatch")
        if self.constitution_artifact_path != CANONICAL_CONSTITUTION_ARTIFACT_PATH:
            raise CanonicalConstitutionError("constitutional artifact path mismatch")

        if self.disposition != "OUT_OF_SCOPE" and not self.basis_refs:
            raise CanonicalConstitutionError(
                "material constitutional dispositions require basis_refs"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ConstitutionalAdmissionReceipt:
    receipt_id: str
    assessment_digest: str
    workstream_id: str
    subject_digest: str
    constitutional_disposition: ConstitutionalDisposition
    admission_disposition: ConstitutionalAdmissionDisposition
    admission_reason: str
    basis_refs: tuple[str, ...]
    constitution_id: str
    constitution_repository: str
    constitution_revision: str
    constitution_artifact_path: str
    constitutional_gate_passed: bool
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ADMISSION_SCHEMA:
            raise CanonicalConstitutionError("unsupported constitutional admission schema")
        for name in (
            "receipt_id",
            "workstream_id",
            "admission_reason",
            "constitution_id",
            "constitution_repository",
            "constitution_artifact_path",
        ):
            _nonempty(name, getattr(self, name))
        _digest("assessment_digest", self.assessment_digest)
        _digest("subject_digest", self.subject_digest)
        _unique_sorted("basis_refs", self.basis_refs)
        if self.constitutional_disposition not in VALID_CONSTITUTIONAL_DISPOSITIONS:
            raise CanonicalConstitutionError("unsupported constitutional disposition")
        if self.admission_disposition not in VALID_ADMISSION_DISPOSITIONS:
            raise CanonicalConstitutionError("unsupported constitutional admission disposition")
        if self.constitution_revision != CANONICAL_CONSTITUTION_REVISION:
            raise CanonicalConstitutionError("constitutional revision mismatch")
        if self.authority_created or self.execution_triggered:
            raise CanonicalConstitutionError(
                "constitutional gate cannot create authority or trigger execution"
            )
        if self.constitutional_gate_passed != (
            self.admission_disposition == "ADMITTED"
        ):
            raise CanonicalConstitutionError("constitutional gate pass flag mismatch")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ConstitutionallyGovernedLaunchResult:
    constitutional_receipt: ConstitutionalAdmissionReceipt
    launch_result: LaunchAdmissionResult | None


def admit_constitutional_assessment(
    assessment: ConstitutionalAssessment,
) -> ConstitutionalAdmissionReceipt:
    if assessment.disposition in {"OUT_OF_SCOPE", "COMPATIBLE"}:
        admission_disposition: ConstitutionalAdmissionDisposition = "ADMITTED"
        reason = (
            "constitutional_scope_not_material"
            if assessment.disposition == "OUT_OF_SCOPE"
            else "constitutional_compatibility_established"
        )
    elif assessment.disposition == "INTERPRETATION_REQUIRED":
        admission_disposition = "INTERPRETATION_GATE"
        reason = "material_constitutional_interpretation_unresolved"
    else:
        admission_disposition = "REJECTED"
        reason = "constitutionally_incompatible"

    identity = {
        "assessment_digest": assessment.digest,
        "admission_disposition": admission_disposition,
        "admission_reason": reason,
        "constitution_revision": assessment.constitution_revision,
    }

    return ConstitutionalAdmissionReceipt(
        receipt_id=stable_id("geccr", identity),
        assessment_digest=assessment.digest,
        workstream_id=assessment.workstream_id,
        subject_digest=assessment.subject_digest,
        constitutional_disposition=assessment.disposition,
        admission_disposition=admission_disposition,
        admission_reason=reason,
        basis_refs=assessment.basis_refs,
        constitution_id=assessment.constitution_id,
        constitution_repository=assessment.constitution_repository,
        constitution_revision=assessment.constitution_revision,
        constitution_artifact_path=assessment.constitution_artifact_path,
        constitutional_gate_passed=admission_disposition == "ADMITTED",
    )


def admit_constitutionally_governed_launch(
    order: ExecutionLaunchOrder,
    assessment: ConstitutionalAssessment,
    *,
    authenticated_order_digest: str,
    authenticated_actor: str,
    existing_launch_receipt: ExecutionLaunchReceipt | None = None,
) -> ConstitutionallyGovernedLaunchResult:
    if assessment.workstream_id != order.workstream_id:
        raise CanonicalConstitutionError(
            "constitutional assessment belongs to another workstream"
        )
    if assessment.subject_digest != order.digest:
        raise CanonicalConstitutionError(
            "constitutional assessment does not bind the exact execution order"
        )

    constitutional_receipt = admit_constitutional_assessment(assessment)
    if constitutional_receipt.admission_disposition != "ADMITTED":
        return ConstitutionallyGovernedLaunchResult(
            constitutional_receipt=constitutional_receipt,
            launch_result=None,
        )

    launch_result = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=authenticated_order_digest,
        authenticated_actor=authenticated_actor,
        existing_receipt=existing_launch_receipt,
    )
    return ConstitutionallyGovernedLaunchResult(
        constitutional_receipt=constitutional_receipt,
        launch_result=launch_result,
    )


def constitutional_assessment_from_dict(data: Any) -> ConstitutionalAssessment:
    obj = _exact(
        data,
        {
            "workstream_id",
            "subject_digest",
            "disposition",
            "basis_refs",
            "reason",
            "assessor",
            "assessment_ref",
            "constitution_id",
            "constitution_repository",
            "constitution_revision",
            "constitution_artifact_path",
            "schema_version",
        },
        "constitutional assessment",
    )
    if not isinstance(obj["basis_refs"], list):
        raise CanonicalConstitutionError("basis_refs must be a list")
    return ConstitutionalAssessment(
        workstream_id=obj["workstream_id"],
        subject_digest=obj["subject_digest"],
        disposition=obj["disposition"],
        basis_refs=tuple(obj["basis_refs"]),
        reason=obj["reason"],
        assessor=obj["assessor"],
        assessment_ref=obj["assessment_ref"],
        constitution_id=obj["constitution_id"],
        constitution_repository=obj["constitution_repository"],
        constitution_revision=obj["constitution_revision"],
        constitution_artifact_path=obj["constitution_artifact_path"],
        schema_version=obj["schema_version"],
    )


def constitutional_admission_receipt_from_dict(
    data: Any,
) -> ConstitutionalAdmissionReceipt:
    obj = _exact(
        data,
        {
            "receipt_id",
            "assessment_digest",
            "workstream_id",
            "subject_digest",
            "constitutional_disposition",
            "admission_disposition",
            "admission_reason",
            "basis_refs",
            "constitution_id",
            "constitution_repository",
            "constitution_revision",
            "constitution_artifact_path",
            "constitutional_gate_passed",
            "authority_created",
            "execution_triggered",
            "schema_version",
        },
        "constitutional admission receipt",
    )
    if not isinstance(obj["basis_refs"], list):
        raise CanonicalConstitutionError("basis_refs must be a list")
    return ConstitutionalAdmissionReceipt(
        **{**obj, "basis_refs": tuple(obj["basis_refs"])}
    )


def constitutional_assessment_to_dict(
    assessment: ConstitutionalAssessment,
) -> dict[str, Any]:
    return json.loads(canonical_json(assessment))


def constitutional_admission_receipt_to_dict(
    receipt: ConstitutionalAdmissionReceipt,
) -> dict[str, Any]:
    return json.loads(canonical_json(receipt))
