from __future__ import annotations

import re
from typing import Any, Mapping

from .canonical import canonical_json, sha256_digest, stable_id
from .models import ArtifactRef, ExecutionSpec

BRIDGE_VERSION = "0.1"
SOURCE_ARTIFACT_TYPE = "build_colony_session_dispatch_request"
ADMISSION_ARTIFACT_TYPE = "general_execution_admission_receipt"
CLIENT_CAPABILITY = "build_colony.session-dispatch.v1"
SOURCE_SYSTEM = "build_colony"
SOURCE_REPOSITORY = "Waterfound/Build-Colony"
PRODUCER_SYSTEM = "general_execution"
PRODUCER_REPOSITORY = "Waterfound/General-Execution"
REV_RE = re.compile(r"^[A-Za-z0-9._:-]{7,128}$")
RAW_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class BuildColonyBridgeError(ValueError):
    pass


def _revision(value: str, field: str) -> str:
    if not isinstance(value, str) or not REV_RE.fullmatch(value):
        raise BuildColonyBridgeError(f"{field} is not a pinned revision identifier")
    return value


def _raw_digest(value: Any) -> str:
    return sha256_digest(value).split(":", 1)[1]


def _require_unique_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise BuildColonyBridgeError(f"{field} must be a list of strings")
    if len(value) != len(set(value)):
        raise BuildColonyBridgeError(f"{field} must not contain duplicates")
    return tuple(value)


