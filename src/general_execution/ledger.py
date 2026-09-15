from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import sha256_digest

GENESIS = "sha256:" + "0" * 64


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    index: int
    event_type: str
    previous_hash: str
    payload: Any
    event_hash: str
    schema_version: str = "ge.ledger-event.v1"


@dataclass(frozen=True, slots=True)
class ExecutionLedger:
    events: tuple[LedgerEvent, ...] = ()
    schema_version: str = "ge.execution-ledger.v1"

    @property
    def head(self) -> str:
        return self.events[-1].event_hash if self.events else GENESIS


def _event_hash(index: int, event_type: str, previous_hash: str, payload: Any) -> str:
    return sha256_digest(
        {
            "schema_version": "ge.ledger-event.v1",
            "index": index,
            "event_type": event_type,
            "previous_hash": previous_hash,
            "payload": payload,
        }
    )


def append_event(ledger: ExecutionLedger, event_type: str, payload: Any) -> ExecutionLedger:
    if not event_type or not event_type.strip():
        raise ValueError("event_type must be non-empty")
    index = len(ledger.events)
    previous_hash = ledger.head
    event_hash = _event_hash(index, event_type, previous_hash, payload)
    event = LedgerEvent(index, event_type, previous_hash, payload, event_hash)
    return ExecutionLedger(events=ledger.events + (event,))


def verify_ledger(ledger: ExecutionLedger) -> bool:
    previous = GENESIS
    for expected_index, event in enumerate(ledger.events):
        if event.index != expected_index or event.previous_hash != previous:
            return False
        if event.event_hash != _event_hash(event.index, event.event_type, event.previous_hash, event.payload):
            return False
        previous = event.event_hash
    return True
