from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .canonical import sha256_digest
from .predictive_sovereign_execution import (
    CapabilityMethod,
    CapabilitySubstitutionDecision,
    GateCandidate,
    GateForecast,
    PredictivePrecomputationPlan,
    PredictiveTask,
    SovereignRecoveryCapsule,
    VerificationObservation,
    VerificationReconciliation,
    build_precomputation_plan,
    build_recovery_capsule,
    forecast_gates,
    reconcile_verification_twin,
    select_capability_substitute,
)
from .provider_portability import (
    InternalLineageBinding,
    ProviderResource,
    ProviderRouteDecision,
    ProviderRoutingAuthority,
    route_provider_task,
)
from .work_sparse_unattended import (
    ControllerDisposition,
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    WorkSparseControllerDecision,
    decide_work_sparse_route,
)

SCHEMA = "ge.holistic-symbiotic-execution.v1"


class HolisticSymbiosisError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExecutorProviderBinding:
    executor_id: str
    resource_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.executor_id.strip():
            raise HolisticSymbiosisError("executor_id must be non-empty")
        if not self.resource_ids:
            raise HolisticSymbiosisError("resource_ids cannot be empty")
        if len(self.resource_ids) != len(set(self.resource_ids)):
            raise HolisticSymbiosisError("resource_ids must be unique")


@dataclass(frozen=True, slots=True)
class StewardPredictiveBundle:
    precomputation: PredictivePrecomputationPlan
    gate_forecast: GateForecast
    recovery_capsule: SovereignRecoveryCapsule
    authority_created: bool = False
    execution_triggered: bool = False

    def __post_init__(self) -> None:
        if self.authority_created or self.execution_triggered:
            raise HolisticSymbiosisError("Steward predictive bundle is advisory only")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class SymbioticRouteDecision:
    work_sparse: WorkSparseControllerDecision
    substitution: CapabilitySubstitutionDecision | None
    provider_route: ProviderRouteDecision | None
    selected_executor_id: str | None
    selected_resource_id: str | None
    ready_for_existing_admission: bool
    reasons: tuple[str, ...]
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = SCHEMA

    def __post_init__(self) -> None:
        if self.authority_created or self.execution_triggered:
            raise HolisticSymbiosisError("composition cannot create authority or trigger execution")
        if self.ready_for_existing_admission and self.selected_executor_id is None:
            raise HolisticSymbiosisError("ready decision must bind an executor")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def build_steward_predictive_bundle(
    *,
    current_gate_ref: str,
    tasks: tuple[PredictiveTask, ...],
    gates: tuple[GateCandidate, ...],
    capsule_id: str,
    source_refs: tuple[str, ...],
    durable_state_digests: tuple[str, ...],
    authority_refs: tuple[str, ...],
    resource_aliases: tuple[str, ...],
    reconstruction_steps: tuple[str, ...],
    verification_predicates: tuple[str, ...],
    already_materialized: tuple[str, ...] = (),
) -> StewardPredictiveBundle:
    return StewardPredictiveBundle(
        precomputation=build_precomputation_plan(
            current_gate_ref,
            tasks,
            already_materialized=already_materialized,
        ),
        gate_forecast=forecast_gates(gates),
        recovery_capsule=build_recovery_capsule(
            capsule_id=capsule_id,
            source_refs=source_refs,
            durable_state_digests=durable_state_digests,
            authority_refs=authority_refs,
            resource_aliases=resource_aliases,
            reconstruction_steps=reconstruction_steps,
            verification_predicates=verification_predicates,
        ),
    )


def reconcile_independent_assurance(
    primary: VerificationObservation,
    twin: VerificationObservation,
) -> VerificationReconciliation:
    return reconcile_verification_twin(primary, twin)


def _method_for_executor(
    executor: ExecutorCapability,
    *,
    predicate: str,
    authority_ref: str,
) -> CapabilityMethod:
    # Preserve Work-Sparse preference ordering inside PSE substitution:
    # non-Work before Work, free before paid, then declared cost rank.
    work_penalty = 1_000_000 if executor.requires_work else 0
    paid_penalty = 100_000 if executor.paid else 0
    return CapabilityMethod(
        method_id=executor.executor_id,
        evidence_predicates=(predicate,),
        authority_refs=(authority_ref,),
        cost_rank=work_penalty + paid_penalty + executor.cost_rank,
        paid_spend_cents=executor.estimated_cost_cents,
        available=executor.available,
        evidence_quality_rank=1,
    )


