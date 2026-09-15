from __future__ import annotations

from .models import DispatchPlan, ExecutionMode, ExecutionSpec, RunnerCapabilities, RunnerRegistry


def _compatible(spec: ExecutionSpec, runner: RunnerCapabilities, mode: ExecutionMode) -> bool:
    return mode in runner.modes and set(spec.required_capabilities).issubset(runner.capabilities)


def plan_execution(spec: ExecutionSpec, registry: RunnerRegistry, mode: ExecutionMode = "read_only") -> DispatchPlan:
    compatible = sorted(
        (runner for runner in registry.runners if _compatible(spec, runner, mode)),
        key=lambda runner: (runner.runner_id, runner.digest),
    )
    if not compatible:
        return DispatchPlan(
            spec_id=spec.spec_id,
            spec_digest=spec.digest,
            registry_digest=registry.digest,
            mode=mode,
            runner_id=None,
            runner_capability_digest=None,
            deferral_reason="no_compatible_runner",
        )

    chosen = compatible[0]
    return DispatchPlan(
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        registry_digest=registry.digest,
        mode=mode,
        runner_id=chosen.runner_id,
        runner_capability_digest=chosen.digest,
        deferral_reason=None,
    )


def verify_plan(spec: ExecutionSpec, registry: RunnerRegistry, plan: DispatchPlan) -> bool:
    return plan == plan_execution(spec, registry, plan.mode)