def _validate_artifact(
    artifact: Mapping[str, Any], *, expected_producer_revision: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_producer_revision = _revision(
        expected_producer_revision, "expected_producer_revision"
    )
    required = {
        "schema_version", "artifact_type", "producer_system", "producer_repository",
        "producer_revision", "capabilities", "request", "execution_semantics", "artifact_digest",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise BuildColonyBridgeError("Build Colony dispatch artifact field set mismatch")
    if artifact["schema_version"] != "bc.ge-session-dispatch.v1":
        raise BuildColonyBridgeError("unsupported Build Colony dispatch artifact schema")
    if artifact["artifact_type"] != SOURCE_ARTIFACT_TYPE:
        raise BuildColonyBridgeError("Build Colony dispatch artifact type mismatch")
    if (
        artifact["producer_system"] != SOURCE_SYSTEM
        or artifact["producer_repository"] != SOURCE_REPOSITORY
    ):
        raise BuildColonyBridgeError("Build Colony producer identity mismatch")
    if artifact["producer_revision"] != expected_producer_revision:
        raise BuildColonyBridgeError("Build Colony producer revision mismatch")
    core = dict(artifact)
    artifact_digest = core.pop("artifact_digest")
    if artifact_digest != sha256_digest(core):
        raise BuildColonyBridgeError("Build Colony dispatch artifact digest mismatch")

    semantics = artifact["execution_semantics"]
    expected_semantics = {
        "requires_build_colony_bind_before_physical_execution": True,
        "verification_authorized": False,
        "integration_authorized": False,
        "promotion_authorized": False,
    }
    if semantics != expected_semantics:
        raise BuildColonyBridgeError("Build Colony execution semantics mismatch")

    capabilities = artifact["capabilities"]
    cap_fields = {
        "adapter_id", "provider", "adapter_version", "modes", "supports_write",
        "supports_artifact_refs", "max_parallelism", "capability_digest",
    }
    if not isinstance(capabilities, Mapping) or set(capabilities) != cap_fields:
        raise BuildColonyBridgeError("Build Colony bridge capabilities field set mismatch")
    if (
        capabilities["adapter_id"] != "general-execution-bridge"
        or capabilities["provider"] != "general-execution"
    ):
        raise BuildColonyBridgeError("Build Colony bridge capability identity mismatch")
    if capabilities["adapter_version"] != BRIDGE_VERSION:
        raise BuildColonyBridgeError("Build Colony bridge adapter version mismatch")
    modes = _require_unique_strings(capabilities["modes"], "capabilities.modes")
    if "execute" not in modes:
        raise BuildColonyBridgeError("Build Colony bridge lacks execute mode")
    if (
        capabilities["supports_artifact_refs"] is not True
        or int(capabilities["max_parallelism"]) < 1
    ):
        raise BuildColonyBridgeError("Build Colony bridge capability declaration is invalid")
    cap_core = dict(capabilities)
    cap_digest = str(cap_core.pop("capability_digest"))
    if not RAW_SHA_RE.fullmatch(cap_digest) or cap_digest != _raw_digest(cap_core):
        raise BuildColonyBridgeError("Build Colony bridge capability digest mismatch")

    request = artifact["request"]
    request_fields = {
        "schema_version", "session_protocol_version", "dispatch_id", "dispatch_attempt",
        "run_id", "manifest_digest", "source_revision", "package_id", "package_digest",
        "domain_id", "adapter_id", "provider", "capability_digest", "mode", "objective",
        "dependencies", "write_scopes", "exclusive_resources", "invariants",
        "forbidden_actions", "gates", "request_digest",
    }
    if not isinstance(request, Mapping) or set(request) != request_fields:
        raise BuildColonyBridgeError("Build Colony session dispatch request field set mismatch")
    if int(request["schema_version"]) != 1 or request["session_protocol_version"] != "0.0.5":
        raise BuildColonyBridgeError("unsupported Build Colony session dispatch version")
    if int(request["dispatch_attempt"]) < 1:
        raise BuildColonyBridgeError("dispatch_attempt must be >= 1")
    for field in ("manifest_digest", "package_digest", "capability_digest", "request_digest"):
        value = str(request[field])
        if not RAW_SHA_RE.fullmatch(value):
            raise BuildColonyBridgeError(
                f"request.{field} must be a lowercase 64-hex digest"
            )
    for field in (
        "dispatch_id", "run_id", "source_revision", "package_id", "domain_id", "objective"
    ):
        if not isinstance(request[field], str) or not request[field].strip():
            raise BuildColonyBridgeError(f"request.{field} must be non-empty")
    if (
        request["adapter_id"] != capabilities["adapter_id"]
        or request["provider"] != capabilities["provider"]
    ):
        raise BuildColonyBridgeError("session dispatch adapter/provider mismatch")
    if request["capability_digest"] != cap_digest:
        raise BuildColonyBridgeError("session dispatch capability digest mismatch")
    if request["mode"] != "execute":
        raise BuildColonyBridgeError("Build Colony bridge supports only execute mode")
    if request["write_scopes"] and capabilities["supports_write"] is not True:
        raise BuildColonyBridgeError("bridge capabilities do not permit required write scopes")

    for field in (
        "dependencies", "write_scopes", "exclusive_resources", "invariants", "forbidden_actions"
    ):
        _require_unique_strings(request[field], f"request.{field}")
    if not isinstance(request["gates"], list):
        raise BuildColonyBridgeError("request.gates must be a list")
    gate_ids: list[str] = []
    for index, gate in enumerate(request["gates"]):
        if (
            not isinstance(gate, Mapping)
            or set(gate) != {"id", "description", "accepted_kinds", "minimum"}
        ):
            raise BuildColonyBridgeError(f"request.gates[{index}] field set mismatch")
        gate_id = str(gate["id"])
        if not gate_id:
            raise BuildColonyBridgeError(f"request.gates[{index}].id is empty")
        if int(gate["minimum"]) < 1:
            raise BuildColonyBridgeError(f"request.gates[{index}].minimum must be >= 1")
        _require_unique_strings(
            gate["accepted_kinds"], f"request.gates[{index}].accepted_kinds"
        )
        gate_ids.append(gate_id)
    if len(gate_ids) != len(set(gate_ids)):
        raise BuildColonyBridgeError("request gate ids must be unique")

    request_core = dict(request)
    request_digest = str(request_core.pop("request_digest"))
    if not RAW_SHA_RE.fullmatch(request_digest) or request_digest != _raw_digest(request_core):
        raise BuildColonyBridgeError("Build Colony session dispatch request digest mismatch")
    seed = {
        "session_protocol_version": request["session_protocol_version"],
        "run_id": request["run_id"],
        "manifest_digest": request["manifest_digest"],
        "source_revision": request["source_revision"],
        "package_id": request["package_id"],
        "package_digest": request["package_digest"],
        "adapter_id": request["adapter_id"],
        "provider": request["provider"],
        "capability_digest": request["capability_digest"],
        "mode": request["mode"],
        "dispatch_attempt": request["dispatch_attempt"],
    }
    if request["dispatch_id"] != f"bcs-{_raw_digest(seed)[:20]}":
        raise BuildColonyBridgeError("Build Colony session dispatch_id mismatch")
    return dict(capabilities), dict(request)


def _gate_requirement(gate: Mapping[str, Any]) -> str:
    kinds = ",".join(str(item) for item in gate["accepted_kinds"])
    return f"{gate['id']}|minimum={int(gate['minimum'])}|kinds={kinds}"


def admit_build_colony_dispatch(
    artifact: Mapping[str, Any],
    *,
    expected_producer_revision: str,
    general_execution_revision: str,
) -> tuple[ExecutionSpec, dict[str, Any]]:
    """Admit a Build Colony strict session dispatch without executing it.

    The resulting spec requires a Build-Colony-aware runner capability. The
    admission receipt explicitly carries `execution_authorized=false`; physical
    execution remains blocked until the source-owned session binding is completed.
    """
    general_execution_revision = _revision(
        general_execution_revision, "general_execution_revision"
    )
    _, request = _validate_artifact(
        artifact, expected_producer_revision=expected_producer_revision
    )
    metadata = (
        ("build_colony.dispatch_attempt", str(request["dispatch_attempt"])),
        ("build_colony.dispatch_id", str(request["dispatch_id"])),
        ("build_colony.domain_id", str(request["domain_id"])),
        (
            "build_colony.exclusive_resources_json",
            canonical_json(request["exclusive_resources"]),
        ),
        ("build_colony.gates_json", canonical_json(request["gates"])),
        ("build_colony.invariants_json", canonical_json(request["invariants"])),
        ("build_colony.manifest_digest", str(request["manifest_digest"])),
        ("build_colony.package_digest", str(request["package_digest"])),
        ("build_colony.package_id", str(request["package_id"])),
        ("build_colony.request_digest", str(request["request_digest"])),
        ("build_colony.run_id", str(request["run_id"])),
        ("interop.bridge_version", BRIDGE_VERSION),
    )
    spec = ExecutionSpec(
        producer=SOURCE_SYSTEM,
        producer_revision=str(artifact["producer_revision"]),
        task_kind="build_colony_session_dispatch",
        objective=str(request["objective"]),
        source_revision=str(request["source_revision"]),
        required_capabilities=(CLIENT_CAPABILITY,),
        allowed_scopes=tuple(str(item) for item in request["write_scopes"]),
        forbidden_actions=tuple(str(item) for item in request["forbidden_actions"]),
        evidence_requirements=tuple(
            _gate_requirement(gate) for gate in request["gates"]
        ),
        authority_ref=ArtifactRef(
            name="build_colony_session_dispatch_request",
            uri=f"build-colony://{request['run_id']}/{request['dispatch_id']}",
            digest=str(artifact["artifact_digest"]),
        ),
        metadata=metadata,
    )
    receipt_core = {
        "schema_version": "ge.bc-admission.v1",
        "artifact_type": ADMISSION_ARTIFACT_TYPE,
        "producer_system": PRODUCER_SYSTEM,
        "producer_repository": PRODUCER_REPOSITORY,
        "producer_revision": general_execution_revision,
        "source_artifact_digest": str(artifact["artifact_digest"]),
        "dispatch_id": str(request["dispatch_id"]),
        "request_digest": str(request["request_digest"]),
        "spec_id": spec.spec_id,
        "spec_digest": spec.digest,
        "accepted": True,
        "execution_authorized": False,
        "verification_authorized": False,
        "integration_authorized": False,
        "promotion_authorized": False,
    }
    pending_id = stable_id("gebc", receipt_core)
    receipt_core = {**receipt_core, "pending_id": pending_id}
    return spec, {**receipt_core, "receipt_digest": sha256_digest(receipt_core)}
