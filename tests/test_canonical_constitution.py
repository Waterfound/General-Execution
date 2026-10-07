import pytest

from general_execution.canonical import sha256_digest
from general_execution.canonical_constitution import (
    CANONICAL_CONSTITUTION_REVISION,
    CanonicalConstitutionError,
    ConstitutionalAssessment,
    admit_constitutional_assessment,
    admit_constitutionally_governed_launch,
)
from general_execution.execution_launch_admission import (
    ExecutionLaunchOrder,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
)


def authority(*scopes: str) -> LaunchAuthorityBinding:
    return LaunchAuthorityBinding(
        actor="Waterfound",
        authority_ref="authority://canonical-constitution/test",
        authority_boundary="Bounded test authority.",
        granted_scopes=tuple(sorted(scopes)),
    )


def executor() -> LaunchExecutorBinding:
    return LaunchExecutorBinding(
        executor="build_colony",
        availability="AVAILABLE",
        evidence_ref="executor://build_colony/capability",
        evidence_digest=sha256_digest({"executor": "build_colony", "available": True}),
    )


def order(objective: str = "Constitutionally governed test") -> ExecutionLaunchOrder:
    return ExecutionLaunchOrder(
        workstream_id="canonical-constitution-test",
        owner="engineering",
        repository="Waterfound/General-Execution",
        executor="build_colony",
        objective=objective,
        order_ref="order://canonical-constitution-test",
        source_revision="1" * 40,
        required_authority_scopes=("candidate_write",),
        authority=authority("candidate_write"),
        executor_binding=executor(),
    )


def assessment(
    value: ExecutionLaunchOrder,
    disposition: str,
    *,
    basis_refs: tuple[str, ...] | None = None,
) -> ConstitutionalAssessment:
    if basis_refs is None:
        basis_refs = () if disposition == "OUT_OF_SCOPE" else ("CCC:1750",)
    return ConstitutionalAssessment(
        workstream_id=value.workstream_id,
        subject_digest=value.digest,
        disposition=disposition,
        basis_refs=tuple(sorted(basis_refs)),
        reason=f"test disposition {disposition}",
        assessor="project-assurance/test",
        assessment_ref="assessment://canonical-constitution-test",
    )


def governed(value, a):
    return admit_constitutionally_governed_launch(
        value,
        a,
        authenticated_order_digest=value.digest,
        authenticated_actor="Waterfound",
    )


def test_out_of_scope_reaches_normal_launch_admission():
    value = order()
    result = governed(value, assessment(value, "OUT_OF_SCOPE"))
    assert result.constitutional_receipt.admission_disposition == "ADMITTED"
    assert result.launch_result is not None
    assert result.launch_result.receipt.disposition == "ADMITTED"


def test_compatible_reaches_normal_launch_admission():
    value = order()
    result = governed(value, assessment(value, "COMPATIBLE"))
    assert result.constitutional_receipt.admission_disposition == "ADMITTED"
    assert result.launch_result is not None
    assert result.launch_result.receipt.disposition == "ADMITTED"


def test_interpretation_required_stops_before_launch():
    value = order()
    result = governed(value, assessment(value, "INTERPRETATION_REQUIRED"))
    assert result.constitutional_receipt.admission_disposition == "INTERPRETATION_GATE"
    assert result.constitutional_receipt.constitutional_gate_passed is False
    assert result.launch_result is None
    assert result.constitutional_receipt.execution_triggered is False


def test_incompatible_is_rejected_even_with_full_normal_authority():
    value = order()
    result = governed(value, assessment(value, "INCOMPATIBLE"))
    assert result.constitutional_receipt.admission_disposition == "REJECTED"
    assert result.launch_result is None
    assert result.constitutional_receipt.authority_created is False


def test_assessment_cannot_be_reused_after_order_change():
    first = order("first objective")
    a = assessment(first, "COMPATIBLE")
    changed = order("changed objective")
    with pytest.raises(
        CanonicalConstitutionError,
        match="does not bind the exact execution order",
    ):
        governed(changed, a)


def test_material_disposition_requires_basis_refs():
    value = order()
    with pytest.raises(
        CanonicalConstitutionError,
        match="material constitutional dispositions require basis_refs",
    ):
        assessment(value, "COMPATIBLE", basis_refs=())


def test_wrong_constitution_revision_fails_closed():
    value = order()
    with pytest.raises(
        CanonicalConstitutionError,
        match="constitutional revision mismatch",
    ):
        ConstitutionalAssessment(
            workstream_id=value.workstream_id,
            subject_digest=value.digest,
            disposition="COMPATIBLE",
            basis_refs=("CCC:1750",),
            reason="wrong revision",
            assessor="test",
            assessment_ref="assessment://wrong-revision",
            constitution_revision="2" * 40,
        )


def test_constitutional_receipt_is_deterministic_and_non_authorizing():
    value = order()
    a = assessment(value, "COMPATIBLE")
    first = admit_constitutional_assessment(a)
    second = admit_constitutional_assessment(a)
    assert first == second
    assert first.constitution_revision == CANONICAL_CONSTITUTION_REVISION
    assert first.authority_created is False
    assert first.execution_triggered is False
