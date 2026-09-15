from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .canonical import sha256_digest, stable_id
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, ResultEnvelope, RunnerCapabilities, RunnerRegistry
from .planner import verify_plan
from .wire import result_to_dict, spec_from_dict, spec_to_dict

REFERENCE_PROVIDER = "reference-provider"
REFERENCE_ADAPTER = "reference-adapter"
REFERENCE_ADAPTER_VERSION = "1"
REFERENCE_CAPABILITY = "reference.probe"
REFERENCE_TASK_KIND = "reference-probe"
REFERENCE_EVIDENCE = "reference-probe-digest"


class AdapterError(ValueError):
    pass


def reference_runner(runner_id: str = "reference-runner-1") -> RunnerCapabilities:
    return RunnerCapabilities(
        runner_id=runner_id,
        provider=REFERENCE_PROVIDER,
        adapter=REFERENCE_ADAPTER,
        adapter_version=REFERENCE_ADAPTER_VERSION,
        capabilities=(REFERENCE_CAPABILITY,),
        modes=("read_only",),
        max_parallelism=1,
    )


@dataclass(frozen=True, slots=True)
class AdapterDispatchRequest:
    invocation_id: str
    session_id: str
    spec_id: str
    spec_digest: str
    plan_id: str
    plan_digest: str
    registry_digest: str
    runner_id: str
    runner_capability_digest: str
    mode: str
    attempt: int
    provider: str
    adapter: str
    adapter_version: str
    spec: ExecutionSpec
    schema_version: str = "ge.adapter-dispatch.v1"

    def __post_init__(self) -> None:
        if not self.invocation_id.startswith("gei-"):
            raise ValueError("invocation_id must use the gei- namespace")
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def request_id(self) -> str:
        return stable_id("ger", self)


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    invocation_id: str
    request_digest: str
    provider_invocation_id: str
    transport_status: str
    result: ResultEnvelope
    response_digest: str
    schema_version: str = "ge.provider-observation.v1"

    def __post_init__(self) -> None:
        if self.transport_status != "completed":
            raise ValueError("v0.0.2 observations support only completed transport status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class AdapterReceipt:
    invocation_id: str
    request_id: str
    request_digest: str
    session_id: str
    runner_id: str
    provider: str
    adapter: str
    adapter_version: str
    provider_invocation_id: str
    transport_status: str
    response_digest: str
    result_digest: str
    schema_version: str = "ge.adapter-receipt.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class InvocationBundle:
    request: AdapterDispatchRequest
    observation: ProviderObservation
    receipt: AdapterReceipt
    result: ResultEnvelope
    schema_version: str = "ge.invocation-bundle.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def request_to_dict(request: AdapterDispatchRequest) -> dict[str, Any]:
    return {
        "schema_version": request.schema_version,
        "invocation_id": request.invocation_id,
        "session_id": request.session_id,
        "spec_id": request.spec_id,
        "spec_digest": request.spec_digest,
        "plan_id": request.plan_id,
        "plan_digest": request.plan_digest,
        "registry_digest": request.registry_digest,
        "runner_id": request.runner_id,
        "runner_capability_digest": request.runner_capability_digest,
        "mode": request.mode,
        "attempt": request.attempt,
        "provider": request.provider,
        "adapter": request.adapter,
        "adapter_version": request.adapter_version,
        "spec": spec_to_dict(request.spec),
    }


def request_from_dict(data: dict[str, Any]) -> AdapterDispatchRequest:
    if data.get("schema_version") != "ge.adapter-dispatch.v1":
        raise AdapterError("unsupported adapter dispatch schema")
    return AdapterDispatchRequest(
        invocation_id=str(data["invocation_id"]),
        session_id=str(data["session_id"]),
        spec_id=str(data["spec_id"]),
        spec_digest=str(data["spec_digest"]),
        plan_id=str(data["plan_id"]),
        plan_digest=str(data["plan_digest"]),
        registry_digest=str(data["registry_digest"]),
        runner_id=str(data["runner_id"]),
        runner_capability_digest=str(data["runner_capability_digest"]),
        mode=str(data["mode"]),
        attempt=int(data["attempt"]),
        provider=str(data["provider"]),
        adapter=str(data["adapter"]),
        adapter_version=str(data["adapter_version"]),
        spec=spec_from_dict(data["spec"]),
    )


def _verify_static_binding(spec, registry, plan, session, runner) -> None:
    if not verify_plan(spec, registry, plan):
        raise AdapterError("dispatch plan does not reproduce")
    if runner not in registry.runners:
        raise AdapterError("runner is absent from registry")
    if session.state != "running":
        raise AdapterError("dispatch requires a running session")
    expected = (
        spec.spec_id, spec.digest, plan.plan_id, plan.digest, registry.digest,
        runner.runner_id, runner.digest, plan.mode,
    )
    actual = (
        session.spec_id, session.spec_digest, session.plan_id, session.plan_digest,
        plan.registry_digest, session.runner_id, session.runner_capability_digest, session.mode,
    )
    if actual != expected:
        raise AdapterError("spec, registry, plan, runner, and session are not exactly bound")


def build_dispatch_request(spec, registry, plan, session, runner, *, invocation_id=None):
    _verify_static_binding(spec, registry, plan, session, runner)
    return AdapterDispatchRequest(
        invocation_id=invocation_id or f"gei-{uuid.uuid4().hex}",
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        registry_digest=registry.digest,
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        mode=session.mode,
        attempt=session.attempt,
        provider=runner.provider,
        adapter=runner.adapter,
        adapter_version=runner.adapter_version,
        spec=spec,
    )


def verify_dispatch_request(spec, registry, plan, session, runner, request) -> bool:
    try:
        expected = build_dispatch_request(
            spec, registry, plan, session, runner, invocation_id=request.invocation_id
        )
    except AdapterError:
        return False
    return request == expected


def reference_evidence_digest(request: AdapterDispatchRequest) -> str:
    return sha256_digest({
        "protocol": "ge.reference-probe.v1",
        "invocation_id": request.invocation_id,
        "session_id": request.session_id,
        "spec_digest": request.spec_digest,
        "source_revision": request.spec.source_revision,
        "objective": request.spec.objective,
        "inputs": request.spec.inputs,
    })


def make_reference_observation(
    request: AdapterDispatchRequest,
    *,
    provider_invocation_id: str = "reference-observation-1",
) -> ProviderObservation:
    if request.mode != "read_only":
        raise AdapterError("reference adapter is read-only")
    if request.spec.task_kind != REFERENCE_TASK_KIND:
        raise AdapterError("reference adapter accepts only reference-probe")
    if REFERENCE_CAPABILITY not in request.spec.required_capabilities:
        raise AdapterError("reference capability must be requested")
    if set(request.spec.evidence_requirements) - {REFERENCE_EVIDENCE}:
        raise AdapterError("unsupported evidence requirement")

    from .models import ArtifactRef

    evidence = ArtifactRef(
        name=REFERENCE_EVIDENCE,
        uri=f"ge+reference://evidence/{request.invocation_id}",
        digest=reference_evidence_digest(request),
    )
    result = ResultEnvelope(
        session_id=request.session_id,
        spec_id=request.spec_id,
        spec_digest=request.spec_digest,
        runner_id=request.runner_id,
        attempt=request.attempt,
        status="completed",
        evidence=(evidence,),
        summary="Reference provider completed the bounded conformance probe.",
    )
    response_digest = sha256_digest({
        "invocation_id": request.invocation_id,
        "request_digest": request.digest,
        "provider_invocation_id": provider_invocation_id,
        "result": result_to_dict(result),
    })
    return ProviderObservation(
        invocation_id=request.invocation_id,
        request_digest=request.digest,
        provider_invocation_id=provider_invocation_id,
        transport_status="completed",
        result=result,
        response_digest=response_digest,
    )


def admit_observation(spec, registry, plan, session, runner, request, observation) -> InvocationBundle:
    if not verify_dispatch_request(spec, registry, plan, session, runner, request):
        raise AdapterError("dispatch request is not admissible")
    result = observation.result
    expected_response = sha256_digest({
        "invocation_id": request.invocation_id,
        "request_digest": request.digest,
        "provider_invocation_id": observation.provider_invocation_id,
        "result": result_to_dict(result),
    })
    if (
        observation.invocation_id != request.invocation_id
        or observation.request_digest != request.digest
        or observation.response_digest != expected_response
        or result.session_id != session.session_id
        or result.spec_id != spec.spec_id
        or result.spec_digest != spec.digest
        or result.runner_id != runner.runner_id
        or result.attempt != session.attempt
    ):
        raise AdapterError("provider observation is not bound to the exact request")

    receipt = AdapterReceipt(
        invocation_id=request.invocation_id,
        request_id=request.request_id,
        request_digest=request.digest,
        session_id=session.session_id,
        runner_id=runner.runner_id,
        provider=runner.provider,
        adapter=runner.adapter,
        adapter_version=runner.adapter_version,
        provider_invocation_id=observation.provider_invocation_id,
        transport_status=observation.transport_status,
        response_digest=observation.response_digest,
        result_digest=result.digest,
    )
    bundle = InvocationBundle(request, observation, receipt, result)
    if not verify_invocation_bundle(spec, registry, plan, session, runner, bundle):
        raise AdapterError("invocation bundle verification failed")
    return bundle


def verify_invocation_bundle(spec, registry, plan, session, runner, bundle) -> bool:
    request = bundle.request
    observation = bundle.observation
    receipt = bundle.receipt
    result = bundle.result
    if not verify_dispatch_request(spec, registry, plan, session, runner, request):
        return False
    if observation.result != result or receipt.result_digest != result.digest:
        return False
    if (
        observation.invocation_id != request.invocation_id
        or observation.request_digest != request.digest
        or receipt.invocation_id != request.invocation_id
        or receipt.request_id != request.request_id
        or receipt.request_digest != request.digest
        or receipt.provider_invocation_id != observation.provider_invocation_id
        or receipt.response_digest != observation.response_digest
        or receipt.transport_status != "completed"
    ):
        return False
    expected_response = sha256_digest({
        "invocation_id": request.invocation_id,
        "request_digest": request.digest,
        "provider_invocation_id": observation.provider_invocation_id,
        "result": result_to_dict(result),
    })
    if observation.response_digest != expected_response:
        return False
    if result.status != "completed" or len(result.evidence) != 1:
        return False
    evidence = result.evidence[0]
    return (
        result.session_id == session.session_id
        and result.spec_id == spec.spec_id
        and result.spec_digest == spec.digest
        and result.runner_id == runner.runner_id
        and result.attempt == session.attempt
        and evidence.name == REFERENCE_EVIDENCE
        and evidence.uri == f"ge+reference://evidence/{request.invocation_id}"
        and evidence.digest == reference_evidence_digest(request)
    )