def _binding_for(
    executor_id: str,
    bindings: Iterable[ExecutorProviderBinding],
) -> ExecutorProviderBinding | None:
    found = [item for item in bindings if item.executor_id == executor_id]
    if len(found) > 1:
        raise HolisticSymbiosisError("executor_id has multiple provider bindings")
    return found[0] if found else None


def compose_symbiotic_route(
    *,
    envelope: UnattendedAuthorityEnvelope,
    work: UnattendedWorkItem,
    executors: tuple[ExecutorCapability, ...],
    evidence_predicate: str,
    usage: ControllerUsage = ControllerUsage(),
    provider_lineage: InternalLineageBinding | None = None,
    provider_routing: ProviderRoutingAuthority | None = None,
    provider_resources: tuple[ProviderResource, ...] = (),
    executor_provider_bindings: tuple[ExecutorProviderBinding, ...] = (),
) -> SymbioticRouteDecision:
    if not evidence_predicate.strip():
        raise HolisticSymbiosisError("evidence_predicate must be non-empty")

    ws = decide_work_sparse_route(envelope, work, executors, usage)
    if ws.disposition != ControllerDisposition.DISPATCH.value:
        return SymbioticRouteDecision(
            work_sparse=ws,
            substitution=None,
            provider_route=None,
            selected_executor_id=None,
            selected_resource_id=None,
            ready_for_existing_admission=False,
            reasons=(f"work_sparse:{ws.disposition}", *ws.reasons),
        )

    methods = tuple(
        _method_for_executor(
            executor,
            predicate=evidence_predicate,
            authority_ref=envelope.authority_ref,
        )
        for executor in executors
    )
    substitution = select_capability_substitute(
        predicate=evidence_predicate,
        methods=methods,
        allowed_method_ids=tuple(executor.executor_id for executor in executors),
        active_authority_refs=(envelope.authority_ref,),
        max_paid_spend_cents=max(0, envelope.max_paid_spend_cents - usage.paid_spend_cents),
        minimum_evidence_quality_rank=1,
    )
    if substitution.deferred:
        return SymbioticRouteDecision(
            work_sparse=ws,
            substitution=substitution,
            provider_route=None,
            selected_executor_id=None,
            selected_resource_id=None,
            ready_for_existing_admission=False,
            reasons=("capability_substitution_deferred",),
        )

    if substitution.selected_method_id != ws.selected_executor_id:
        raise HolisticSymbiosisError(
            "Work-Sparse and capability substitution selected different executors"
        )
    selected_executor = ws.selected_executor_id
    if selected_executor is None:
        raise HolisticSymbiosisError("dispatch decision did not bind executor")

    binding = _binding_for(selected_executor, executor_provider_bindings)
    if binding is None:
        return SymbioticRouteDecision(
            work_sparse=ws,
            substitution=substitution,
            provider_route=None,
            selected_executor_id=selected_executor,
            selected_resource_id=None,
            ready_for_existing_admission=True,
            reasons=("executor_selected","no_provider_route_required"),
        )

    if provider_lineage is None or provider_routing is None:
        raise HolisticSymbiosisError(
            "provider-bound executor requires lineage and routing authority"
        )
    if tuple(provider_lineage.required_capabilities) != tuple(work.required_capabilities):
        raise HolisticSymbiosisError(
            "provider lineage capabilities must exactly match work capabilities"
        )

    allowed_bound_resources = tuple(
        resource_id
        for resource_id in provider_routing.allowed_resource_ids
        if resource_id in set(binding.resource_ids)
    )
    derived_routing = ProviderRoutingAuthority(
        authority_ref=provider_routing.authority_ref,
        allowed_resource_ids=allowed_bound_resources,
        allowed_capabilities=provider_routing.allowed_capabilities,
    )
    provider_decision = route_provider_task(
        provider_lineage,
        derived_routing,
        provider_resources,
    )
    if provider_decision.deferred:
        return SymbioticRouteDecision(
            work_sparse=ws,
            substitution=substitution,
            provider_route=provider_decision,
            selected_executor_id=selected_executor,
            selected_resource_id=None,
            ready_for_existing_admission=False,
            reasons=("provider_route_deferred","fail_closed"),
        )

    return SymbioticRouteDecision(
        work_sparse=ws,
        substitution=substitution,
        provider_route=provider_decision,
        selected_executor_id=selected_executor,
        selected_resource_id=provider_decision.selected_resource_id,
        ready_for_existing_admission=True,
        reasons=("executor_selected","evidence_predicate_preserved","provider_route_available"),
    )
