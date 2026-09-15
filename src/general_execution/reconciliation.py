from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest, stable_id
from .dispatch import DispatchIntentError, DispatchIntentState, DispatchPermit, verify_dispatch_permit
from .dispatch_guard import LiveDispatchPermit, verify_live_dispatch_permit
from .durable import SqliteCapacityHeadStore
from .models import RunnerCapabilities
from .physical import PhysicalAttemptAuthorization

SameRequestSemantics = Literal["same_operation", "duplicate_rejected"]
ReconciliationStatus = Literal["absent", "accepted", "terminal", "unknown"]
ReconciliationAction = Literal[
    "resubmit_same_invocation",
    "poll_existing",
    "admit_terminal_evidence",
    "hold",
]

CONTRACT_SCHEMA = "ge.provider-reconciliation-contract.v1"
QUERY_SCHEMA = "ge.provider-reconciliation-query.v1"
OBSERVATION_SCHEMA = "ge.provider-reconciliation-observation.v1"
EVIDENCE_SCHEMA = "ge.provider-reconciliation-evidence.v1"
DECISION_SCHEMA = "ge.provider-reconciliation-decision.v1"


class ReconciliationError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class ProviderReconciliationContract:
    provider: str
    adapter: str
    adapter_version: str
    idempotency_key: str = "invocation_id"
    lookup_by_invocation: bool = True
    request_digest_bound: bool = True
    same_key_same_request: SameRequestSemantics = "same_operation"
    same_key_different_request: str = "reject"
    terminal_evidence_lookup: bool = True
    schema_version: str = CONTRACT_SCHEMA

    def __post_init__(self) -> None:
        for name in ("provider", "adapter", "adapter_version"):
            _nonempty(name, getattr(self, name))
        if self.idempotency_key != "invocation_id":
            raise ValueError("v0.0.7 reconciliation requires invocation_id as idempotency key")
        if self.same_key_same_request not in {"same_operation", "duplicate_rejected"}:
            raise ValueError("unsupported same-key/same-request semantics")
        if self.same_key_different_request != "reject":
            raise ValueError("same idempotency key with a different request must be rejected")

    @property
    def reconciliation_capable(self) -> bool:
        return self.lookup_by_invocation and self.request_digest_bound

    @property
    def safe_idempotent_resubmission(self) -> bool:
        return (
            self.reconciliation_capable
            and self.same_key_same_request in {"same_operation", "duplicate_rejected"}
            and self.same_key_different_request == "reject"
        )

    @property
    def contract_id(self) -> str:
        return stable_id("geprc", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderReconciliationQuery:
    intent_id: str
    dispatch_state_digest: str
    dispatch_permit_digest: str
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    runner_id: str
    provider: str
    adapter: str
    adapter_version: str
    contract_digest: str
    schema_version: str = QUERY_SCHEMA

    def __post_init__(self) -> None:
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        for name in (
            "intent_id",
            "dispatch_state_digest",
            "dispatch_permit_digest",
            "authorization_id",
            "authorization_digest",
            "invocation_id",
            "request_digest",
            "runner_id",
            "provider",
            "adapter",
            "adapter_version",
            "contract_digest",
        ):
            _nonempty(name, getattr(self, name))

    @property
    def query_id(self) -> str:
        return stable_id("geprq", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderReconciliationObservation:
    query_digest: str
    invocation_id: str
    request_digest: str
    provider: str
    adapter: str
    adapter_version: str
    status: ReconciliationStatus
    evidence_digest: str
    provider_invocation_id: str | None = None
    terminal_evidence_digest: str | None = None
    schema_version: str = OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        for name in (
            "query_digest",
            "invocation_id",
            "request_digest",
            "provider",
            "adapter",
            "adapter_version",
            "evidence_digest",
        ):
            _nonempty(name, getattr(self, name))
        _sha256("evidence_digest", self.evidence_digest)
        if self.terminal_evidence_digest is not None:
            _sha256("terminal_evidence_digest", self.terminal_evidence_digest)

        if self.status == "absent":
            if self.provider_invocation_id is not None or self.terminal_evidence_digest is not None:
                raise ValueError("absent observation cannot claim provider invocation or terminal evidence")
        elif self.status == "accepted":
            if not self.provider_invocation_id or self.terminal_evidence_digest is not None:
                raise ValueError("accepted observation requires provider invocation and no terminal evidence")
        elif self.status == "terminal":
            if not self.provider_invocation_id or self.terminal_evidence_digest is None:
                raise ValueError("terminal observation requires provider invocation and terminal evidence digest")
        elif self.status == "unknown":
            if self.terminal_evidence_digest is not None:
                raise ValueError("unknown observation cannot claim terminal evidence")
        else:
            raise ValueError("unsupported reconciliation status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderReconciliationEvidence:
    query: ProviderReconciliationQuery
    observation: ProviderReconciliationObservation
    contract_digest: str
    schema_version: str = EVIDENCE_SCHEMA

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    intent_id: str
    dispatch_state_digest: str
    evidence_digest: str
    contract_digest: str
    status: ReconciliationStatus
    action: ReconciliationAction
    resubmit_authorized: bool
    requires_fresh_live_permit: bool
    live_permit_digest: str | None
    reason: str
    schema_version: str = DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.action == "resubmit_same_invocation":
            if not self.resubmit_authorized or not self.requires_fresh_live_permit or not self.live_permit_digest:
                raise ValueError("resubmit decision requires explicit authorization and fresh live permit")
        else:
            if self.resubmit_authorized or self.live_permit_digest is not None:
                raise ValueError("non-resubmit decision cannot authorize transport")
        if not self.reason.strip():
            raise ValueError("reconciliation decision reason must be non-empty")

    @property
    def decision_id(self) -> str:
        return stable_id("geprd", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _verify_authorization_binding(
    state: DispatchIntentState,
    authorization: PhysicalAttemptAuthorization,
) -> bool:
    intent = state.intent
    request = authorization.request
    return (
        authorization.authorization_id == intent.authorization_id
        and authorization.digest == intent.authorization_digest
        and request.invocation_id == intent.invocation_id
        and request.digest == intent.request_digest
        and request.runner_id == intent.runner_id
        and request.runner_capability_digest == intent.runner_capability_digest
        and request.session_id == intent.session_id
        and request.attempt == intent.logical_attempt
        and authorization.physical_attempt == intent.physical_attempt
    )


def create_reconciliation_query(
    state: DispatchIntentState,
    permit: DispatchPermit,
    authorization: PhysicalAttemptAuthorization,
    contract: ProviderReconciliationContract,
) -> ProviderReconciliationQuery:
    if state.status != "submission_unknown":
        raise ReconciliationError("reconciliation requires submission_unknown durable state")
    if not verify_dispatch_permit(state, permit):
        raise ReconciliationError("durable dispatch permit does not reproduce")
    if not _verify_authorization_binding(state, authorization):
        raise ReconciliationError("physical authorization does not reproduce dispatch intent")
    request = authorization.request
    if (
        contract.provider != request.provider
        or contract.adapter != request.adapter
        or contract.adapter_version != request.adapter_version
    ):
        raise ReconciliationError("provider reconciliation contract does not match physical authorization")
    if not contract.reconciliation_capable:
        raise ReconciliationError("provider contract cannot reconcile by invocation identity")
    return ProviderReconciliationQuery(
        intent_id=state.intent.intent_id,
        dispatch_state_digest=state.digest,
        dispatch_permit_digest=permit.digest,
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.digest,
        invocation_id=request.invocation_id,
        request_digest=request.digest,
        physical_attempt=authorization.physical_attempt,
        runner_id=request.runner_id,
        provider=request.provider,
        adapter=request.adapter,
        adapter_version=request.adapter_version,
        contract_digest=contract.digest,
    )


def admit_reconciliation_observation(
    query: ProviderReconciliationQuery,
    contract: ProviderReconciliationContract,
    observation: ProviderReconciliationObservation,
) -> ProviderReconciliationEvidence:
    if query.contract_digest != contract.digest:
        raise ReconciliationError("reconciliation query contract binding mismatch")
    if observation.query_digest != query.digest:
        raise ReconciliationError("provider reconciliation observation query binding mismatch")
    if (
        observation.invocation_id != query.invocation_id
        or observation.request_digest != query.request_digest
        or observation.provider != query.provider
        or observation.adapter != query.adapter
        or observation.adapter_version != query.adapter_version
    ):
        raise ReconciliationError("provider reconciliation observation identity mismatch")
    return ProviderReconciliationEvidence(query, observation, contract.digest)


def decide_reconciliation(
    state: DispatchIntentState,
    permit: DispatchPermit,
    authorization: PhysicalAttemptAuthorization,
    contract: ProviderReconciliationContract,
    evidence: ProviderReconciliationEvidence,
    *,
    live_permit: LiveDispatchPermit | None = None,
    capacity_store: SqliteCapacityHeadStore | None = None,
    runner: RunnerCapabilities | None = None,
) -> ReconciliationDecision:
    query = create_reconciliation_query(state, permit, authorization, contract)
    if evidence.query != query or evidence.contract_digest != contract.digest:
        raise ReconciliationError("reconciliation evidence does not belong to current query")
    observation = evidence.observation
    if observation.query_digest != query.digest:
        raise ReconciliationError("reconciliation evidence observation is not bound to current query")

    if observation.status == "absent":
        if not contract.safe_idempotent_resubmission:
            return ReconciliationDecision(
                intent_id=state.intent.intent_id,
                dispatch_state_digest=state.digest,
                evidence_digest=evidence.digest,
                contract_digest=contract.digest,
                status="absent",
                action="hold",
                resubmit_authorized=False,
                requires_fresh_live_permit=True,
                live_permit_digest=None,
                reason="provider absence is insufficient without strong idempotent resubmission semantics",
            )
        if live_permit is None or capacity_store is None or runner is None:
            raise ReconciliationError("safe resubmission requires a fresh live dispatch permit")
        if not verify_live_dispatch_permit(state, permit, live_permit, capacity_store, runner):
            raise ReconciliationError("live dispatch permit is stale or invalid")
        return ReconciliationDecision(
            intent_id=state.intent.intent_id,
            dispatch_state_digest=state.digest,
            evidence_digest=evidence.digest,
            contract_digest=contract.digest,
            status="absent",
            action="resubmit_same_invocation",
            resubmit_authorized=True,
            requires_fresh_live_permit=True,
            live_permit_digest=live_permit.digest,
            reason="provider proved absence and same invocation is protected by strong idempotency",
        )

    if observation.status == "accepted":
        return ReconciliationDecision(
            intent_id=state.intent.intent_id,
            dispatch_state_digest=state.digest,
            evidence_digest=evidence.digest,
            contract_digest=contract.digest,
            status="accepted",
            action="poll_existing",
            resubmit_authorized=False,
            requires_fresh_live_permit=False,
            live_permit_digest=None,
            reason="provider already recognizes the invocation; poll the existing operation",
        )

    if observation.status == "terminal":
        action: ReconciliationAction = "admit_terminal_evidence" if contract.terminal_evidence_lookup else "hold"
        reason = (
            "provider returned terminal evidence for admission"
            if contract.terminal_evidence_lookup
            else "provider reports terminal state but contract cannot retrieve admissible terminal evidence"
        )
        return ReconciliationDecision(
            intent_id=state.intent.intent_id,
            dispatch_state_digest=state.digest,
            evidence_digest=evidence.digest,
            contract_digest=contract.digest,
            status="terminal",
            action=action,
            resubmit_authorized=False,
            requires_fresh_live_permit=False,
            live_permit_digest=None,
            reason=reason,
        )

    return ReconciliationDecision(
        intent_id=state.intent.intent_id,
        dispatch_state_digest=state.digest,
        evidence_digest=evidence.digest,
        contract_digest=contract.digest,
        status="unknown",
        action="hold",
        resubmit_authorized=False,
        requires_fresh_live_permit=False,
        live_permit_digest=None,
        reason="provider state remains unknown; preserve ambiguity and do not resubmit blindly",
    )
