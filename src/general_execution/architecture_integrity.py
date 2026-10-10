from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any

from .canonical import sha256_digest

COMPONENT_SCHEMA = "ge.architecture-component-projection.v1"
RELATION_SCHEMA = "ge.architecture-relation-projection.v1"
RECEIPT_SCHEMA = "ge.architecture-integrity-receipt.v1"


class ArchitectureIntegrityError(ValueError):
    pass


class ArchitectureClass(str, Enum):
    NORMATIVE_BOUNDARY = "NORMATIVE_BOUNDARY"
    SYSTEM = "SYSTEM"
    SYSTEM_CAPABILITY = "SYSTEM_CAPABILITY"
    PROTOCOL = "PROTOCOL"
    PRIVATE_PROTOCOL = "PRIVATE_PROTOCOL"
    THIN_PROTOCOL = "THIN_PROTOCOL"
    CONTRACT = "CONTRACT"
    SELECTION_CAPABILITY = "SELECTION_CAPABILITY"
    PORTFOLIO_MODEL = "PORTFOLIO_MODEL"
    AUTHORITY_BOUNDARY_MECHANISM = "AUTHORITY_BOUNDARY_MECHANISM"
    CONTINUATION_PATTERN = "CONTINUATION_PATTERN"
    RUNTIME_ADOPTION_PATTERN = "RUNTIME_ADOPTION_PATTERN"
    CROSS_CUTTING_CAPABILITY = "CROSS_CUTTING_CAPABILITY"
    READ_ONLY_PROJECTION = "READ_ONLY_PROJECTION"
    PRESERVATION_CAPABILITY = "PRESERVATION_CAPABILITY"
    INTEGRATION_PROPERTY = "INTEGRATION_PROPERTY"
    DEVELOPMENT_PRINCIPLE = "DEVELOPMENT_PRINCIPLE"
    SUBPILLAR = "SUBPILLAR"
    DEPENDENT_CAPABILITY = "DEPENDENT_CAPABILITY"
    ARCHITECTURE_VERIFICATION_LAYER = "ARCHITECTURE_VERIFICATION_LAYER"
    HISTORICAL_EXPERIMENT = "HISTORICAL_EXPERIMENT"


class ArchitectureMode(str, Enum):
    NO_SYSTEM = "NO_SYSTEM"
    ADVISORY = "ADVISORY"
    REAL_RUN = "REAL_RUN"
    COMPOSED_REAL_RUN = "COMPOSED_REAL_RUN"
    READ_ONLY_REAL_RUN = "READ_ONLY_REAL_RUN"
    PERSISTENT_UNATTENDED = "PERSISTENT_UNATTENDED"
    HUMAN_GATE = "HUMAN_GATE"
    NOT_EXECUTOR = "NOT_EXECUTOR"


class ArchitectureState(str, Enum):
    CANONICAL = "CANONICAL"
    CANDIDATE = "CANDIDATE"
    HISTORICAL = "HISTORICAL"


