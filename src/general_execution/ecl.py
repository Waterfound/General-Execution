from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Mapping

from .canonical import canonical_json, sha256_digest
from .models import ExecutionSpec


ECL_VERSION = "0.1"
ECL_METADATA_PREFIX = "ecl."
BOUND_FIELDS = {"context_manifest", "context_sidecar", "binding_digest", "grants_authority"}
SIDECAR_FIELDS = {
    "context_version", "project_id", "repository", "project_revision",
    "prompt_digest", "manifest_digest", "adapter_id", "adapter_version",
    "grants_authority",
}
REQUIRED_AUTHORIZATION = {
    "scope_type": "user-owned-project",
    "external_targets": False,
    "grants_authority": False,
    "authority_source": "target-owned",
}
REQUIRED_CONSTRAINTS = {
    "safeguard_bypass": False,
    "external_intrusion": False,
    "credential_acquisition": False,
    "external_persistence": False,
}


class ECLCarrierError(ValueError):
    pass


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ECLCarrierError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ECLCarrierError(f"{name} must contain 64 hexadecimal characters") from exc
    if value[7:] != value[7:].lower():
        raise ECLCarrierError(f"{name} must use lowercase hex")
    return value


def validate_bound_context(bound: Mapping[str, Any]) -> dict[str, str | bool]:
    if not isinstance(bound, Mapping) or set(bound) != BOUND_FIELDS:
        raise ECLCarrierError("ECL bound context fields mismatch")
    if bound["grants_authority"] is not False:
        raise ECLCarrierError("ECL cannot grant authority")

    manifest = bound["context_manifest"]
    if not isinstance(manifest, Mapping):
        raise ECLCarrierError("ECL manifest must be an object")
    required_manifest = {
        "context_version", "project_id", "repository", "project_revision", "domain",
        "purpose", "terminology", "authorization", "constraints", "related_systems",
    }
    if not required_manifest.issubset(manifest):
        raise ECLCarrierError("ECL manifest is incomplete")
    if set(manifest) - (required_manifest | {"metadata"}):
        raise ECLCarrierError("ECL manifest contains unknown fields")
    if manifest["context_version"] != ECL_VERSION:
        raise ECLCarrierError("unsupported ECL context version")
    if dict(manifest["authorization"]) != REQUIRED_AUTHORIZATION:
        raise ECLCarrierError("ECL authorization contract mismatch")
    if dict(manifest["constraints"]) != REQUIRED_CONSTRAINTS:
        raise ECLCarrierError("ECL safety contract mismatch")
    for name in ("project_id", "repository", "project_revision", "domain", "purpose"):
        if not isinstance(manifest[name], str) or not manifest[name]:
            raise ECLCarrierError(f"ECL {name} must be non-empty")
    if not isinstance(manifest["terminology"], Mapping):
        raise ECLCarrierError("ECL terminology must be an object")
    if not isinstance(manifest["related_systems"], list):
        raise ECLCarrierError("ECL related_systems must be a list")

    sidecar = bound["context_sidecar"]
    if not isinstance(sidecar, Mapping) or set(sidecar) != SIDECAR_FIELDS:
        raise ECLCarrierError("ECL sidecar fields mismatch")
    _sha256(sidecar["prompt_digest"], "ECL prompt_digest")
    _sha256(sidecar["manifest_digest"], "ECL manifest_digest")
    _sha256(bound["binding_digest"], "ECL binding_digest")
    if sidecar["context_version"] != ECL_VERSION or sidecar["grants_authority"] is not False:
        raise ECLCarrierError("ECL sidecar authority/version mismatch")
    for name in ("project_id", "repository", "project_revision"):
        if sidecar[name] != manifest[name]:
            raise ECLCarrierError(f"ECL {name} binding mismatch")
    if sidecar["manifest_digest"] != sha256_digest(manifest):
        raise ECLCarrierError("ECL manifest digest mismatch")
    if bound["binding_digest"] != sha256_digest(sidecar):
        raise ECLCarrierError("ECL binding digest mismatch")
    if not isinstance(sidecar["adapter_id"], str) or not sidecar["adapter_id"]:
        raise ECLCarrierError("ECL adapter_id must be non-empty")
    if not isinstance(sidecar["adapter_version"], str) or not sidecar["adapter_version"]:
        raise ECLCarrierError("ECL adapter_version must be non-empty")

    return {
        "context_version": ECL_VERSION,
        "manifest_digest": sidecar["manifest_digest"],
        "binding_digest": bound["binding_digest"],
        "prompt_digest": sidecar["prompt_digest"],
        "adapter_id": sidecar["adapter_id"],
        "adapter_version": sidecar["adapter_version"],
        "grants_authority": False,
    }


