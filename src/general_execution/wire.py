from __future__ import annotations

from typing import Any

from .models import ArtifactRef, ExecutionSession, ExecutionSpec, ResultEnvelope


def artifact_to_dict(artifact: ArtifactRef) -> dict[str, Any]:
    return {"name": artifact.name, "uri": artifact.uri, "digest": artifact.digest}


def artifact_from_dict(data: dict[str, Any]) -> ArtifactRef:
    return ArtifactRef(name=str(data["name"]), uri=str(data["uri"]), digest=str(data["digest"]))


def spec_to_dict(spec: ExecutionSpec) -> dict[str, Any]:
    return {
        "schema_version": spec.schema_version,
        "producer": spec.producer,
        "producer_revision": spec.producer_revision,
        "task_kind": spec.task_kind,
        "objective": spec.objective,
        "source_revision": spec.source_revision,
        "required_capabilities": list(spec.required_capabilities),
        "allowed_scopes": list(spec.allowed_scopes),
        "forbidden_actions": list(spec.forbidden_actions),
        "evidence_requirements": list(spec.evidence_requirements),
        "inputs": [artifact_to_dict(item) for item in spec.inputs],
        "authority_ref": artifact_to_dict(spec.authority_ref) if spec.authority_ref else None,
        "metadata": [[key, value] for key, value in spec.metadata],
    }


def spec_from_dict(data: dict[str, Any]) -> ExecutionSpec:
    if data.get("schema_version", "ge.execution-spec.v1") != "ge.execution-spec.v1":
        raise ValueError("unsupported execution spec schema")
    authority = data.get("authority_ref")
    return ExecutionSpec(
        producer=str(data["producer"]),
        producer_revision=str(data["producer_revision"]),
        task_kind=str(data["task_kind"]),
        objective=str(data["objective"]),
        source_revision=str(data["source_revision"]),
        required_capabilities=tuple(str(item) for item in data.get("required_capabilities", [])),
        allowed_scopes=tuple(str(item) for item in data.get("allowed_scopes", [])),
        forbidden_actions=tuple(str(item) for item in data.get("forbidden_actions", [])),
        evidence_requirements=tuple(str(item) for item in data.get("evidence_requirements", [])),
        inputs=tuple(artifact_from_dict(item) for item in data.get("inputs", [])),
        authority_ref=artifact_from_dict(authority) if authority else None,
        metadata=tuple((str(key), str(value)) for key, value in data.get("metadata", [])),
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
    if data.get("schema_version") != "ge.execution-session.v1":
        raise ValueError("unsupported execution session schema")
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
        result_digest=str(data["result_digest"]) if data.get("result_digest") is not None else None,
    )


def result_to_dict(result: ResultEnvelope) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "session_id": result.session_id,
        "spec_id": result.spec_id,
        "spec_digest": result.spec_digest,
        "runner_id": result.runner_id,
        "attempt": result.attempt,
        "status": result.status,
        "output_artifacts": [artifact_to_dict(item) for item in result.output_artifacts],
        "evidence": [artifact_to_dict(item) for item in result.evidence],
        "summary": result.summary,
    }


def result_from_dict(data: dict[str, Any]) -> ResultEnvelope:
    if data.get("schema_version", "ge.result-envelope.v1") != "ge.result-envelope.v1":
        raise ValueError("unsupported result envelope schema")
    return ResultEnvelope(
        session_id=str(data["session_id"]),
        spec_id=str(data["spec_id"]),
        spec_digest=str(data["spec_digest"]),
        runner_id=str(data["runner_id"]),
        attempt=int(data["attempt"]),
        status=str(data["status"]),
        output_artifacts=tuple(artifact_from_dict(item) for item in data.get("output_artifacts", [])),
        evidence=tuple(artifact_from_dict(item) for item in data.get("evidence", [])),
        summary=str(data.get("summary", "")),
    )
