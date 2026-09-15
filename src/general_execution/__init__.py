"""General Execution: deterministic execution substrate for bounded authorized work."""

from .canonical import canonical_json, sha256_digest, stable_id
from .ledger import ExecutionLedger, LedgerEvent, append_event, verify_ledger
from .models import (
    ArtifactRef,
    DispatchPlan,
    ExecutionSession,
    ExecutionSpec,
    ResultEnvelope,
    RunnerCapabilities,
    RunnerRegistry,
)
from .planner import plan_execution, verify_plan
from .session import SessionError, bind_session, revoke_session, start_session, submit_result

__all__ = [
    "ArtifactRef",
    "DispatchPlan",
    "ExecutionLedger",
    "ExecutionSession",
    "ExecutionSpec",
    "LedgerEvent",
    "ResultEnvelope",
    "RunnerCapabilities",
    "RunnerRegistry",
    "SessionError",
    "append_event",
    "bind_session",
    "canonical_json",
    "plan_execution",
    "revoke_session",
    "sha256_digest",
    "stable_id",
    "start_session",
    "submit_result",
    "verify_ledger",
    "verify_plan",
]

__version__ = "0.0.1"
