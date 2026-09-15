from __future__ import annotations

import json
from dataclasses import dataclass, replace

from .adapter import REFERENCE_ADAPTER, REFERENCE_CAPABILITY, REFERENCE_PROVIDER, reference_runner
from .canonical import canonical_json, sha256_digest
from .models import RunnerCapabilities
from .physical import PhysicalObservation
from .reattachment import (
    PROVIDER_REATTACHMENT_CAPABILITY,
    ProviderReattachmentKey,
    ProviderStatusObservation,
    ProviderStatusProbe,
    observe_provider_not_found,
    observe_provider_running,
    observe_provider_terminal,
    reattachment_key_from_authorization,
)
from .reference_registry import (
    ReferenceRegistryConflict,
    ReferenceRegistryIntegrityError,
    SQLiteReferenceJobRegistry,
)
from .wire import result_from_dict, result_to_dict


class ReferenceBridgeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReferenceRegistrationReceipt:
    provider_key: str
    job_id: str
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    idempotent: bool
    schema_version: str = "ge.reference-registration-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.reference-registration-receipt.v1":
            raise ValueError("unsupported reference registration receipt schema")
        for name in ("provider_key", "job_id", "authorization_id", "authorization_digest", "invocation_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def reattachable_reference_runner(runner_id: str = "reference-runner-1") -> RunnerCapabilities:
    base = reference_runner(runner_id)
    return replace(base, capabilities=(REFERENCE_CAPABILITY, PROVIDER_REATTACHMENT_CAPABILITY))


def _verify_runner(runner: RunnerCapabilities) -> None:
    if (
        runner.provider != REFERENCE_PROVIDER
        or runner.adapter != REFERENCE_ADAPTER
        or REFERENCE_CAPABILITY not in runner.capabilities
        or PROVIDER_REATTACHMENT_CAPABILITY not in runner.capabilities
    ):
        raise ReferenceBridgeError("runner is not a reattachable reference runner")


def _physical_to_dict(observation: PhysicalObservation) -> dict:
    return {
        "schema_version": observation.schema_version,
        "authorization_id": observation.authorization_id,
        "invocation_id": observation.invocation_id,
        "request_digest": observation.request_digest,
        "provider_invocation_id": observation.provider_invocation_id,
        "transport_status": observation.transport_status,
        "result": result_to_dict(observation.result) if observation.result else None,
        "failure_code": observation.failure_code,
        "detail_digest": observation.detail_digest,
        "response_digest": observation.response_digest,
    }


def _physical_from_dict(data: dict) -> PhysicalObservation:
    if data.get("schema_version") != "ge.physical-observation.v1":
        raise ReferenceRegistryIntegrityError("unsupported terminal observation schema")
    try:
        result_data = data.get("result")
        return PhysicalObservation(
            authorization_id=str(data["authorization_id"]),
            invocation_id=str(data["invocation_id"]),
            request_digest=str(data["request_digest"]),
            provider_invocation_id=(
                str(data["provider_invocation_id"]) if data.get("provider_invocation_id") is not None else None
            ),
            transport_status=str(data["transport_status"]),
            result=result_from_dict(result_data) if result_data is not None else None,
            failure_code=str(data["failure_code"]) if data.get("failure_code") is not None else None,
            detail_digest=str(data["detail_digest"]) if data.get("detail_digest") is not None else None,
            response_digest=str(data["response_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceRegistryIntegrityError("invalid terminal observation payload") from exc


def register_reference_invocation(
    registry: SQLiteReferenceJobRegistry,
    authorization,
    runner: RunnerCapabilities,
) -> tuple[ProviderReattachmentKey, ReferenceRegistrationReceipt]:
    _verify_runner(runner)
    try:
        key = reattachment_key_from_authorization(authorization, runner)
    except ValueError as exc:
        raise ReferenceBridgeError("authorization cannot produce reference reattachment key") from exc
    record, idempotent = registry.register(key)
    return key, ReferenceRegistrationReceipt(
        provider_key=key.provider_key,
        job_id=record.job_id,
        authorization_id=key.authorization_id,
        authorization_digest=key.authorization_digest,
        invocation_id=key.invocation_id,
        idempotent=idempotent,
    )


def query_reference_status(
    registry: SQLiteReferenceJobRegistry,
    probe: ProviderStatusProbe,
) -> ProviderStatusObservation:
    key = probe.reattachment_key
    if key.provider != REFERENCE_PROVIDER or key.adapter != REFERENCE_ADAPTER:
        raise ReferenceBridgeError("status probe is not for the reference provider")
    record = registry.lookup(key)
    if record is None:
        return observe_provider_not_found(probe)
    if record.state == "running":
        return observe_provider_running(probe, provider_invocation_id=record.job_id)
    if record.state != "terminal" or record.terminal_payload is None or record.terminal_payload_digest is None:
        raise ReferenceRegistryIntegrityError("reference job has inconsistent terminal state")
    if sha256_digest(record.terminal_payload) != record.terminal_payload_digest:
        raise ReferenceRegistryIntegrityError("stored terminal payload digest mismatch")
    try:
        data = json.loads(record.terminal_payload)
    except json.JSONDecodeError as exc:
        raise ReferenceRegistryIntegrityError("stored terminal payload is not valid JSON") from exc
    physical = _physical_from_dict(data)
    if physical.provider_invocation_id != record.job_id:
        raise ReferenceRegistryIntegrityError("terminal observation job id mismatch")
    return observe_provider_terminal(probe, physical)


def record_reference_terminal(
    registry: SQLiteReferenceJobRegistry,
    key: ProviderReattachmentKey,
    observation: PhysicalObservation,
) -> bool:
    record = registry.lookup(key)
    if record is None:
        raise ReferenceRegistryConflict("reference job does not exist")
    if (
        observation.authorization_id != key.authorization_id
        or observation.invocation_id != key.invocation_id
        or observation.provider_invocation_id != record.job_id
    ):
        raise ReferenceRegistryConflict("terminal observation does not belong to reference job")
    payload = canonical_json(_physical_to_dict(observation))
    return registry.mark_terminal(key, payload=payload, payload_digest=sha256_digest(payload))
