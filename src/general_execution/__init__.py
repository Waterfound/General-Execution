"""General Execution: deterministic execution substrate for bounded authorized work."""

from .adapter import (
    AdapterDispatchRequest,
    AdapterError,
    AdapterReceipt,
    InvocationBundle,
    ProviderObservation,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    admit_observation,
    build_dispatch_request,
    make_reference_observation,
    reference_runner,
    verify_dispatch_request,
    verify_invocation_bundle,
)
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
from .provenance import InvocationRecord, record_invocation, verify_invocation_record
from .session import SessionError, bind_session, revoke_session, start_session, submit_result

__all__ = [
    "AdapterDispatchRequest",
    "AdapterError",
    "AdapterReceipt",
    "ArtifactRef",
    "DispatchPlan",
    "ExecutionLedger",
    "ExecutionSession",
    "ExecutionSpec",
    "InvocationBundle",
    "InvocationRecord",
    "LedgerEvent",
    "ProviderObservation",
    "REFERENCE_CAPABILITY",
    "REFERENCE_EVIDENCE",
    "REFERENCE_TASK_KIND",
    "ResultEnvelope",
    "RunnerCapabilities",
    "RunnerRegistry",
    "SessionError",
    "admit_observation",
    "append_event",
    "bind_session",
    "build_dispatch_request",
    "canonical_json",
    "make_reference_observation",
    "plan_execution",
    "record_invocation",
    "reference_runner",
    "revoke_session",
    "sha256_digest",
    "stable_id",
    "start_session",
    "submit_result",
    "verify_dispatch_request",
    "verify_invocation_bundle",
    "verify_invocation_record",
    "verify_ledger",
    "verify_plan",
]

__version__ = "0.0.2"
