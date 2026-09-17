from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    ISSUE = "issue"


@dataclass(frozen=True)
class RunLedger:
    ready: tuple[str, ...]
    events: tuple[dict, ...] = ()
