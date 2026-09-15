from __future__ import annotations

import json
from typing import Any

from .adapter import AdapterError, request_from_dict, request_to_dict
from .canonical import canonical_json
from .physical import (
    PhysicalAttemptAuthorization,
    PhysicalObservation,
    PhysicalOutcomeBundle,
    PhysicalReceipt,
    _verify_intrinsic_outcome,
)
from .wire import result_from_dict, result_to_dict

PHYSICAL_OUTCOME_WIRE_SCHEMA = "ge.physical-outcome-wire.v1"


class PhysicalOutcomeCodecError(ValueError):
    pass


def physical_authorization_to_dict(authorization: PhysicalAttemptAuthorization) -> dict[str, Any]:
    return {
        "schema_version": authorization.schema_version,
        "request": request_to_dict(authorization.request),
        "physical_attempt": authorization.physical_attempt,
        "previous_invocation_id": authorization.previous_invocation_id,
        "previous_receipt_digest": authorization.previous_receipt_digest,
    }


def physical_authorization_from_dict(data: dict[str, Any]) -> PhysicalAttemptAuthorization:
    if not isinstance(data, dict) or data.get("schema_version") != "ge.physical-authorization.v1":
        raise PhysicalOutcomeCodecError("unsupported physical authorization schema")
    try:
        request = request_from_dict(data["request"])
        return PhysicalAttemptAuthorization(
            request=request,
            physical_attempt=int(data["physical_attempt"]),
            previous_invocation_id=(
                str(data["previous_invocation_id"])
                if data.get("previous_invocation_id") is not None
                else None
            ),
            previous_receipt_digest=(
                str(data["previous_receipt_digest"])
                if data.get("previous_receipt_digest") is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError, AdapterError) as exc:
        raise PhysicalOutcomeCodecError("invalid physical authorization payload") from exc


def physical_observation_to_dict(observation: PhysicalObservation) -> dict[str, Any]:
    return {
        "schema_version": observation.schema_version,
        "authorization_id": observation.authorization_id,
        "invocation_id": observation.invocation_id,
        "request_digest": observation.request_digest,
        "provider_invocation_id": observation.provider_invocation_id,
        "transport_status": observation.transport_status,
        "result": result_to_dict(observation.result) if observation.result is not None else None,
        "failure_code": observation.failure_code,
        "detail_digest": observation.detail_digest,
        "response_digest": observation.response_digest,
    }


def physical_observation_from_dict(data: dict[str, Any]) -> PhysicalObservation:
    if not isinstance(data, dict) or data.get("schema_version") != "ge.physical-observation.v1":
        raise PhysicalOutcomeCodecError("unsupported physical observation schema")
    try:
        result_data = data.get("result")
        result = result_from_dict(result_data) if result_data is not None else None
        return PhysicalObservation(
            authorization_id=str(data["authorization_id"]),
            invocation_id=str(data["invocation_id"]),
            request_digest=str(data["request_digest"]),
            provider_invocation_id=(
                str(data["provider_invocation_id"])
                if data.get("provider_invocation_id") is not None
                else None
            ),
            transport_status=str(data["transport_status"]),
            result=result,
            failure_code=str(data["failure_code"]) if data.get("failure_code") is not None else None,
            detail_digest=str(data["detail_digest"]) if data.get("detail_digest") is not None else None,
            response_digest=str(data["response_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PhysicalOutcomeCodecError("invalid physical observation payload") from exc


def physical_receipt_to_dict(receipt: PhysicalReceipt) -> dict[str, Any]:
    return {
        "schema_version": receipt.schema_version,
        "authorization_id": receipt.authorization_id,
        "authorization_digest": receipt.authorization_digest,
        "invocation_id": receipt.invocation_id,
        "request_digest": receipt.request_digest,
        "physical_attempt": receipt.physical_attempt,
        "previous_invocation_id": receipt.previous_invocation_id,
        "previous_receipt_digest": receipt.previous_receipt_digest,
        "session_id": receipt.session_id,
        "runner_id": receipt.runner_id,
        "provider": receipt.provider,
        "adapter": receipt.adapter,
        "adapter_version": receipt.adapter_version,
        "provider_invocation_id": receipt.provider_invocation_id,
        "transport_status": receipt.transport_status,
        "response_digest": receipt.response_digest,
        "observation_digest": receipt.observation_digest,
        "result_digest": receipt.result_digest,
        "failure_code": receipt.failure_code,
    }


def physical_receipt_from_dict(data: dict[str, Any]) -> PhysicalReceipt:
    if not isinstance(data, dict) or data.get("schema_version") != "ge.physical-receipt.v1":
        raise PhysicalOutcomeCodecError("unsupported physical receipt schema")
    try:
        return PhysicalReceipt(
            authorization_id=str(data["authorization_id"]),
            authorization_digest=str(data["authorization_digest"]),
            invocation_id=str(data["invocation_id"]),
            request_digest=str(data["request_digest"]),
            physical_attempt=int(data["physical_attempt"]),
            previous_invocation_id=(
                str(data["previous_invocation_id"])
                if data.get("previous_invocation_id") is not None
                else None
            ),
            previous_receipt_digest=(
                str(data["previous_receipt_digest"])
                if data.get("previous_receipt_digest") is not None
                else None
            ),
            session_id=str(data["session_id"]),
            runner_id=str(data["runner_id"]),
            provider=str(data["provider"]),
            adapter=str(data["adapter"]),
            adapter_version=str(data["adapter_version"]),
            provider_invocation_id=(
                str(data["provider_invocation_id"])
                if data.get("provider_invocation_id") is not None
                else None
            ),
            transport_status=str(data["transport_status"]),
            response_digest=str(data["response_digest"]),
            observation_digest=str(data["observation_digest"]),
            result_digest=str(data["result_digest"]) if data.get("result_digest") is not None else None,
            failure_code=str(data["failure_code"]) if data.get("failure_code") is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PhysicalOutcomeCodecError("invalid physical receipt payload") from exc


def physical_outcome_to_dict(outcome: PhysicalOutcomeBundle) -> dict[str, Any]:
    return {
        "schema_version": PHYSICAL_OUTCOME_WIRE_SCHEMA,
        "authorization": physical_authorization_to_dict(outcome.authorization),
        "observation": physical_observation_to_dict(outcome.observation),
        "receipt": physical_receipt_to_dict(outcome.receipt),
        "result": result_to_dict(outcome.result) if outcome.result is not None else None,
    }


def physical_outcome_from_dict(data: dict[str, Any]) -> PhysicalOutcomeBundle:
    if not isinstance(data, dict) or data.get("schema_version") != PHYSICAL_OUTCOME_WIRE_SCHEMA:
        raise PhysicalOutcomeCodecError("unsupported physical outcome wire schema")
    try:
        authorization = physical_authorization_from_dict(data["authorization"])
        observation = physical_observation_from_dict(data["observation"])
        receipt = physical_receipt_from_dict(data["receipt"])
        result_data = data.get("result")
        result = result_from_dict(result_data) if result_data is not None else None
        outcome = PhysicalOutcomeBundle(
            authorization=authorization,
            observation=observation,
            receipt=receipt,
            result=result,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, PhysicalOutcomeCodecError):
            raise
        raise PhysicalOutcomeCodecError("invalid physical outcome payload") from exc
    if not _verify_intrinsic_outcome(outcome):
        raise PhysicalOutcomeCodecError("physical outcome payload fails intrinsic verification")
    return outcome


def serialize_physical_outcome(outcome: PhysicalOutcomeBundle) -> str:
    if not _verify_intrinsic_outcome(outcome):
        raise PhysicalOutcomeCodecError("physical outcome fails intrinsic verification")
    return canonical_json(physical_outcome_to_dict(outcome))


def deserialize_physical_outcome(payload: str) -> PhysicalOutcomeBundle:
    try:
        data = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PhysicalOutcomeCodecError("physical outcome payload is not valid JSON") from exc
    outcome = physical_outcome_from_dict(data)
    if serialize_physical_outcome(outcome) != payload:
        raise PhysicalOutcomeCodecError("physical outcome payload is not canonical")
    return outcome