def ecl_metadata(bound: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    receipt = validate_bound_context(bound)
    manifest_json = canonical_json(bound["context_manifest"])
    return (
        ("ecl.context_version", str(receipt["context_version"])),
        ("ecl.manifest", manifest_json),
        ("ecl.manifest_digest", str(receipt["manifest_digest"])),
        ("ecl.binding_digest", str(receipt["binding_digest"])),
        ("ecl.prompt_digest", str(receipt["prompt_digest"])),
        ("ecl.adapter_id", str(receipt["adapter_id"])),
        ("ecl.adapter_version", str(receipt["adapter_version"])),
        ("ecl.grants_authority", "false"),
    )


def attach_ecl_context(spec: ExecutionSpec, bound: Mapping[str, Any]) -> ExecutionSpec:
    """Carry ECL through General Execution as immutable metadata, never authority."""
    existing = dict(spec.metadata)
    if any(key.startswith(ECL_METADATA_PREFIX) for key in existing):
        raise ECLCarrierError("ExecutionSpec already contains ECL metadata")
    metadata = tuple(sorted((*spec.metadata, *ecl_metadata(bound)), key=lambda item: item[0]))
    return replace(spec, metadata=metadata)


def validate_spec_ecl(spec: ExecutionSpec) -> dict[str, Any] | None:
    values = dict(spec.metadata)
    ecl_values = {key: value for key, value in values.items() if key.startswith(ECL_METADATA_PREFIX)}
    if not ecl_values:
        return None
    required = {
        "ecl.context_version", "ecl.manifest", "ecl.manifest_digest", "ecl.binding_digest",
        "ecl.prompt_digest", "ecl.adapter_id", "ecl.adapter_version", "ecl.grants_authority",
    }
    if set(ecl_values) != required:
        raise ECLCarrierError("ExecutionSpec ECL metadata fields mismatch")
    if ecl_values["ecl.context_version"] != ECL_VERSION:
        raise ECLCarrierError("ExecutionSpec ECL version mismatch")
    if ecl_values["ecl.grants_authority"] != "false":
        raise ECLCarrierError("ExecutionSpec ECL metadata cannot grant authority")
    try:
        manifest = json.loads(ecl_values["ecl.manifest"])
    except json.JSONDecodeError as exc:
        raise ECLCarrierError("ExecutionSpec ECL manifest is not valid JSON") from exc
    if canonical_json(manifest) != ecl_values["ecl.manifest"]:
        raise ECLCarrierError("ExecutionSpec ECL manifest is not canonical")
    if sha256_digest(manifest) != ecl_values["ecl.manifest_digest"]:
        raise ECLCarrierError("ExecutionSpec ECL manifest digest mismatch")
    for key in ("ecl.manifest_digest", "ecl.binding_digest", "ecl.prompt_digest"):
        _sha256(ecl_values[key], key)
    return {
        "context_version": ECL_VERSION,
        "manifest_digest": ecl_values["ecl.manifest_digest"],
        "binding_digest": ecl_values["ecl.binding_digest"],
        "prompt_digest": ecl_values["ecl.prompt_digest"],
        "grants_authority": False,
        "context_carried": True,
    }