class ImplementationState(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    CANDIDATE = "CANDIDATE"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    OPERATING_LAYER = "OPERATING_LAYER"


class ActivationState(str, Enum):
    ACTIVE = "ACTIVE"
    GATED = "GATED"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    HISTORICAL = "HISTORICAL"


class RelationType(str, Enum):
    SELECTS = "SELECTS"
    INVOKES = "INVOKES"
    HOSTS = "HOSTS"
    PERSISTS = "PERSISTS"
    OBSERVES = "OBSERVES"
    VERIFIES = "VERIFIES"
    BINDS = "BINDS"
    CONSTRAINS = "CONSTRAINS"
    SUBSTITUTES = "SUBSTITUTES"
    ROUTES = "ROUTES"
    PROJECTS = "PROJECTS"
    EXTENDS = "EXTENDS"
    COMPOSES_WITH = "COMPOSES_WITH"
    DEPENDS_ON = "DEPENDS_ON"
    GOVERNS = "GOVERNS"


def _opaque(value: str, prefix: str, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        rf"{re.escape(prefix)}_[0-9a-f]{{16}}", value
    ):
        raise ArchitectureIntegrityError(
            f"{field} must be opaque {prefix}_<16-hex>"
        )
    return value


def _digest(value: str, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ArchitectureIntegrityError(f"{field} must be sha256:<64-hex>")
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    return value


@dataclass(frozen=True, slots=True)
class ArchitectureComponentProjection:
    component_id: str
    owner_id: str
    classification: ArchitectureClass
    modes: tuple[ArchitectureMode, ...]
    architecture_state: ArchitectureState
    implementation_state: ImplementationState
    activation_state: ActivationState
    projection_id: str
    registry_revision_digest: str
    authority_ceiling_digest: str
    execution_capable: bool = False
    target_mutation_capable: bool = False
    independent_native_owner: bool = False
    native_state_or_semantics_owned: bool = False
    has_system_justification: bool = False
    decision_scoped: bool = True
    stable_alias: bool = False
    internal_identity_disclosed: bool = False
    authority_created: bool = False
    schema_version: str = COMPONENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != COMPONENT_SCHEMA:
            raise ArchitectureIntegrityError("unsupported component projection schema")
        _opaque(self.component_id, "c", "component_id")
        _opaque(self.owner_id, "o", "owner_id")
        _opaque(self.projection_id, "p", "projection_id")
        _digest(self.registry_revision_digest, "registry_revision_digest")
        _digest(self.authority_ceiling_digest, "authority_ceiling_digest")
        if not self.modes or len(self.modes) != len(set(self.modes)):
            raise ArchitectureIntegrityError("modes must be non-empty and unique")
        for field in (
            "execution_capable",
            "target_mutation_capable",
            "independent_native_owner",
            "native_state_or_semantics_owned",
            "has_system_justification",
            "decision_scoped",
            "stable_alias",
            "internal_identity_disclosed",
            "authority_created",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ArchitectureIntegrityError(f"{field} must be boolean")

        if not self.decision_scoped or self.stable_alias:
            raise ArchitectureIntegrityError("public architecture aliases must be fresh decision-scoped aliases")
        if self.internal_identity_disclosed:
            raise ArchitectureIntegrityError("public architecture projection cannot disclose internal identity")
        if self.authority_created:
            raise ArchitectureIntegrityError("architecture projection cannot create authority")

        if self.classification is ArchitectureClass.SYSTEM:
            if not self.independent_native_owner:
                raise ArchitectureIntegrityError("System projection lacks independent native owner")
            if not self.native_state_or_semantics_owned:
                raise ArchitectureIntegrityError("System projection lacks native state/semantics ownership")
            if not self.has_system_justification:
                raise ArchitectureIntegrityError("System projection lacks anti-proliferation justification")
        else:
            if self.independent_native_owner or self.has_system_justification:
                raise ArchitectureIntegrityError("non-System projection cannot claim System ownership/justification")

        if (
            self.architecture_state is ArchitectureState.HISTORICAL
            and self.activation_state not in {
                ActivationState.HISTORICAL,
                ActivationState.NOT_APPLICABLE,
            }
        ):
            raise ArchitectureIntegrityError("historical architecture cannot be active")
        if (
            self.architecture_state is ArchitectureState.CANDIDATE
            and self.activation_state is ActivationState.ACTIVE
        ):
            raise ArchitectureIntegrityError("candidate architecture cannot claim active activation")
        if (
            self.execution_capable
            and self.activation_state is ActivationState.ACTIVE
            and self.implementation_state is ImplementationState.NOT_APPLICABLE
        ):
            raise ArchitectureIntegrityError("active execution capability requires implementation")


@dataclass(frozen=True, slots=True)
class ArchitectureRelationProjection:
    source_id: str
    relation_type: RelationType
    target_id: str
    projection_id: str
    registry_revision_digest: str
    internal_identity_disclosed: bool = False
    authority_created: bool = False
    schema_version: str = RELATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RELATION_SCHEMA:
            raise ArchitectureIntegrityError("unsupported relation projection schema")
        _opaque(self.source_id, "c", "source_id")
        _opaque(self.target_id, "c", "target_id")
        _opaque(self.projection_id, "p", "projection_id")
        _digest(self.registry_revision_digest, "registry_revision_digest")
        if self.internal_identity_disclosed:
            raise ArchitectureIntegrityError("relation projection cannot disclose internal identity")
        if self.authority_created:
            raise ArchitectureIntegrityError("relation projection cannot create authority")


@dataclass(frozen=True, slots=True)
class ArchitectureIntegrityReceipt:
    projection_id: str
    registry_revision_digest: str
    component_count: int
    relation_count: int
    system_count: int
    executable_count: int
    verdict: str = "PASS"
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = RECEIPT_SCHEMA

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def verify_architecture_projection(
    components: tuple[ArchitectureComponentProjection, ...],
    relations: tuple[ArchitectureRelationProjection, ...],
) -> ArchitectureIntegrityReceipt:
    if not components:
        raise ArchitectureIntegrityError("projection must contain at least one component")

    component_ids = [item.component_id for item in components]
    if len(component_ids) != len(set(component_ids)):
        raise ArchitectureIntegrityError("component aliases must be unique")

    projection_ids = {item.projection_id for item in components}
    registry_digests = {item.registry_revision_digest for item in components}
    if len(projection_ids) != 1 or len(registry_digests) != 1:
        raise ArchitectureIntegrityError("components must belong to one projection and registry revision")

    projection_id = next(iter(projection_ids))
    registry_digest = next(iter(registry_digests))
    known = set(component_ids)

    relation_keys: set[tuple[str, RelationType, str]] = set()
    for relation in relations:
        if relation.projection_id != projection_id:
            raise ArchitectureIntegrityError("relation projection does not match component projection")
        if relation.registry_revision_digest != registry_digest:
            raise ArchitectureIntegrityError("relation registry revision does not match component projection")
        if relation.source_id not in known or relation.target_id not in known:
            raise ArchitectureIntegrityError("relation endpoint is outside the projected component set")
        key = (relation.source_id, relation.relation_type, relation.target_id)
        if key in relation_keys:
            raise ArchitectureIntegrityError("duplicate projected relation")
        relation_keys.add(key)

    return ArchitectureIntegrityReceipt(
        projection_id=projection_id,
        registry_revision_digest=registry_digest,
        component_count=len(components),
        relation_count=len(relations),
        system_count=sum(
            item.classification is ArchitectureClass.SYSTEM for item in components
        ),
        executable_count=sum(item.execution_capable for item in components),
    )


def receipt_to_dict(receipt: ArchitectureIntegrityReceipt) -> dict[str, Any]:
    return _jsonable(receipt)
