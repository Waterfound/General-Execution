from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical import sha256_digest

AUTHORITY_SCHEMA = "ge.work-sparse-authority-envelope.v1"
WORK_ITEM_SCHEMA = "ge.work-sparse-work-item.v1"
EXECUTOR_SCHEMA = "ge.work-sparse-executor-capability.v1"
DECISION_SCHEMA = "ge.work-sparse-controller-decision.v1"
PROTOCOL_VERSION = "0.1.0"


class WorkSparseError(ValueError):
    """Raised when a work-sparse unattended contract is invalid."""


class ControllerDisposition(str, Enum):
    OBSERVE_EXISTING = "OBSERVE_EXISTING"
    DISPATCH = "DISPATCH"
    CONDITION_WAIT = "CONDITION_WAIT"
    HUMAN_GATE = "HUMAN_GATE"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkSparseError(f"{field} must be a non-empty string")
    return value.strip()


def _boolean(value: bool, field: str) -> bool:
    if not isinstance(value, bool):
        raise WorkSparseError(f"{field} must be boolean")
    return value


def _nonnegative_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorkSparseError(f"{field} must be a non-negative integer")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise WorkSparseError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise WorkSparseError(f"{field} must not contain duplicates")
    return items


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class UnattendedAuthorityEnvelope:
    envelope_id: str
    authority_ref: str
    allowed_repositories: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    max_work_invocations: int = 0
    max_paid_spend_cents: int = 0
    authority_created: bool = False
    schema_version: str = AUTHORITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != AUTHORITY_SCHEMA:
            raise WorkSparseError("unsupported authority envelope schema")
        _nonempty(self.envelope_id, "envelope_id")
        _nonempty(self.authority_ref, "authority_ref")
        _unique(self.allowed_repositories, "allowed_repositories", allow_empty=False)
        allowed = _unique(self.allowed_actions, "allowed_actions", allow_empty=False)
        forbidden = _unique(self.forbidden_actions, "forbidden_actions")
        if set(allowed) & set(forbidden):
            raise WorkSparseError("allowed_actions and forbidden_actions must not overlap")
        _nonnegative_int(self.max_work_invocations, "max_work_invocations")
        _nonnegative_int(self.max_paid_spend_cents, "max_paid_spend_cents")
        _boolean(self.authority_created, "authority_created")
        if self.authority_created:
            raise WorkSparseError("authority envelope cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class UnattendedWorkItem:
    work_id: str
    objective: str
    repository: str
    source_revision: str
    authority_ref: str
    required_capabilities: tuple[str, ...]
    requested_actions: tuple[str, ...]
    existing_execution_ref: str | None = None
    schema_version: str = WORK_ITEM_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != WORK_ITEM_SCHEMA:
            raise WorkSparseError("unsupported work item schema")
        for field in ("work_id", "objective", "repository", "source_revision", "authority_ref"):
            _nonempty(getattr(self, field), field)
        _unique(self.required_capabilities, "required_capabilities", allow_empty=False)
        _unique(self.requested_actions, "requested_actions", allow_empty=False)
        if self.existing_execution_ref is not None:
            _nonempty(self.existing_execution_ref, "existing_execution_ref")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutorCapability:
    executor_id: str
    capabilities: tuple[str, ...]
    cost_rank: int
    estimated_cost_cents: int = 0
    requires_work: bool = False
    paid: bool = False
    available: bool = True
    evidence_ref: str = "evidence://unbound"
    authority_created: bool = False
    schema_version: str = EXECUTOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != EXECUTOR_SCHEMA:
            raise WorkSparseError("unsupported executor capability schema")
        _nonempty(self.executor_id, "executor_id")
        _unique(self.capabilities, "capabilities", allow_empty=False)
        _nonnegative_int(self.cost_rank, "cost_rank")
        _nonnegative_int(self.estimated_cost_cents, "estimated_cost_cents")
        _boolean(self.requires_work, "requires_work")
        _boolean(self.paid, "paid")
        _boolean(self.available, "available")
        _nonempty(self.evidence_ref, "evidence_ref")
        _boolean(self.authority_created, "authority_created")
        if self.authority_created:
            raise WorkSparseError("executor capability cannot create authority")
        if not self.paid and self.estimated_cost_cents != 0:
            raise WorkSparseError("non-paid executor must have zero estimated_cost_cents")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ControllerUsage:
    work_invocations_used: int = 0
    paid_spend_cents: int = 0

    def __post_init__(self) -> None:
        _nonnegative_int(self.work_invocations_used, "work_invocations_used")
        _nonnegative_int(self.paid_spend_cents, "paid_spend_cents")


@dataclass(frozen=True, slots=True)
class WorkSparseControllerDecision:
    work_id: str
    disposition: str
    selected_executor_id: str | None
    selected_executor_digest: str | None
    work_required: bool
    reasons: tuple[str, ...]
    envelope_digest: str
    work_item_digest: str
    authority_ref: str
    authority_created: bool = False
    execution_triggered: bool = False
    protocol_version: str = PROTOCOL_VERSION
    schema_version: str = DECISION_SCHEMA
    decision_digest: str = ""

    def __post_init__(self) -> None:
        if self.disposition not in {item.value for item in ControllerDisposition}:
            raise WorkSparseError("unsupported controller disposition")
        if self.selected_executor_id is None:
            if self.selected_executor_digest is not None or self.work_required:
                raise WorkSparseError("non-dispatch decision cannot bind an executor")
        else:
            _nonempty(self.selected_executor_id, "selected_executor_id")
            _nonempty(self.selected_executor_digest, "selected_executor_digest")
        if self.authority_created:
            raise WorkSparseError("controller decision cannot create authority")
        if self.execution_triggered:
            raise WorkSparseError("controller decision cannot claim execution")
        _nonempty(self.authority_ref, "authority_ref")

    @property
    def digest(self) -> str:
        return self.decision_digest


def _decision_payload(decision: WorkSparseControllerDecision) -> dict[str, Any]:
    payload = _jsonable(decision)
    payload.pop("decision_digest", None)
    return payload


def decision_to_dict(decision: WorkSparseControllerDecision) -> dict[str, Any]:
    return {**_decision_payload(decision), "decision_digest": decision.decision_digest}


def _finalize(
    *,
    work: UnattendedWorkItem,
    envelope: UnattendedAuthorityEnvelope,
    disposition: ControllerDisposition,
    reasons: tuple[str, ...],
    executor: ExecutorCapability | None = None,
) -> WorkSparseControllerDecision:
    provisional = WorkSparseControllerDecision(
        work_id=work.work_id,
        disposition=disposition.value,
        selected_executor_id=executor.executor_id if executor else None,
        selected_executor_digest=executor.digest if executor else None,
        work_required=bool(executor and executor.requires_work),
        reasons=reasons,
        envelope_digest=envelope.digest,
        work_item_digest=work.digest,
        authority_ref=envelope.authority_ref,
    )
    digest = sha256_digest(_decision_payload(provisional))
    return WorkSparseControllerDecision(
        work_id=provisional.work_id,
        disposition=provisional.disposition,
        selected_executor_id=provisional.selected_executor_id,
        selected_executor_digest=provisional.selected_executor_digest,
        work_required=provisional.work_required,
        reasons=provisional.reasons,
        envelope_digest=provisional.envelope_digest,
        work_item_digest=provisional.work_item_digest,
        authority_ref=provisional.authority_ref,
        decision_digest=digest,
    )


def decide_work_sparse_route(
    envelope: UnattendedAuthorityEnvelope,
    work: UnattendedWorkItem,
    executors: tuple[ExecutorCapability, ...],
    usage: ControllerUsage = ControllerUsage(),
) -> WorkSparseControllerDecision:
    """Choose the cheapest admissible executor without creating launch authority.

    The decision is deliberately side-effect free. A DISPATCH disposition means
    "this executor is the preferred next admission target"; it never means that
    execution has been triggered.
    """

    if work.authority_ref != envelope.authority_ref:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.HUMAN_GATE,
            reasons=("authority_ref_mismatch",),
        )

    if work.repository not in envelope.allowed_repositories:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.HUMAN_GATE,
            reasons=("repository_outside_authority_envelope",),
        )

    forbidden = sorted(set(work.requested_actions) & set(envelope.forbidden_actions))
    if forbidden:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.HUMAN_GATE,
            reasons=(f"forbidden_action:{','.join(forbidden)}",),
        )

    unknown = sorted(set(work.requested_actions) - set(envelope.allowed_actions))
    if unknown:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.HUMAN_GATE,
            reasons=(f"action_not_authorized:{','.join(unknown)}",),
        )

    if work.existing_execution_ref is not None:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.OBSERVE_EXISTING,
            reasons=(f"existing_execution:{work.existing_execution_ref}",),
        )

    required = set(work.required_capabilities)
    matching = tuple(
        executor
        for executor in executors
        if required <= set(executor.capabilities)
    )
    if not matching:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.CONDITION_WAIT,
            reasons=("no_executor_matches_required_capabilities",),
        )

    available = [executor for executor in matching if executor.available]
    if not available:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.CONDITION_WAIT,
            reasons=("matching_executors_unavailable",),
        )

    admissible: list[ExecutorCapability] = []
    rejected_reasons: list[str] = []
    for executor in available:
        if executor.requires_work and usage.work_invocations_used >= envelope.max_work_invocations:
            rejected_reasons.append(f"{executor.executor_id}:work_budget_exhausted")
            continue
        projected_spend = usage.paid_spend_cents + executor.estimated_cost_cents
        if executor.paid and projected_spend > envelope.max_paid_spend_cents:
            rejected_reasons.append(f"{executor.executor_id}:paid_budget_exhausted")
            continue
        admissible.append(executor)

    if not admissible:
        return _finalize(
            work=work,
            envelope=envelope,
            disposition=ControllerDisposition.CONDITION_WAIT,
            reasons=tuple(sorted(rejected_reasons)) or ("no_executor_within_budget",),
        )

    selected = min(
        admissible,
        key=lambda executor: (
            1 if executor.requires_work else 0,
            1 if executor.paid else 0,
            executor.cost_rank,
            executor.estimated_cost_cents,
            executor.executor_id,
        ),
    )
    reasons = (
        "cheapest_admissible_executor",
        "work_sparse_preference" if not selected.requires_work else "work_required_by_capability",
    )
    return _finalize(
        work=work,
        envelope=envelope,
        disposition=ControllerDisposition.DISPATCH,
        reasons=reasons,
        executor=selected,
    )


def verify_work_sparse_decision(
    envelope: UnattendedAuthorityEnvelope,
    work: UnattendedWorkItem,
    executors: tuple[ExecutorCapability, ...],
    usage: ControllerUsage,
    decision: dict[str, Any],
) -> bool:
    try:
        expected = decision_to_dict(
            decide_work_sparse_route(envelope, work, executors, usage)
        )
    except (WorkSparseError, TypeError, ValueError):
        return False
    return expected == decision
