from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical import sha256_digest, stable_id

LINEAGE_SCHEMA = "ge.internal-lineage-binding.v1"
RESOURCE_SCHEMA = "ge.provider-resource.v1"
ROUTING_SCHEMA = "ge.provider-routing-authority.v1"
ENVELOPE_SCHEMA = "ge.provider-task-envelope.v1"
BINDING_SCHEMA = "ge.provider-envelope-binding.v1"
DECISION_SCHEMA = "ge.provider-route-decision.v1"
PROTOCOL_VERSION = "0.1.0"


class ProviderPortabilityError(ValueError):
    """Raised when provider-portability contracts are invalid."""


class ResourceDisposition(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DECLINED = "declined"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderPortabilityError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProviderPortabilityError(f"{field} must be a positive integer")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise ProviderPortabilityError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise ProviderPortabilityError(f"{field} must not contain duplicates")
    return items


def _digest(value: str, field: str) -> str:
    value = _nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ProviderPortabilityError(f"{field} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ProviderPortabilityError(f"{field} must contain hexadecimal digest") from exc
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class InternalLineageBinding:
    """Rich internal identity. Never send this object to an execution provider."""

    work_id: str
    portfolio_ref: str
    source_revision: str
    authority_ref: str
    required_capabilities: tuple[str, ...]
    input_artifact_digests: tuple[str, ...]
    output_contract_digest: str
    semantic_context: tuple[str, ...] = ()
    schema_version: str = LINEAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != LINEAGE_SCHEMA:
            raise ProviderPortabilityError("unsupported lineage schema")
        for field in ("work_id", "portfolio_ref", "source_revision", "authority_ref"):
            _nonempty(getattr(self, field), field)
        _unique(self.required_capabilities, "required_capabilities")
        _unique(self.input_artifact_digests, "input_artifact_digests")
        for index, digest in enumerate(self.input_artifact_digests):
            _digest(digest, f"input_artifact_digests[{index}]")
        _digest(self.output_contract_digest, "output_contract_digest")
        _unique(self.semantic_context, "semantic_context", allow_empty=True)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderResource:
    resource_id: str
    provider_id: str
    disposition: ResourceDisposition
    capabilities: tuple[str, ...]
    billing_scope_ref: str
    authority_ref: str
    admission_digest: str
    evidence_refs: tuple[str, ...]
    authority_created: bool = False
    schema_version: str = RESOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RESOURCE_SCHEMA:
            raise ProviderPortabilityError("unsupported provider resource schema")
        for field in ("resource_id", "provider_id", "billing_scope_ref", "authority_ref"):
            _nonempty(getattr(self, field), field)
        _unique(self.capabilities, "capabilities")
        _digest(self.admission_digest, "admission_digest")
        _unique(self.evidence_refs, "evidence_refs")
        if not isinstance(self.authority_created, bool):
            raise ProviderPortabilityError("authority_created must be boolean")
        if self.authority_created:
            raise ProviderPortabilityError("provider resource cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderRoutingAuthority:
    authority_ref: str
    allowed_resource_ids: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    authority_created: bool = False
    schema_version: str = ROUTING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ROUTING_SCHEMA:
            raise ProviderPortabilityError("unsupported provider routing schema")
        _nonempty(self.authority_ref, "authority_ref")
        _unique(self.allowed_resource_ids, "allowed_resource_ids")
        _unique(self.allowed_capabilities, "allowed_capabilities")
        if not isinstance(self.authority_created, bool):
            raise ProviderPortabilityError("authority_created must be boolean")
        if self.authority_created:
            raise ProviderPortabilityError("routing authority cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderTaskEnvelope:
    """Provider-visible projection. Contains no internal project identity fields."""

    provider_task_ref: str
    resource_id: str
    billing_scope_ref: str
    required_capabilities: tuple[str, ...]
    input_artifact_digests: tuple[str, ...]
    output_contract_digest: str
    max_runtime_seconds: int
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = ENVELOPE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ENVELOPE_SCHEMA:
            raise ProviderPortabilityError("unsupported provider task envelope schema")
        for field in ("provider_task_ref", "resource_id", "billing_scope_ref"):
            _nonempty(getattr(self, field), field)
        _unique(self.required_capabilities, "required_capabilities")
        _unique(self.input_artifact_digests, "input_artifact_digests")
        for index, digest in enumerate(self.input_artifact_digests):
            _digest(digest, f"input_artifact_digests[{index}]")
        _digest(self.output_contract_digest, "output_contract_digest")
        _positive_int(self.max_runtime_seconds, "max_runtime_seconds")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderEnvelopeBinding:
    """Internal receipt binding an opaque provider envelope back to exact lineage."""

    internal_lineage_digest: str
    provider_envelope_digest: str
    provider_task_ref: str
    resource_id: str
    provider_id: str
    authority_ref: str
    schema_version: str = BINDING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BINDING_SCHEMA:
            raise ProviderPortabilityError("unsupported provider envelope binding schema")
        _digest(self.internal_lineage_digest, "internal_lineage_digest")
        _digest(self.provider_envelope_digest, "provider_envelope_digest")
        for field in ("provider_task_ref", "resource_id", "provider_id", "authority_ref"):
            _nonempty(getattr(self, field), field)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderRouteRejection:
    resource_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProviderRouteDecision:
    routing_authority_digest: str
    internal_lineage_digest: str
    selected_resource_id: str | None
    selected_provider_id: str | None
    rejected: tuple[ProviderRouteRejection, ...]
    deferred: bool
    authority_created: bool = False
    execution_authorized: bool = False
    schema_version: str = DECISION_SCHEMA
    decision_digest: str = ""

    def __post_init__(self) -> None:
        _digest(self.routing_authority_digest, "routing_authority_digest")
        _digest(self.internal_lineage_digest, "internal_lineage_digest")
        if self.deferred:
            if self.selected_resource_id is not None or self.selected_provider_id is not None:
                raise ProviderPortabilityError("deferred route cannot select a resource")
        else:
            _nonempty(self.selected_resource_id or "", "selected_resource_id")
            _nonempty(self.selected_provider_id or "", "selected_provider_id")
        if self.authority_created or self.execution_authorized:
            raise ProviderPortabilityError("route decision cannot create or authorize execution")

    @property
    def digest(self) -> str:
        return self.decision_digest


def _decision_payload(decision: ProviderRouteDecision) -> dict[str, Any]:
    payload = _jsonable(decision)
    payload.pop("decision_digest", None)
    return payload


def route_provider_task(
    lineage: InternalLineageBinding,
    routing: ProviderRoutingAuthority,
    resources: tuple[ProviderResource, ...],
) -> ProviderRouteDecision:
    """Select an already-authorized available resource; never bypass a declined one."""

    resource_ids = [resource.resource_id for resource in resources]
    if len(resource_ids) != len(set(resource_ids)):
        raise ProviderPortabilityError("resource_id values must be unique")

    allowed_ids = set(routing.allowed_resource_ids)
    allowed_caps = set(routing.allowed_capabilities)
    required = set(lineage.required_capabilities)
    rejected: list[ProviderRouteRejection] = []
    eligible: list[ProviderResource] = []

    for resource in sorted(resources, key=lambda item: (item.provider_id, item.resource_id)):
        reasons: list[str] = []
        if resource.resource_id not in allowed_ids:
            reasons.append("resource_outside_authority")
        if not required <= allowed_caps:
            reasons.append("task_capability_outside_authority")
        if not required <= set(resource.capabilities):
            reasons.append("resource_capability_mismatch")
        if resource.disposition is ResourceDisposition.UNAVAILABLE:
            reasons.append("resource_unavailable")
        elif resource.disposition is ResourceDisposition.DECLINED:
            reasons.append("resource_declined")

        if reasons:
            rejected.append(
                ProviderRouteRejection(resource.resource_id, tuple(sorted(set(reasons))))
            )
        else:
            eligible.append(resource)

    selected = eligible[0] if eligible else None
    provisional = ProviderRouteDecision(
        routing_authority_digest=routing.digest,
        internal_lineage_digest=lineage.digest,
        selected_resource_id=selected.resource_id if selected else None,
        selected_provider_id=selected.provider_id if selected else None,
        rejected=tuple(sorted(rejected, key=lambda item: item.resource_id)),
        deferred=selected is None,
    )
    return ProviderRouteDecision(
        routing_authority_digest=provisional.routing_authority_digest,
        internal_lineage_digest=provisional.internal_lineage_digest,
        selected_resource_id=provisional.selected_resource_id,
        selected_provider_id=provisional.selected_provider_id,
        rejected=provisional.rejected,
        deferred=provisional.deferred,
        authority_created=False,
        execution_authorized=False,
        decision_digest=sha256_digest(_decision_payload(provisional)),
    )


def build_provider_task_envelope(
    lineage: InternalLineageBinding,
    resource: ProviderResource,
    *,
    dispatch_nonce: str,
    max_runtime_seconds: int,
) -> tuple[ProviderTaskEnvelope, ProviderEnvelopeBinding]:
    """Project internal lineage into a minimum provider-visible execution envelope."""

    if resource.disposition is not ResourceDisposition.AVAILABLE:
        raise ProviderPortabilityError("provider envelope requires an available resource")
    if not set(lineage.required_capabilities) <= set(resource.capabilities):
        raise ProviderPortabilityError("provider resource lacks required capability")
    _nonempty(dispatch_nonce, "dispatch_nonce")
    _positive_int(max_runtime_seconds, "max_runtime_seconds")

    provider_task_ref = stable_id(
        "pt",
        {
            "lineage_digest": lineage.digest,
            "resource_id": resource.resource_id,
            "dispatch_nonce": dispatch_nonce,
        },
    )
    envelope = ProviderTaskEnvelope(
        provider_task_ref=provider_task_ref,
        resource_id=resource.resource_id,
        billing_scope_ref=resource.billing_scope_ref,
        required_capabilities=lineage.required_capabilities,
        input_artifact_digests=lineage.input_artifact_digests,
        output_contract_digest=lineage.output_contract_digest,
        max_runtime_seconds=max_runtime_seconds,
    )
    binding = ProviderEnvelopeBinding(
        internal_lineage_digest=lineage.digest,
        provider_envelope_digest=envelope.digest,
        provider_task_ref=envelope.provider_task_ref,
        resource_id=resource.resource_id,
        provider_id=resource.provider_id,
        authority_ref=resource.authority_ref,
    )
    return envelope, binding


def provider_visible_dict(envelope: ProviderTaskEnvelope) -> dict[str, Any]:
    return _jsonable(envelope)


def verify_provider_binding(
    lineage: InternalLineageBinding,
    envelope: ProviderTaskEnvelope,
    binding: ProviderEnvelopeBinding,
) -> bool:
    return (
        binding.internal_lineage_digest == lineage.digest
        and binding.provider_envelope_digest == envelope.digest
        and binding.provider_task_ref == envelope.provider_task_ref
        and binding.resource_id == envelope.resource_id
    )
