from __future__ import annotations

from dataclasses import replace

from .models import DispatchPlan, ExecutionSession, ExecutionSpec, ResultEnvelope, RunnerRegistry
from .planner import verify_plan


class SessionError(ValueError):
    pass


def bind_session(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    *,
    attempt: int = 1,
) -> ExecutionSession:
    if not verify_plan(spec, registry, plan):
        raise SessionError("dispatch plan does not reproduce from the supplied spec and registry")
    if plan.runner_id is None or plan.runner_capability_digest is None:
        raise SessionError("cannot bind a deferred dispatch plan")
    return ExecutionSession(
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        plan_id=plan.plan_id,
        plan_digest=plan.digest,
        runner_id=plan.runner_id,
        runner_capability_digest=plan.runner_capability_digest,
        mode=plan.mode,
        attempt=attempt,
    )


def start_session(session: ExecutionSession) -> ExecutionSession:
    if session.state != "bound":
        raise SessionError("only a bound session can start")
    return replace(session, state="running")


def revoke_session(session: ExecutionSession) -> ExecutionSession:
    if session.state not in {"bound", "running"}:
        raise SessionError("only a bound or running session can be revoked")
    return replace(session, state="revoked")


def submit_result(session: ExecutionSession, result: ResultEnvelope) -> ExecutionSession:
    if session.state != "running":
        raise SessionError("only a running session can submit a result")
    expected = {
        "session_id": session.session_id,
        "spec_id": session.spec_id,
        "spec_digest": session.spec_digest,
        "runner_id": session.runner_id,
        "attempt": session.attempt,
    }
    actual = {
        "session_id": result.session_id,
        "spec_id": result.spec_id,
        "spec_digest": result.spec_digest,
        "runner_id": result.runner_id,
        "attempt": result.attempt,
    }
    if actual != expected:
        raise SessionError("result is not bound to the exact active session")
    return replace(session, state="result_submitted", result_digest=result.digest)
