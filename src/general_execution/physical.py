from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Literal

from .adapter import AdapterDispatchRequest, build_dispatch_request, verify_dispatch_request
from .canonical import sha256_digest, stable_id
from .ledger import ExecutionLedger, append_event, verify_ledger
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, ResultEnvelope, RunnerCapabilities, RunnerRegistry
from .wire import result_to_dict

TransportStatus = Literal["completed", "rejected", "timed_out", "cancelled", "transport_failed"]
VALID_TRANSPORT_STATUSES = frozenset({"completed", "rejected", "timed_out", "cancelled", "transport_failed"})
FAILURE_TRANSPORT_STATUSES = frozenset({"rejected", "timed_out", "cancelled", "transport_failed"})


class PhysicalAttemptError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PhysicalAttemptAuthorization:
    request: AdapterDispatchRequest
    physical_attempt: int
    previous_invocation_id: str | None = None
    previous_receipt_digest: str | None = None
    schema_version: str = "ge.physical-authorization.v1"

    def __post_init__(self) -> None:
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        first = self.physical_attempt == 1
        if first and (self.previous_invocation_id is not None or self.previous_receipt_digest is not None):
            raise ValueError("first physical attempt cannot have a predecessor")
        if not first and (self.previous_invocation_id is None or self.previous_receipt_digest is None):
            raise ValueError("retry physical attempt requires predecessor bindings")
        if self.previous_receipt_digest is not None:
            if not self.previous_receipt_digest.startswith("sha256:") or len(self.previous_receipt_digest) != 71:
                raise ValueError("previous_receipt_digest must be sha256:<64-hex>")
            try:
                int(self.previous_receipt_digest[7:], 16)
            except ValueError as exc:
                raise ValueError("previous_receipt_digest must contain 64 hexadecimal characters") from exc

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def authorization_id(self) -> str:
        return stable_id("gea", self)


