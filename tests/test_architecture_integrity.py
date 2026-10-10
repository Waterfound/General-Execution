from __future__ import annotations

import pytest

from general_execution.architecture_integrity import (
    ActivationState,
    ArchitectureClass,
    ArchitectureComponentProjection,
    ArchitectureIntegrityError,
    ArchitectureMode,
    ArchitectureRelationProjection,
    ArchitectureState,
    ImplementationState,
    RelationType,
    receipt_to_dict,
    verify_architecture_projection,
)

PROJECTION = "p_aaaaaaaaaaaaaaaa"
REGISTRY = "sha256:" + "1" * 64
AUTH = "sha256:" + "2" * 64


def component(
    component_id,
    *,
    owner_id="o_aaaaaaaaaaaaaaaa",
    classification=ArchitectureClass.PROTOCOL,
    modes=(ArchitectureMode.ADVISORY,),
    architecture=ArchitectureState.CANONICAL,
    implementation=ImplementationState.IMPLEMENTED,
    activation=ActivationState.ACTIVE,
    execution=False,
    mutation=False,
    native_owner=False,
    native_semantics=False,
    justified=False,
    projection=PROJECTION,
    registry=REGISTRY,
):
    return ArchitectureComponentProjection(
        component_id=component_id,
        owner_id=owner_id,
        classification=classification,
        modes=modes,
        architecture_state=architecture,
        implementation_state=implementation,
        activation_state=activation,
        projection_id=projection,
        registry_revision_digest=registry,
        authority_ceiling_digest=AUTH,
        execution_capable=execution,
        target_mutation_capable=mutation,
        independent_native_owner=native_owner,
        native_state_or_semantics_owned=native_semantics,
        has_system_justification=justified,
    )


def relation(source, kind, target, *, projection=PROJECTION, registry=REGISTRY):
    return ArchitectureRelationProjection(
        source_id=source,
        relation_type=kind,
        target_id=target,
        projection_id=projection,
        registry_revision_digest=registry,
    )


def test_valid_opaque_projection_passes_without_private_semantics():
    system = component(
        "c_1111111111111111",
        classification=ArchitectureClass.SYSTEM,
        modes=(ArchitectureMode.ADVISORY, ArchitectureMode.REAL_RUN),
        execution=True,
        mutation=True,
        native_owner=True,
        native_semantics=True,
        justified=True,
    )
    protocol = component(
        "c_2222222222222222",
        classification=ArchitectureClass.PROTOCOL,
        activation=ActivationState.GATED,
        architecture=ArchitectureState.CANDIDATE,
        implementation=ImplementationState.CANDIDATE,
    )
    receipt = verify_architecture_projection(
        (system, protocol),
        (relation(
            "c_2222222222222222",
            RelationType.SELECTS,
            "c_1111111111111111",
        ),),
    )
    data = receipt_to_dict(receipt)
    assert data["verdict"] == "PASS"
    assert data["component_count"] == 2
    assert data["relation_count"] == 1
    assert data["system_count"] == 1
    assert data["executable_count"] == 1
    assert data["authority_created"] is False
    assert data["execution_triggered"] is False
    assert "name" not in data


def test_system_requires_independent_owner_and_justification():
    with pytest.raises(ArchitectureIntegrityError, match="independent native owner"):
        component(
            "c_1111111111111111",
            classification=ArchitectureClass.SYSTEM,
            native_owner=False,
            native_semantics=True,
            justified=True,
        )

    with pytest.raises(ArchitectureIntegrityError, match="anti-proliferation justification"):
        component(
            "c_1111111111111111",
            classification=ArchitectureClass.SYSTEM,
            native_owner=True,
            native_semantics=True,
            justified=False,
        )


def test_non_system_cannot_claim_system_ownership():
    with pytest.raises(ArchitectureIntegrityError, match="non-System"):
        component(
            "c_1111111111111111",
            classification=ArchitectureClass.CROSS_CUTTING_CAPABILITY,
            native_owner=True,
        )


def test_candidate_architecture_cannot_claim_active_activation():
    with pytest.raises(ArchitectureIntegrityError, match="candidate architecture"):
        component(
            "c_1111111111111111",
            architecture=ArchitectureState.CANDIDATE,
            implementation=ImplementationState.CANDIDATE,
            activation=ActivationState.ACTIVE,
        )


def test_active_executor_requires_real_implementation():
    with pytest.raises(ArchitectureIntegrityError, match="requires implementation"):
        component(
            "c_1111111111111111",
            classification=ArchitectureClass.SYSTEM_CAPABILITY,
            execution=True,
            implementation=ImplementationState.NOT_APPLICABLE,
            activation=ActivationState.ACTIVE,
        )


def test_private_semantic_identifier_is_rejected_as_public_component_id():
    with pytest.raises(ArchitectureIntegrityError, match="opaque c_<16-hex>"):
        component("wf.sys.example")


def test_stable_or_non_decision_scoped_alias_is_rejected():
    with pytest.raises(ArchitectureIntegrityError, match="fresh decision-scoped"):
        ArchitectureComponentProjection(
            component_id="c_1111111111111111",
            owner_id="o_1111111111111111",
            classification=ArchitectureClass.PROTOCOL,
            modes=(ArchitectureMode.ADVISORY,),
            architecture_state=ArchitectureState.CANONICAL,
            implementation_state=ImplementationState.IMPLEMENTED,
            activation_state=ActivationState.ACTIVE,
            projection_id=PROJECTION,
            registry_revision_digest=REGISTRY,
            authority_ceiling_digest=AUTH,
            decision_scoped=False,
        )
    with pytest.raises(ArchitectureIntegrityError, match="fresh decision-scoped"):
        ArchitectureComponentProjection(
            component_id="c_1111111111111111",
            owner_id="o_1111111111111111",
            classification=ArchitectureClass.PROTOCOL,
            modes=(ArchitectureMode.ADVISORY,),
            architecture_state=ArchitectureState.CANONICAL,
            implementation_state=ImplementationState.IMPLEMENTED,
            activation_state=ActivationState.ACTIVE,
            projection_id=PROJECTION,
            registry_revision_digest=REGISTRY,
            authority_ceiling_digest=AUTH,
            stable_alias=True,
        )


def test_mixed_projection_or_registry_revision_fails_closed():
    left = component("c_1111111111111111")
    right = component(
        "c_2222222222222222",
        projection="p_bbbbbbbbbbbbbbbb",
    )
    with pytest.raises(ArchitectureIntegrityError, match="one projection"):
        verify_architecture_projection((left, right), ())

    right = component(
        "c_2222222222222222",
        registry="sha256:" + "3" * 64,
    )
    with pytest.raises(ArchitectureIntegrityError, match="one projection"):
        verify_architecture_projection((left, right), ())


def test_unknown_relation_endpoint_fails_closed():
    item = component("c_1111111111111111")
    edge = relation(
        "c_1111111111111111",
        RelationType.HOSTS,
        "c_ffffffffffffffff",
    )
    with pytest.raises(ArchitectureIntegrityError, match="outside the projected"):
        verify_architecture_projection((item,), (edge,))


def test_relation_with_mismatched_projection_fails_closed():
    left = component("c_1111111111111111")
    right = component("c_2222222222222222")
    edge = relation(
        left.component_id,
        RelationType.VERIFIES,
        right.component_id,
        projection="p_bbbbbbbbbbbbbbbb",
    )
    with pytest.raises(ArchitectureIntegrityError, match="relation projection"):
        verify_architecture_projection((left, right), (edge,))
