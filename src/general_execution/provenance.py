from __future__ import annotations

from dataclasses import asdict, dataclass

from .adapter import InvocationBundle, request_to_dict
from .canonical import sha256_digest, stable_id
from .ledger import ExecutionLedger, append_event, verify_ledger
from .wire import result_to_dict


@dataclass(frozen=True, slots=True)
class InvocationRecord:
    invocation_id: str
    bundle_digest: str
    first_event_index: int
    last_event_index: int
    recorded_head: str
    schema_version: str = "ge.invocation-record.v1"

    @property
    def record_id(self) -> str:
        return stable_id("geq", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _payloads(bundle: InvocationBundle):
    return (
        ("ADAPTER_DISPATCH", {"request": request_to_dict(bundle.request), "request_digest": bundle.request.digest}),
        ("PROVIDER_OBSERVATION", {"observation": asdict(bundle.observation), "observation_digest": bundle.observation.digest}),
        ("ADAPTER_RECEIPT", {"receipt": asdict(bundle.receipt), "receipt_digest": bundle.receipt.digest}),
        ("ADAPTER_RESULT", {"result": result_to_dict(bundle.result), "result_digest": bundle.result.digest}),
    )


def record_invocation(ledger: ExecutionLedger, bundle: InvocationBundle):
    first = len(ledger.events)
    current = ledger
    for event_type, payload in _payloads(bundle):
        current = append_event(current, event_type, payload)
    return current, InvocationRecord(
        invocation_id=bundle.request.invocation_id,
        bundle_digest=bundle.digest,
        first_event_index=first,
        last_event_index=first + 3,
        recorded_head=current.head,
    )


def verify_invocation_record(ledger, bundle, record) -> bool:
    if not verify_ledger(ledger):
        return False
    if record.invocation_id != bundle.request.invocation_id or record.bundle_digest != bundle.digest:
        return False
    if record.last_event_index != record.first_event_index + 3:
        return False
    if record.first_event_index < 0 or record.last_event_index >= len(ledger.events):
        return False
    actual = ledger.events[record.first_event_index:record.last_event_index + 1]
    expected = _payloads(bundle)
    if len(actual) != 4:
        return False
    for event, (event_type, payload) in zip(actual, expected, strict=True):
        if event.event_type != event_type or event.payload != payload:
            return False
    return actual[-1].event_hash == record.recorded_head
