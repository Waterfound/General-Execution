from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical import sha256_digest

RESOURCE_OFFER_SCHEMA = "ge.abundant-resource-offer.v1"
RESOURCE_ENVELOPE_SCHEMA = "ge.abundant-resource-authority-envelope.v1"
RESOURCE_DECISION_SCHEMA = "ge.abundant-resource-admission.v1"
PROTOCOL_VERSION = "0.1.0"


class AbundantResourceError(ValueError):
    """Raised when the abundant-resource admission contract is invalid."""


class ResourceEconomics(str, Enum):
    OWNED_LOCAL = "owned_local"
    INCLUDED_ALLOWANCE = "included_allowance"
    ZERO_COST_PROVIDER = "zero_cost_provider"
    PAID = "paid"
    UNKNOWN = "unknown"


_ABUNDANT_ECONOMICS = {
    ResourceEconomics.OWNED_LOCAL,
    ResourceEconomics.INCLUDED_ALLOWANCE,
    ResourceEconomics.ZERO_COST_PROVIDER,
}


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AbundantResourceError(f"{field} must be a non-empty string")
    return value.strip()


def _nonnegative_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AbundantResourceError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AbundantResourceError(f"{field} must be a positive integer")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    result = tuple(_nonempty(value, field) for value in values)
    if not allow_empty and not result:
        raise AbundantResourceError(f"{field} cannot be empty")
    if len(result) != len(set(result)):
        raise AbundantResourceError(f"{field} must not contain duplicates")
    return result


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
class ResourceOffer:
    resource_id: str
    capabilities: tuple[str, ...]
    max_parallelism: int
    economics: ResourceEconomics
    incremental_cost_cents_per_invocation: int
    automatic_paid_fallback: bool
    available: bool
    evidence_refs: tuple[str, ...]
    authority_created: bool = False
    schema_version: str = RESOURCE_OFFER_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RESOURCE_OFFER_SCHEMA:
            raise AbundantResourceError("unsupported resource offer schema")
        _nonempty(self.resource_id, "resource_id")
        _unique(self.capabilities, "capabilities")
        _positive_int(self.max_parallelism, "max_parallelism")
        _nonnegative_int(
            self.incremental_cost_cents_per_invocation,
            "incremental_cost_cents_per_invocation",
        )
        if not isinstance(self.automatic_paid_fallback, bool):
            raise AbundantResourceError("automatic_paid_fallback must be boolean")
        if not isinstance(self.available, bool):
            raise AbundantResourceError("available must be boolean")
        _unique(self.evidence_refs, "evidence_refs")
        if not isinstance(self.authority_created, bool):
            raise AbundantResourceError("authority_created must be boolean")
        if self.authority_created:
            raise AbundantResourceError("resource offer cannot create authority")
        if (
            self.economics in _ABUNDANT_ECONOMICS
            and self.incremental_cost_cents_per_invocation != 0
        ):
            raise AbundantResourceError(
                "abundant economics require zero incremental monetary cost"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AbundantResourceAuthorityEnvelope:
    envelope_id: str
    authority_ref: str
    allowed_resource_ids: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    max_total_parallelism: int
    allow_paid_resources: bool = False
    authority_created: bool = False
    schema_version: str = RESOURCE_ENVELOPE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RESOURCE_ENVELOPE_SCHEMA:
            raise AbundantResourceError("unsupported resource envelope schema")
        _nonempty(self.envelope_id, "envelope_id")
        _nonempty(self.authority_ref, "authority_ref")
        _unique(self.allowed_resource_ids, "allowed_resource_ids")
        _unique(self.allowed_capabilities, "allowed_capabilities")
        _positive_int(self.max_total_parallelism, "max_total_parallelism")
        if not isinstance(self.allow_paid_resources, bool):
            raise AbundantResourceError("allow_paid_resources must be boolean")
        if not isinstance(self.authority_created, bool):
            raise AbundantResourceError("authority_created must be boolean")
        if self.authority_created:
            raise AbundantResourceError("resource envelope cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ResourceRejection:
    resource_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AbundantResourceAdmission:
    envelope_digest: str
    admitted_resource_ids: tuple[str, ...]
    admitted_resource_digests: tuple[str, ...]
    rejected: tuple[ResourceRejection, ...]
    admitted_parallelism: int
    incremental_paid_spend_cents: int
    authority_created: bool = False
    execution_triggered: bool = False
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = RESOURCE_DECISION_SCHEMA
    decision_digest: str = ""

    def __post_init__(self) -> None:
        if self.authority_created:
            raise AbundantResourceError("admission cannot create authority")
        if self.execution_triggered:
            raise AbundantResourceError("admission cannot claim execution")
        _nonnegative_int(self.admitted_parallelism, "admitted_parallelism")
        _nonnegative_int(
            self.incremental_paid_spend_cents,
            "incremental_paid_spend_cents",
        )
        if self.incremental_paid_spend_cents != 0:
            raise AbundantResourceError(
                "abundant admission must have zero incremental paid spend"
            )

    @property
    def digest(self) -> str:
        return self.decision_digest


def _decision_payload(decision: AbundantResourceAdmission) -> dict[str, Any]:
    payload = _jsonable(decision)
    payload.pop("decision_digest", None)
    return payload


def admission_to_dict(decision: AbundantResourceAdmission) -> dict[str, Any]:
    return {**_decision_payload(decision), "decision_digest": decision.decision_digest}


def admit_abundant_resources(
    envelope: AbundantResourceAuthorityEnvelope,
    offers: tuple[ResourceOffer, ...],
) -> AbundantResourceAdmission:
    """Admit zero-incremental-cost resource capacity without launching work."""

    ids = [offer.resource_id for offer in offers]
    if len(ids) != len(set(ids)):
        raise AbundantResourceError("resource_id values must be unique")

    allowed_ids = set(envelope.allowed_resource_ids)
    allowed_caps = set(envelope.allowed_capabilities)
    admitted: list[ResourceOffer] = []
    rejected: list[ResourceRejection] = []

    for offer in sorted(offers, key=lambda item: item.resource_id):
        reasons: list[str] = []
        if offer.resource_id not in allowed_ids:
            reasons.append("resource_outside_authority_envelope")
        if not offer.available:
            reasons.append("resource_unavailable")
        if not set(offer.capabilities) <= allowed_caps:
            reasons.append("capability_outside_authority_envelope")
        if offer.economics not in _ABUNDANT_ECONOMICS:
            reasons.append(f"economics_not_abundant:{offer.economics.value}")
        if offer.incremental_cost_cents_per_invocation != 0:
            reasons.append("nonzero_incremental_cost")
        if offer.automatic_paid_fallback:
            reasons.append("automatic_paid_fallback_enabled")
        if offer.economics is ResourceEconomics.PAID and not envelope.allow_paid_resources:
            reasons.append("paid_resource_not_authorized")

        if reasons:
            rejected.append(ResourceRejection(offer.resource_id, tuple(sorted(set(reasons)))))
        else:
            admitted.append(offer)

    # Admission is deterministic. Capacity is bounded globally by the authority envelope.
    remaining = envelope.max_total_parallelism
    bounded_ids: list[str] = []
    bounded_digests: list[str] = []
    admitted_parallelism = 0

    for offer in admitted:
        if remaining <= 0:
            rejected.append(
                ResourceRejection(
                    offer.resource_id,
                    ("global_parallelism_envelope_exhausted",),
                )
            )
            continue
        granted = min(offer.max_parallelism, remaining)
        if granted < offer.max_parallelism:
            # Partial admission would require a derived capability declaration.
            # Fail closed instead of silently mutating the provider's declared capacity.
            rejected.append(
                ResourceRejection(
                    offer.resource_id,
                    ("resource_capacity_exceeds_remaining_envelope",),
                )
            )
            continue
        bounded_ids.append(offer.resource_id)
        bounded_digests.append(offer.digest)
        admitted_parallelism += granted
        remaining -= granted

    provisional = AbundantResourceAdmission(
        envelope_digest=envelope.digest,
        admitted_resource_ids=tuple(bounded_ids),
        admitted_resource_digests=tuple(bounded_digests),
        rejected=tuple(sorted(rejected, key=lambda item: item.resource_id)),
        admitted_parallelism=admitted_parallelism,
        incremental_paid_spend_cents=0,
    )
    digest = sha256_digest(_decision_payload(provisional))
    return AbundantResourceAdmission(
        envelope_digest=provisional.envelope_digest,
        admitted_resource_ids=provisional.admitted_resource_ids,
        admitted_resource_digests=provisional.admitted_resource_digests,
        rejected=provisional.rejected,
        admitted_parallelism=provisional.admitted_parallelism,
        incremental_paid_spend_cents=0,
        authority_created=False,
        execution_triggered=False,
        decision_digest=digest,
    )


def verify_abundant_resource_admission(
    envelope: AbundantResourceAuthorityEnvelope,
    offers: tuple[ResourceOffer, ...],
    decision: dict[str, Any],
) -> bool:
    try:
        expected = admission_to_dict(admit_abundant_resources(envelope, offers))
    except (AbundantResourceError, TypeError, ValueError):
        return False
    return expected == decision
