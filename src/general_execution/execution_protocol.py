from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import Enum
from itertools import combinations
from typing import Any, Iterable

from .canonical import sha256_digest
from .holistic_symbiosis import (
    ExecutorProviderBinding,
    SymbioticRouteDecision,
    compose_symbiotic_route,
)
from .provider_portability import (
    InternalLineageBinding,
    ProviderResource,
    ProviderRoutingAuthority,
)
from .work_sparse_unattended import (
    ControllerDisposition,
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
)

PROTOCOL_VERSION = "0.1.0"
SYSTEM_SCHEMA = "ge.execution-protocol-capability-projection.v1"
REQUEST_SCHEMA = "ge.execution-protocol-request.v1"
RESOURCE_SCHEMA = "ge.execution-protocol-resource-observation.v1"
METHOD_SCHEMA = "ge.execution-protocol-method-profile.v1"
DECISION_SCHEMA = "ge.execution-protocol-decision.v1"


class ExecutionProtocolError(ValueError):
    pass


class InvocationMode(str, Enum):
    NO_SYSTEM = "NO_SYSTEM"
    ADVISORY = "ADVISORY"
    REAL_RUN = "REAL_RUN"
    COMPOSED_REAL_RUN = "COMPOSED_REAL_RUN"


class ProtocolDisposition(str, Enum):
    NO_SYSTEM_REQUIRED = "NO_SYSTEM_REQUIRED"
    ADVISORY_READY = "ADVISORY_READY"
    READY_FOR_EXISTING_ADMISSION = "READY_FOR_EXISTING_ADMISSION"
    OBSERVE_EXISTING = "OBSERVE_EXISTING"
    CONDITION_WAIT = "CONDITION_WAIT"
    HUMAN_GATE = "HUMAN_GATE"


class ResourceCauseKind(str, Enum):
    NONE = "none"
    CAPACITY = "capacity"
    CREDENTIAL = "credential"
    PROVIDER = "provider"
    PAID_RESOURCE = "paid_resource"
    TIME = "time"
    EXTERNAL_EVIDENCE = "external_evidence"
    UNKNOWN = "unknown"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionProtocolError(f"{field} must be a non-empty string")
    return value.strip()