@dataclass(frozen=True, slots=True)
class PhysicalObservation:
    authorization_id: str
    invocation_id: str
    request_digest: str
    provider_invocation_id: str | None
    transport_status: TransportStatus
    result: ResultEnvelope | None
    failure_code: str | None
    detail_digest: str | None
    response_digest: str
    schema_version: str = "ge.physical-observation.v1"

    def __post_init__(self) -> None:
        if self.transport_status not in VALID_TRANSPORT_STATUSES:
            raise ValueError("unsupported transport_status")
        if self.transport_status == "completed":
            if self.result is None:
                raise ValueError("completed observation requires a result")
            if self.failure_code is not None:
                raise ValueError("completed observation cannot carry failure_code")
            if not self.provider_invocation_id or not self.provider_invocation_id.strip():
                raise ValueError("completed observation requires provider_invocation_id")
        else:
            if self.result is not None:
                raise ValueError("failed transport observation cannot carry a result")
            if not self.failure_code or not self.failure_code.strip():
                raise ValueError("failed transport observation requires failure_code")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PhysicalReceipt:
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    previous_invocation_id: str | None
    previous_receipt_digest: str | None
    session_id: str
    runner_id: str
    provider: str
    adapter: str
    adapter_version: str
    provider_invocation_id: str | None
    transport_status: TransportStatus
    response_digest: str
    observation_digest: str
    result_digest: str | None
    failure_code: str | None
    schema_version: str = "ge.physical-receipt.v1"

    def __post_init__(self) -> None:
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        if self.transport_status not in VALID_TRANSPORT_STATUSES:
            raise ValueError("unsupported transport_status")
        if self.transport_status == "completed":
            if self.result_digest is None or self.failure_code is not None:
                raise ValueError("completed receipt requires result_digest and no failure_code")
        else:
            if self.result_digest is not None or not self.failure_code:
                raise ValueError("failure receipt requires failure_code and no result_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PhysicalOutcomeBundle:
    authorization: PhysicalAttemptAuthorization
    observation: PhysicalObservation
    receipt: PhysicalReceipt
    result: ResultEnvelope | None
    schema_version: str = "ge.physical-outcome.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class DuplicatePhysicalAttempt:
    authorization_id: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    canonical_observation_digest: str
    duplicate_observation_digest: str
    canonical_provider_invocation_id: str
    duplicate_provider_invocation_id: str
    schema_version: str = "ge.duplicate-physical-attempt.v1"

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class PhysicalAttemptRecord:
    authorization_id: str
    outcome_digest: str
    first_event_index: int
    last_event_index: int
    recorded_head: str
    schema_version: str = "ge.physical-attempt-record.v1"

    @property
    def record_id(self) -> str:
        return stable_id("gepr", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def authorize_physical_attempt(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    *,
    invocation_id: str | None = None,
) -> PhysicalAttemptAuthorization:
    request = build_dispatch_request(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=invocation_id or f"gei-{uuid.uuid4().hex}",
    )
    return PhysicalAttemptAuthorization(request=request, physical_attempt=1)


def authorize_retry(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    prior: PhysicalOutcomeBundle,
    *,
    invocation_id: str | None = None,
) -> PhysicalAttemptAuthorization:
    if not verify_physical_outcome(spec, registry, plan, session, runner, prior):
        raise PhysicalAttemptError("prior physical outcome is not admissible")
    if prior.receipt.transport_status == "completed":
        raise PhysicalAttemptError("cannot retry after a completed physical attempt")
    request = build_dispatch_request(
        spec,
        registry,
        plan,
        session,
        runner,
        invocation_id=invocation_id or f"gei-{uuid.uuid4().hex}",
    )
    return PhysicalAttemptAuthorization(
        request=request,
        physical_attempt=prior.authorization.physical_attempt + 1,
        previous_invocation_id=prior.authorization.request.invocation_id,
        previous_receipt_digest=prior.receipt.digest,
    )


def _response_digest(
    authorization: PhysicalAttemptAuthorization,
    *,
    provider_invocation_id: str | None,
    transport_status: TransportStatus,
    result: ResultEnvelope | None,
    failure_code: str | None,
    detail_digest: str | None,
) -> str:
    return sha256_digest(
        {
            "protocol": "ge.physical-outcome.v1",
            "authorization_id": authorization.authorization_id,
            "authorization_digest": authorization.digest,
            "invocation_id": authorization.request.invocation_id,
            "request_digest": authorization.request.digest,
            "physical_attempt": authorization.physical_attempt,
            "provider_invocation_id": provider_invocation_id,
            "transport_status": transport_status,
            "result": result_to_dict(result) if result else None,
            "failure_code": failure_code,
            "detail_digest": detail_digest,
        }
    )


def observe_completed(
    authorization: PhysicalAttemptAuthorization,
    result: ResultEnvelope,
    *,
    provider_invocation_id: str,
    detail_digest: str | None = None,
) -> PhysicalObservation:
    response_digest = _response_digest(
        authorization,
        provider_invocation_id=provider_invocation_id,
        transport_status="completed",
        result=result,
        failure_code=None,
        detail_digest=detail_digest,
    )
    return PhysicalObservation(
        authorization_id=authorization.authorization_id,
        invocation_id=authorization.request.invocation_id,
        request_digest=authorization.request.digest,
        provider_invocation_id=provider_invocation_id,
        transport_status="completed",
        result=result,
        failure_code=None,
        detail_digest=detail_digest,
        response_digest=response_digest,
    )


def observe_failure(
    authorization: PhysicalAttemptAuthorization,
    transport_status: TransportStatus,
    *,
    failure_code: str,
    provider_invocation_id: str | None = None,
    detail_digest: str | None = None,
) -> PhysicalObservation:
    if transport_status not in FAILURE_TRANSPORT_STATUSES:
        raise PhysicalAttemptError("failure observation requires a failure transport status")
    response_digest = _response_digest(
        authorization,
        provider_invocation_id=provider_invocation_id,
        transport_status=transport_status,
        result=None,
        failure_code=failure_code,
        detail_digest=detail_digest,
    )
    return PhysicalObservation(
        authorization_id=authorization.authorization_id,
        invocation_id=authorization.request.invocation_id,
        request_digest=authorization.request.digest,
        provider_invocation_id=provider_invocation_id,
        transport_status=transport_status,
        result=None,
        failure_code=failure_code,
        detail_digest=detail_digest,
        response_digest=response_digest,
    )


def _verify_result_binding(request: AdapterDispatchRequest, result: ResultEnvelope) -> bool:
    return (
        result.session_id == request.session_id
        and result.spec_id == request.spec_id
        and result.spec_digest == request.spec_digest
        and result.runner_id == request.runner_id
        and result.attempt == request.attempt
    )


def _verify_observation_against_authorization(
    authorization: PhysicalAttemptAuthorization, observation: PhysicalObservation
) -> bool:
    request = authorization.request
    expected_response = _response_digest(
        authorization,
        provider_invocation_id=observation.provider_invocation_id,
        transport_status=observation.transport_status,
        result=observation.result,
        failure_code=observation.failure_code,
        detail_digest=observation.detail_digest,
    )
    if (
        observation.authorization_id != authorization.authorization_id
        or observation.invocation_id != request.invocation_id
        or observation.request_digest != request.digest
        or observation.response_digest != expected_response
    ):
        return False
    if observation.result is not None and not _verify_result_binding(request, observation.result):
        return False
    return True


def _verify_intrinsic_outcome(bundle: PhysicalOutcomeBundle) -> bool:
    auth, obs, receipt, result = bundle.authorization, bundle.observation, bundle.receipt, bundle.result
    request = auth.request
    if obs.result != result or not _verify_observation_against_authorization(auth, obs):
        return False
    if (
        receipt.authorization_id != auth.authorization_id
        or receipt.authorization_digest != auth.digest
        or receipt.invocation_id != request.invocation_id
        or receipt.request_digest != request.digest
        or receipt.physical_attempt != auth.physical_attempt
        or receipt.previous_invocation_id != auth.previous_invocation_id
        or receipt.previous_receipt_digest != auth.previous_receipt_digest
        or receipt.session_id != request.session_id
        or receipt.runner_id != request.runner_id
        or receipt.provider != request.provider
        or receipt.adapter != request.adapter
        or receipt.adapter_version != request.adapter_version
        or receipt.provider_invocation_id != obs.provider_invocation_id
        or receipt.transport_status != obs.transport_status
        or receipt.response_digest != obs.response_digest
        or receipt.observation_digest != obs.digest
        or receipt.failure_code != obs.failure_code
    ):
        return False
    if obs.transport_status == "completed":
        return result is not None and receipt.result_digest == result.digest and _verify_result_binding(request, result)
    return result is None and receipt.result_digest is None and obs.transport_status in FAILURE_TRANSPORT_STATUSES


def admit_physical_observation(
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    authorization: PhysicalAttemptAuthorization,
    observation: PhysicalObservation,
) -> PhysicalOutcomeBundle:
    request = authorization.request
    if not verify_dispatch_request(spec, registry, plan, session, runner, request):
        raise PhysicalAttemptError("physical authorization contains an inadmissible request")
    if not _verify_observation_against_authorization(authorization, observation):
        raise PhysicalAttemptError("physical observation is not bound to the exact authorization")

    receipt = PhysicalReceipt(
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.digest,
        invocation_id=request.invocation_id,
        request_digest=request.digest,
        physical_attempt=authorization.physical_attempt,
        previous_invocation_id=authorization.previous_invocation_id,
        previous_receipt_digest=authorization.previous_receipt_digest,
        session_id=request.session_id,
        runner_id=request.runner_id,
        provider=request.provider,
        adapter=request.adapter,
        adapter_version=request.adapter_version,
        provider_invocation_id=observation.provider_invocation_id,
        transport_status=observation.transport_status,
        response_digest=observation.response_digest,
        observation_digest=observation.digest,
        result_digest=observation.result.digest if observation.result else None,
        failure_code=observation.failure_code,
    )
    bundle = PhysicalOutcomeBundle(authorization, observation, receipt, observation.result)
    if not verify_physical_outcome(spec, registry, plan, session, runner, bundle):
        raise PhysicalAttemptError("physical outcome verification failed")
    return bundle


def verify_physical_outcome(spec, registry, plan, session, runner, bundle: PhysicalOutcomeBundle) -> bool:
    if not verify_dispatch_request(spec, registry, plan, session, runner, bundle.authorization.request):
        return False
    return _verify_intrinsic_outcome(bundle)


def identify_duplicate_physical_attempt(
    authorization: PhysicalAttemptAuthorization,
    canonical_observation: PhysicalObservation,
    duplicate_observation: PhysicalObservation,
) -> DuplicatePhysicalAttempt:
    for observation in (canonical_observation, duplicate_observation):
        if not _verify_observation_against_authorization(authorization, observation):
            raise PhysicalAttemptError("observation is not bound to the physical authorization")
    a = canonical_observation.provider_invocation_id
    b = duplicate_observation.provider_invocation_id
    if not a or not b or a == b:
        raise PhysicalAttemptError("duplicate evidence requires two distinct provider invocation ids")
    if canonical_observation.digest == duplicate_observation.digest:
        raise PhysicalAttemptError("duplicate evidence must identify distinct observations")
    return DuplicatePhysicalAttempt(
        authorization_id=authorization.authorization_id,
        invocation_id=authorization.request.invocation_id,
        request_digest=authorization.request.digest,
        physical_attempt=authorization.physical_attempt,
        canonical_observation_digest=canonical_observation.digest,
        duplicate_observation_digest=duplicate_observation.digest,
        canonical_provider_invocation_id=a,
        duplicate_provider_invocation_id=b,
    )


def verify_retry_chain(outcomes: tuple[PhysicalOutcomeBundle, ...]) -> bool:
    if not outcomes:
        return False
    first = outcomes[0]
    base = (
        first.authorization.request.session_id,
        first.authorization.request.spec_id,
        first.authorization.request.spec_digest,
        first.authorization.request.runner_id,
        first.authorization.request.attempt,
    )
    seen_invocations: set[str] = set()
    for index, outcome in enumerate(outcomes, start=1):
        if not _verify_intrinsic_outcome(outcome):
            return False
        auth, receipt = outcome.authorization, outcome.receipt
        request = auth.request
        if auth.physical_attempt != index:
            return False
        if (
            request.session_id,
            request.spec_id,
            request.spec_digest,
            request.runner_id,
            request.attempt,
        ) != base:
            return False
        if request.invocation_id in seen_invocations:
            return False
        seen_invocations.add(request.invocation_id)
        if index == 1:
            if auth.previous_invocation_id is not None or auth.previous_receipt_digest is not None:
                return False
        else:
            prior = outcomes[index - 2]
            if prior.receipt.transport_status == "completed":
                return False
            if auth.previous_invocation_id != prior.authorization.request.invocation_id:
                return False
            if auth.previous_receipt_digest != prior.receipt.digest:
                return False
    return True


def _physical_payloads(bundle: PhysicalOutcomeBundle):
    terminal_type = "PHYSICAL_RESULT" if bundle.result is not None else "PHYSICAL_TERMINAL_FAILURE"
    terminal_payload = (
        {"result": result_to_dict(bundle.result), "result_digest": bundle.result.digest}
        if bundle.result is not None
        else {
            "transport_status": bundle.receipt.transport_status,
            "failure_code": bundle.receipt.failure_code,
            "receipt_digest": bundle.receipt.digest,
        }
    )
    return (
        (
            "PHYSICAL_DISPATCH",
            {
                "authorization": asdict(bundle.authorization),
                "authorization_digest": bundle.authorization.digest,
            },
        ),
        (
            "PHYSICAL_OBSERVATION",
            {"observation": asdict(bundle.observation), "observation_digest": bundle.observation.digest},
        ),
        (
            "PHYSICAL_RECEIPT",
            {"receipt": asdict(bundle.receipt), "receipt_digest": bundle.receipt.digest},
        ),
        (terminal_type, terminal_payload),
    )


def record_physical_attempt(ledger: ExecutionLedger, bundle: PhysicalOutcomeBundle):
    existing = {
        event.payload.get("authorization_digest")
        for event in ledger.events
        if event.event_type == "PHYSICAL_DISPATCH" and isinstance(event.payload, dict)
    }
    if bundle.authorization.digest in existing:
        raise PhysicalAttemptError("physical authorization is already recorded")
    first = len(ledger.events)
    current = ledger
    for event_type, payload in _physical_payloads(bundle):
        current = append_event(current, event_type, payload)
    return current, PhysicalAttemptRecord(
        authorization_id=bundle.authorization.authorization_id,
        outcome_digest=bundle.digest,
        first_event_index=first,
        last_event_index=first + 3,
        recorded_head=current.head,
    )


def verify_physical_attempt_record(ledger, bundle, record) -> bool:
    if not verify_ledger(ledger):
        return False
    if record.authorization_id != bundle.authorization.authorization_id or record.outcome_digest != bundle.digest:
        return False
    if record.last_event_index != record.first_event_index + 3:
        return False
    if record.first_event_index < 0 or record.last_event_index >= len(ledger.events):
        return False
    actual = ledger.events[record.first_event_index : record.last_event_index + 1]
    expected = _physical_payloads(bundle)
    if len(actual) != 4:
        return False
    for event, (event_type, payload) in zip(actual, expected, strict=True):
        if event.event_type != event_type or event.payload != payload:
            return False
    return actual[-1].event_hash == record.recorded_head


def record_duplicate_physical_attempt(ledger: ExecutionLedger, duplicate: DuplicatePhysicalAttempt) -> ExecutionLedger:
    return append_event(
        ledger,
        "DUPLICATE_PHYSICAL_ATTEMPT",
        {"duplicate": asdict(duplicate), "duplicate_digest": duplicate.digest},
    )
