from __future__ import annotations

from typing import Any

from .adapter import request_from_dict, request_to_dict
from .models import DispatchPlan, ExecutionSession, RunnerCapabilities, RunnerRegistry
from .physical import PhysicalAttemptAuthorization

RUNNER_CODEC_SCHEMA = "ge.runner-capabilities-codec.v1"


class ContextCodecError(ValueError):
    pass


def _schema(data: dict[str, Any], expected: str) -> None:
    if data.get("schema_version") != expected:
        raise ContextCodecError(f"schema_version must be {expected}")


def runner_to_dict(runner: RunnerCapabilities) -> dict[str, Any]:
    return {
        "schema_version": RUNNER_CODEC_SCHEMA,
        "runner_id": runner.runner_id,
        "provider": runner.provider,
        "adapter": runner.adapter,
        "adapter_version": runner.adapter_version,
        "capabilities": list(runner.capabilities),
        "modes": list(runner.modes),
        "max_parallelism": runner.max_parallelism,
    }


def runner_from_dict(data: dict[str, Any]) -> RunnerCapabilities:
    _schema(data, RUNNER_CODEC_SCHEMA)
    return RunnerCapabilities(
        runner_id=str(data["runner_id"]),
        provider=str(data["provider"]),
        adapter=str(data["adapter"]),
        adapter_version=str(data["adapter_version"]),
        capabilities=tuple(str(item) for item in data["capabilities"]),
        modes=tuple(str(item) for item in data["modes"]),
        max_parallelism=int(data["max_parallelism"]),
    )


def registry_to_dict(registry: RunnerRegistry) -> dict[str, Any]:
    return {
        "schema_version": registry.schema_version,
        "runners": [runner_to_dict(item) for item in registry.runners],
    }


def registry_from_dict(data: dict[str, Any]) -> RunnerRegistry:
    _schema(data, "ge.runner-registry.v1")
    return RunnerRegistry(tuple(runner_from_dict(item) for item in data["runners"]))


def plan_to_dict(plan: DispatchPlan) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "spec_id": plan.spec_id,
        "spec_digest": plan.spec_digest,
        "registry_digest": plan.registry_digest,
        "mode": plan.mode,
        "runner_id": plan.runner_id,
        "runner_capability_digest": plan.runner_capability_digest,
        "deferral_reason": plan.deferral_reason,
    }


def plan_from_dict(data: dict[str, Any]) -> DispatchPlan:
    _schema(data, "ge.dispatch-plan.v1")
    return DispatchPlan(
        spec_id=str(data["spec_id"]),
        spec_digest=str(data["spec_digest"]),
        registry_digest=str(data["registry_digest"]),
        mode=str(data["mode"]),
        runner_id=str(data["runner_id"]) if data["runner_id"] is not None else None,
        runner_capability_digest=(
            str(data["runner_capability_digest"])
            if data["runner_capability_digest"] is not None
            else None
        ),
        deferral_reason=str(data["deferral_reason"]) if data["deferral_reason"] is not None else None,
    )


def session_to_dict(session: ExecutionSession) -> dict[str, Any]:
    return {
        "schema_version": session.schema_version,
        "spec_id": session.spec_id,
        "spec_digest": session.spec_digest,
        "plan_id": session.plan_id,
        "plan_digest": session.plan_digest,
        "runner_id": session.runner_id,
        "runner_capability_digest": session.runner_capability_digest,
        "mode": session.mode,
        "attempt": session.attempt,
        "state": session.state,
        "result_digest": session.result_digest,
    }


def session_from_dict(data: dict[str, Any]) -> ExecutionSession:
    _schema(data, "ge.execution-session.v1")
    return ExecutionSession(
        spec_id=str(data["spec_id"]),
        spec_digest=str(data["spec_digest"]),
        plan_id=str(data["plan_id"]),
        plan_digest=str(data["plan_digest"]),
        runner_id=str(data["runner_id"]),
        runner_capability_digest=str(data["runner_capability_digest"]),
        mode=str(data["mode"]),
        attempt=int(data["attempt"]),
        state=str(data["state"]),
        result_digest=str(data["result_digest"]) if data["result_digest"] is not None else None,
    )


def authorization_to_dict(authorization: PhysicalAttemptAuthorization) -> dict[str, Any]:
    return {
        "schema_version": authorization.schema_version,
        "request": request_to_dict(authorization.request),
        "physical_attempt": authorization.physical_attempt,
        "previous_invocation_id": authorization.previous_invocation_id,
        "previous_receipt_digest": authorization.previous_receipt_digest,
    }


def authorization_from_dict(data: dict[str, Any]) -> PhysicalAttemptAuthorization:
    _schema(data, "ge.physical-authorization.v1")
    return PhysicalAttemptAuthorization(
        request=request_from_dict(data["request"]),
        physical_attempt=int(data["physical_attempt"]),
        previous_invocation_id=(
            str(data["previous_invocation_id"]) if data["previous_invocation_id"] is not None else None
        ),
        previous_receipt_digest=(
            str(data["previous_receipt_digest"]) if data["previous_receipt_digest"] is not None else None
        ),
    )