def _nonnegative(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExecutionProtocolError(f"{field} must be a non-negative integer")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise ExecutionProtocolError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise ExecutionProtocolError(f"{field} must not contain duplicates")
    return items


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
class CapabilityProjection:
    candidate_id: str
    capability_ids: tuple[str, ...]
    projection_id: str
    registry_revision_digest: str
    authority_ref_digest: str
    cost_rank: int = 0
    execution_capable: bool = False
    internal_identity_disclosed: bool = False
    authority_created: bool = False
    schema_version: str = SYSTEM_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SYSTEM_SCHEMA:
            raise ExecutionProtocolError("unsupported capability projection schema")
        _nonempty(self.candidate_id, "candidate_id")
        _unique(self.capability_ids, "capability_ids", allow_empty=False)
        _nonempty(self.projection_id, "projection_id")
        for field in ("registry_revision_digest", "authority_ref_digest"):
            value = _nonempty(getattr(self, field), field)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ExecutionProtocolError(f"{field} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ExecutionProtocolError(f"{field} must contain hexadecimal digest") from exc
        _nonnegative(self.cost_rank, "cost_rank")
        if not isinstance(self.execution_capable, bool):
            raise ExecutionProtocolError("execution_capable must be boolean")
        if self.internal_identity_disclosed:
            raise ExecutionProtocolError("public capability projection cannot disclose internal identity")
        if self.authority_created:
            raise ExecutionProtocolError("system capability cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionProtocolRequest:
    request_id: str
    objective: str
    evidence_predicate: str
    required_capability_ids: tuple[str, ...]
    repository: str
    authority_ref: str
    projection_id: str | None = None
    registry_revision_digest: str | None = None
    authority_ref_digest: str | None = None
    required_executor_capabilities: tuple[str, ...] = ()
    requested_actions: tuple[str, ...] = ()
    requires_observed_evidence: bool = False
    requires_state_change: bool = False
    advisory_allowed: bool = True
    existing_execution_ref: str | None = None
    schema_version: str = REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA:
            raise ExecutionProtocolError("unsupported request schema")
        for field in ("request_id", "objective", "evidence_predicate", "repository", "authority_ref"):
            _nonempty(getattr(self, field), field)
        _unique(self.required_capability_ids, "required_capability_ids")
        if self.required_capability_ids:
            for field in ("projection_id", "registry_revision_digest", "authority_ref_digest"):
                value = getattr(self, field)
                if value is None:
                    raise ExecutionProtocolError(f"{field} is required when capability selection is requested")
                _nonempty(value, field)
            for field in ("registry_revision_digest", "authority_ref_digest"):
                value = getattr(self, field)
                if value is None or not value.startswith("sha256:") or len(value) != 71:
                    raise ExecutionProtocolError(f"{field} must be sha256:<64-hex>")
                try:
                    int(value[7:], 16)
                except ValueError as exc:
                    raise ExecutionProtocolError(f"{field} must contain hexadecimal digest") from exc
        _unique(self.required_executor_capabilities, "required_executor_capabilities")
        _unique(self.requested_actions, "requested_actions")
        for field in ("requires_observed_evidence", "requires_state_change", "advisory_allowed"):
            if not isinstance(getattr(self, field), bool):
                raise ExecutionProtocolError(f"{field} must be boolean")
        if self.existing_execution_ref is not None:
            _nonempty(self.existing_execution_ref, "existing_execution_ref")


@dataclass(frozen=True, slots=True)
class ResourceObservation:
    executor_id: str
    available: bool
    cause_kind: ResourceCauseKind
    cause_code: str
    evidence_ref: str
    authority_created: bool = False
    schema_version: str = RESOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RESOURCE_SCHEMA:
            raise ExecutionProtocolError("unsupported resource observation schema")
        _nonempty(self.executor_id, "executor_id")
        _nonempty(self.cause_code, "cause_code")
        _nonempty(self.evidence_ref, "evidence_ref")
        if not isinstance(self.available, bool):
            raise ExecutionProtocolError("available must be boolean")
        if self.available and self.cause_kind is not ResourceCauseKind.NONE:
            raise ExecutionProtocolError("available resource must use cause_kind=none")
        if not self.available and self.cause_kind is ResourceCauseKind.NONE:
            raise ExecutionProtocolError("unavailable resource requires a resolved cause")
        if self.authority_created:
            raise ExecutionProtocolError("resource observation cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionMethodProfile:
    executor_id: str
    evidence_predicates: tuple[str, ...]
    evidence_quality_rank: int = 1
    schema_version: str = METHOD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != METHOD_SCHEMA:
            raise ExecutionProtocolError("unsupported method profile schema")
        _nonempty(self.executor_id, "executor_id")
        _unique(self.evidence_predicates, "evidence_predicates", allow_empty=False)
        _nonnegative(self.evidence_quality_rank, "evidence_quality_rank")


@dataclass(frozen=True, slots=True)
class ExecutionProtocolDecision:
    request_id: str
    invocation_mode: InvocationMode
    disposition: ProtocolDisposition
    selected_candidate_ids: tuple[str, ...]
    selected_executor_id: str | None
    selected_resource_id: str | None
    uncovered_capability_ids: tuple[str, ...]
    resource_findings: tuple[str, ...]
    rejected_executors: tuple[str, ...]
    route_digest: str | None
    evidence_predicate_preserved: bool
    reasons: tuple[str, ...]
    authority_ref: str
    authority_created: bool = False
    execution_triggered: bool = False
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = DECISION_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.request_id, "request_id")
        _nonempty(self.authority_ref, "authority_ref")
        _unique(self.selected_candidate_ids, "selected_candidate_ids")
        _unique(self.uncovered_capability_ids, "uncovered_capability_ids")
        _unique(self.resource_findings, "resource_findings")
        _unique(self.rejected_executors, "rejected_executors")
        if self.authority_created or self.execution_triggered:
            raise ExecutionProtocolError("Execution Protocol cannot create authority or trigger execution")
        if self.disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION:
            if self.selected_executor_id is None or self.route_digest is None:
                raise ExecutionProtocolError("ready decision must bind an executor and route")
            if not self.evidence_predicate_preserved:
                raise ExecutionProtocolError("ready decision must preserve the evidence predicate")
        if self.invocation_mode in {InvocationMode.NO_SYSTEM, InvocationMode.ADVISORY}:
            if self.selected_executor_id is not None or self.execution_triggered:
                raise ExecutionProtocolError("non-real mode cannot bind or trigger an executor")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def decision_to_dict(decision: ExecutionProtocolDecision) -> dict[str, Any]:
    return _jsonable(decision)


def _select_candidates(
    required_capabilities: tuple[str, ...],
    candidates: tuple[CapabilityProjection, ...],
    *,
    expected_projection_id: str | None,
    expected_registry_revision_digest: str | None,
    expected_authority_ref_digest: str | None,
) -> tuple[tuple[CapabilityProjection, ...], tuple[str, ...]]:
    required = set(required_capabilities)
    if not required:
        return (), ()

    ids = [item.candidate_id for item in candidates]
    if len(ids) != len(set(ids)):
        raise ExecutionProtocolError("candidate_id values must be unique")
    projection_ids = {item.projection_id for item in candidates}
    registry_digests = {item.registry_revision_digest for item in candidates}
    authority_digests = {item.authority_ref_digest for item in candidates}
    if len(projection_ids) != 1 or len(registry_digests) != 1 or len(authority_digests) != 1:
        raise ExecutionProtocolError("capability candidates must come from one bound projection")
    if (
        projection_ids != {expected_projection_id}
        or registry_digests != {expected_registry_revision_digest}
        or authority_digests != {expected_authority_ref_digest}
    ):
        raise ExecutionProtocolError("capability projection does not match request binding")

    covering: list[tuple[CapabilityProjection, ...]] = []
    for size in range(1, len(candidates) + 1):
        for combo in combinations(candidates, size):
            covered = set().union(*(set(item.capability_ids) for item in combo))
            if required <= covered:
                covering.append(combo)
        if covering:
            break

    if not covering:
        covered = set().union(*(set(item.capability_ids) for item in candidates)) if candidates else set()
        return (), tuple(sorted(required - covered))

    selected = min(
        covering,
        key=lambda combo: (
            sum(item.cost_rank for item in combo),
            tuple(sorted(item.candidate_id for item in combo)),
        ),
    )
    return tuple(sorted(selected, key=lambda item: item.candidate_id)), ()


def _mode_for(
    request: ExecutionProtocolRequest,
    selected: tuple[CapabilityProjection, ...],
) -> InvocationMode:
    if not request.required_capability_ids:
        if request.requires_observed_evidence or request.requires_state_change:
            return InvocationMode.REAL_RUN
        return InvocationMode.NO_SYSTEM
    if not request.requires_observed_evidence and not request.requires_state_change:
        if request.advisory_allowed:
            return InvocationMode.ADVISORY
    return (
        InvocationMode.REAL_RUN
        if len(selected) <= 1
        else InvocationMode.COMPOSED_REAL_RUN
    )


def _resource_index(
    observations: tuple[ResourceObservation, ...],
) -> dict[str, ResourceObservation]:
    found: dict[str, ResourceObservation] = {}
    for observation in observations:
        if observation.executor_id in found:
            raise ExecutionProtocolError("resource observations must be unique by executor_id")
        found[observation.executor_id] = observation
    return found


def _method_index(
    profiles: tuple[ExecutionMethodProfile, ...],
) -> dict[str, ExecutionMethodProfile]:
    found: dict[str, ExecutionMethodProfile] = {}
    for profile in profiles:
        if profile.executor_id in found:
            raise ExecutionProtocolError("method profiles must be unique by executor_id")
        found[profile.executor_id] = profile
    return found


def _resolve_executors(
    *,
    predicate: str,
    executors: tuple[ExecutorCapability, ...],
    resources: tuple[ResourceObservation, ...],
    profiles: tuple[ExecutionMethodProfile, ...],
    minimum_evidence_quality_rank: int,
) -> tuple[tuple[ExecutorCapability, ...], tuple[str, ...], tuple[str, ...]]:
    _nonnegative(minimum_evidence_quality_rank, "minimum_evidence_quality_rank")
    resource_by_id = _resource_index(resources)
    method_by_id = _method_index(profiles)

    ids = [executor.executor_id for executor in executors]
    if len(ids) != len(set(ids)):
        raise ExecutionProtocolError("executor_id values must be unique")

    eligible: list[ExecutorCapability] = []
    findings: list[str] = []
    rejected: list[str] = []

    for executor in executors:
        observation = resource_by_id.get(executor.executor_id)
        if observation is None:
            if not executor.available:
                raise ExecutionProtocolError(
                    f"unavailable executor {executor.executor_id} has no resolved resource cause"
                )
            available = True
        else:
            available = observation.available
            findings.append(
                f"{executor.executor_id}:{observation.cause_kind.value}:{observation.cause_code}"
            )

        profile = method_by_id.get(executor.executor_id)
        reasons: list[str] = []
        if profile is None:
            reasons.append("missing_method_profile")
        else:
            if predicate not in profile.evidence_predicates:
                reasons.append("predicate_not_covered")
            if profile.evidence_quality_rank < minimum_evidence_quality_rank:
                reasons.append("evidence_quality_insufficient")
        if not available:
            cause = observation.cause_kind.value if observation is not None else "unknown"
            code = observation.cause_code if observation is not None else "unresolved"
            reasons.append(f"resource_unavailable:{cause}:{code}")

        if reasons:
            rejected.append(f"{executor.executor_id}|" + ",".join(sorted(reasons)))
            continue
        eligible.append(replace(executor, available=True))

    return tuple(eligible), tuple(sorted(findings)), tuple(sorted(rejected))


def decide_execution_protocol(
    *,
    request: ExecutionProtocolRequest,
    candidates: tuple[CapabilityProjection, ...],
    envelope: UnattendedAuthorityEnvelope,
    executors: tuple[ExecutorCapability, ...] = (),
    resource_observations: tuple[ResourceObservation, ...] = (),
    method_profiles: tuple[ExecutionMethodProfile, ...] = (),
    usage: ControllerUsage = ControllerUsage(),
    minimum_evidence_quality_rank: int = 1,
    provider_lineage: InternalLineageBinding | None = None,
    provider_routing: ProviderRoutingAuthority | None = None,
    provider_resources: tuple[ProviderResource, ...] = (),
    executor_provider_bindings: tuple[ExecutorProviderBinding, ...] = (),
) -> ExecutionProtocolDecision:
    selected_candidates, uncovered = _select_candidates(
        request.required_capability_ids,
        candidates,
        expected_projection_id=request.projection_id,
        expected_registry_revision_digest=request.registry_revision_digest,
        expected_authority_ref_digest=request.authority_ref_digest,
    )
    mode = _mode_for(request, selected_candidates)
    selected_ids = tuple(item.candidate_id for item in selected_candidates)

    if uncovered:
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.CONDITION_WAIT,
            selected_candidate_ids=(),
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=uncovered,
            resource_findings=(),
            rejected_executors=(),
            route_digest=None,
            evidence_predicate_preserved=False,
            reasons=("capability_uncovered",),
            authority_ref=request.authority_ref,
        )

    if mode is InvocationMode.NO_SYSTEM:
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.NO_SYSTEM_REQUIRED,
            selected_candidate_ids=(),
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=(),
            resource_findings=(),
            rejected_executors=(),
            route_digest=None,
            evidence_predicate_preserved=True,
            reasons=("no_system_needed_for_requested_outcome",),
            authority_ref=request.authority_ref,
        )

    if mode is InvocationMode.ADVISORY:
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.ADVISORY_READY,
            selected_candidate_ids=selected_ids,
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=(),
            resource_findings=(),
            rejected_executors=(),
            route_digest=None,
            evidence_predicate_preserved=True,
            reasons=("advisory_system_application",),
            authority_ref=request.authority_ref,
        )

    if not any(item.execution_capable for item in selected_candidates):
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.CONDITION_WAIT,
            selected_candidate_ids=selected_ids,
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=(),
            resource_findings=(),
            rejected_executors=(),
            route_digest=None,
            evidence_predicate_preserved=False,
            reasons=("real_run_requires_execution_capable_candidate",),
            authority_ref=request.authority_ref,
        )

    if request.existing_execution_ref is not None:
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.OBSERVE_EXISTING,
            selected_candidate_ids=selected_ids,
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=(),
            resource_findings=(),
            rejected_executors=(),
            route_digest=None,
            evidence_predicate_preserved=True,
            reasons=(f"existing_execution:{request.existing_execution_ref}",),
            authority_ref=request.authority_ref,
        )

    eligible_executors, findings, rejected = _resolve_executors(
        predicate=request.evidence_predicate,
        executors=executors,
        resources=resource_observations,
        profiles=method_profiles,
        minimum_evidence_quality_rank=minimum_evidence_quality_rank,
    )

    work = UnattendedWorkItem(
        work_id=request.request_id,
        objective=request.objective,
        repository=request.repository,
        source_revision="execution-protocol-request",
        authority_ref=request.authority_ref,
        required_capabilities=request.required_executor_capabilities,
        requested_actions=request.requested_actions,
        existing_execution_ref=request.existing_execution_ref,
    )

    if not eligible_executors:
        blocked_causes = tuple(
            item for item in findings if not item.endswith(":none:available")
        )
        return ExecutionProtocolDecision(
            request_id=request.request_id,
            invocation_mode=mode,
            disposition=ProtocolDisposition.CONDITION_WAIT,
            selected_candidate_ids=selected_ids,
            selected_executor_id=None,
            selected_resource_id=None,
            uncovered_capability_ids=(),
            resource_findings=findings,
            rejected_executors=rejected,
            route_digest=None,
            evidence_predicate_preserved=False,
            reasons=(
                "no_evidence_equivalent_available_executor",
                *blocked_causes,
            ),
            authority_ref=request.authority_ref,
        )

    route: SymbioticRouteDecision = compose_symbiotic_route(
        envelope=envelope,
        work=work,
        executors=eligible_executors,
        evidence_predicate=request.evidence_predicate,
        usage=usage,
        provider_lineage=provider_lineage,
        provider_routing=provider_routing,
        provider_resources=provider_resources,
        executor_provider_bindings=executor_provider_bindings,
    )

    ws_disposition = route.work_sparse.disposition
    if ws_disposition == ControllerDisposition.OBSERVE_EXISTING.value:
        disposition = ProtocolDisposition.OBSERVE_EXISTING
    elif ws_disposition == ControllerDisposition.HUMAN_GATE.value:
        disposition = ProtocolDisposition.HUMAN_GATE
    elif route.ready_for_existing_admission:
        disposition = ProtocolDisposition.READY_FOR_EXISTING_ADMISSION
    else:
        disposition = ProtocolDisposition.CONDITION_WAIT

    predicate_preserved = bool(
        route.substitution is not None
        and route.substitution.evidence_predicate_preserved
        and not route.substitution.deferred
    ) if disposition is ProtocolDisposition.READY_FOR_EXISTING_ADMISSION else False

    return ExecutionProtocolDecision(
        request_id=request.request_id,
        invocation_mode=mode,
        disposition=disposition,
        selected_candidate_ids=selected_ids,
        selected_executor_id=route.selected_executor_id,
        selected_resource_id=route.selected_resource_id,
        uncovered_capability_ids=(),
        resource_findings=findings,
        rejected_executors=rejected,
        route_digest=route.digest,
        evidence_predicate_preserved=predicate_preserved,
        reasons=(
            *route.reasons,
            *(
                ("resource_cause_resolved_before_route",)
                if findings
                else ()
            ),
        ),
        authority_ref=request.authority_ref,
    )
