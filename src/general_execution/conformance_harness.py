from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .canonical import sha256_digest, stable_id
from .conformance import (
    ProviderConformanceCaseResult,
    ProviderConformanceEvidence,
)
from .reconciliation import ProviderReconciliationContract

SubmitStatus = Literal[
    "accepted",
    "duplicate_rejected",
    "different_request_rejected",
]
LookupStatus = Literal[
    "absent",
    "accepted",
    "terminal",
    "unknown",
    "identity_mismatch",
]
EnvironmentScope = Literal["sandbox", "production_equivalent"]

SUBMIT_SCHEMA = "ge.conformance-submit-result.v1"
LOOKUP_SCHEMA = "ge.conformance-lookup-result.v1"
RUN_SCHEMA = "ge.provider-conformance-run.v1"
REFERENCE_TARGET_SCHEMA = "ge.reference-conformance-target.v1"
HARNESS_VERSION = "ge.provider-conformance-harness.v1"


class ConformanceHarnessError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class ConformanceSubmitResult:
    invocation_id: str
    request_digest: str
    status: SubmitStatus
    provider_invocation_id: str | None
    evidence_digest: str
    schema_version: str = SUBMIT_SCHEMA

    def __post_init__(self) -> None:
        _nonempty("invocation_id", self.invocation_id)
        _nonempty("request_digest", self.request_digest)
        _nonempty("evidence_digest", self.evidence_digest)
        if self.status == "accepted" and not self.provider_invocation_id:
            raise ValueError("accepted submit requires provider invocation identity")
        if self.status in {"duplicate_rejected", "different_request_rejected"} and self.provider_invocation_id is not None:
            raise ValueError("rejected submit cannot create a new provider invocation")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ConformanceLookupResult:
    invocation_id: str
    request_digest: str
    status: LookupStatus
    provider_invocation_id: str | None
    terminal_evidence_digest: str | None
    evidence_digest: str
    schema_version: str = LOOKUP_SCHEMA

    def __post_init__(self) -> None:
        _nonempty("invocation_id", self.invocation_id)
        _nonempty("request_digest", self.request_digest)
        _nonempty("evidence_digest", self.evidence_digest)
        if self.status == "accepted":
            if not self.provider_invocation_id or self.terminal_evidence_digest is not None:
                raise ValueError("accepted lookup requires provider invocation and no terminal evidence")
        elif self.status == "terminal":
            if not self.provider_invocation_id or not self.terminal_evidence_digest:
                raise ValueError("terminal lookup requires provider invocation and terminal evidence")
        else:
            if self.terminal_evidence_digest is not None:
                raise ValueError("non-terminal lookup cannot carry terminal evidence")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@runtime_checkable
class ProviderConformanceTarget(Protocol):
    provider: str
    adapter: str
    adapter_version: str
    adapter_revision: str
    environment_scope: EnvironmentScope

    def reset(self) -> None: ...

    def submit(self, invocation_id: str, request_digest: str) -> ConformanceSubmitResult: ...

    def lookup(self, invocation_id: str, request_digest: str) -> ConformanceLookupResult: ...

    def mark_terminal(
        self,
        invocation_id: str,
        request_digest: str,
        terminal_evidence_digest: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderConformanceRun:
    harness_version: str
    contract_digest: str
    provider: str
    adapter: str
    adapter_version: str
    adapter_revision: str
    environment_scope: EnvironmentScope
    case_results: tuple[ProviderConformanceCaseResult, ...]
    conformance_evidence_digest: str
    all_required_cases_passed: bool
    schema_version: str = RUN_SCHEMA

    def __post_init__(self) -> None:
        if self.harness_version != HARNESS_VERSION:
            raise ValueError("unsupported provider conformance harness version")
        if self.environment_scope not in {"sandbox", "production_equivalent"}:
            raise ValueError("unsupported conformance run environment")
        ids = [case.case_id for case in self.case_results]
        if len(ids) != len(set(ids)):
            raise ValueError("conformance run case IDs must be unique")

    @property
    def run_id(self) -> str:
        return stable_id("gepcr", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _case(case_id: str, passed: bool, transcript) -> ProviderConformanceCaseResult:
    return ProviderConformanceCaseResult(
        case_id=case_id,
        passed=passed,
        evidence_digest=sha256_digest(
            {
                "harness_version": HARNESS_VERSION,
                "case_id": case_id,
                "transcript": transcript,
            }
        ),
    )


def _identity(contract: ProviderReconciliationContract, target: ProviderConformanceTarget) -> None:
    if (
        target.provider != contract.provider
        or target.adapter != contract.adapter
        or target.adapter_version != contract.adapter_version
    ):
        raise ConformanceHarnessError("conformance target identity does not match provider contract")
    if target.environment_scope not in {"sandbox", "production_equivalent"}:
        raise ConformanceHarnessError("conformance target environment scope is unsupported")
    if not target.adapter_revision or len(target.adapter_revision) not in {40, 64}:
        raise ConformanceHarnessError("conformance target must expose immutable adapter revision")
    try:
        int(target.adapter_revision, 16)
    except ValueError as exc:
        raise ConformanceHarnessError("adapter revision must be hexadecimal") from exc


def _same_request_case(contract, target, invocation_id, request_digest):
    target.reset()
    first = target.submit(invocation_id, request_digest)
    second = target.submit(invocation_id, request_digest)
    if first.status != "accepted" or not first.provider_invocation_id:
        passed = False
    elif contract.same_key_same_request == "same_operation":
        passed = second.status == "accepted" and second.provider_invocation_id == first.provider_invocation_id
    elif contract.same_key_same_request == "duplicate_rejected":
        passed = second.status == "duplicate_rejected"
    else:
        passed = (
            second.status == "accepted"
            and second.provider_invocation_id is not None
            and second.provider_invocation_id != first.provider_invocation_id
        )
    return _case(
        "same_request_semantics",
        passed,
        {
            "declared": contract.same_key_same_request,
            "first": first,
            "second": second,
        },
    )


def _different_request_case(contract, target, invocation_id, request_digest, different_request_digest):
    target.reset()
    first = target.submit(invocation_id, request_digest)
    second = target.submit(invocation_id, different_request_digest)
    passed = (
        first.status == "accepted"
        and contract.same_key_different_request == "reject"
        and second.status == "different_request_rejected"
    )
    return _case(
        "different_request_rejection",
        passed,
        {"first": first, "different_request": second},
    )


def _lookup_identity_case(target, invocation_id, request_digest, different_request_digest):
    target.reset()
    submitted = target.submit(invocation_id, request_digest)
    correct = target.lookup(invocation_id, request_digest)
    wrong = target.lookup(invocation_id, different_request_digest)
    passed = (
        submitted.status == "accepted"
        and correct.status == "accepted"
        and correct.provider_invocation_id == submitted.provider_invocation_id
        and wrong.status == "identity_mismatch"
    )
    return _case(
        "lookup_identity_binding",
        passed,
        {"submit": submitted, "correct_lookup": correct, "wrong_request_lookup": wrong},
    )


def _absence_case(target, invocation_id, request_digest):
    target.reset()
    before = target.lookup(invocation_id, request_digest)
    submitted = target.submit(invocation_id, request_digest)
    after = target.lookup(invocation_id, request_digest)
    passed = (
        before.status == "absent"
        and submitted.status == "accepted"
        and after.status == "accepted"
        and after.provider_invocation_id == submitted.provider_invocation_id
    )
    return _case(
        "absence_semantics",
        passed,
        {"before": before, "submit": submitted, "after": after},
    )


def _terminal_case(target, invocation_id, request_digest, terminal_evidence_digest):
    target.reset()
    submitted = target.submit(invocation_id, request_digest)
    if submitted.status == "accepted":
        target.mark_terminal(invocation_id, request_digest, terminal_evidence_digest)
    terminal = target.lookup(invocation_id, request_digest)
    passed = (
        submitted.status == "accepted"
        and terminal.status == "terminal"
        and terminal.provider_invocation_id == submitted.provider_invocation_id
        and terminal.terminal_evidence_digest == terminal_evidence_digest
    )
    return _case(
        "terminal_evidence_binding",
        passed,
        {"submit": submitted, "terminal_lookup": terminal},
    )


def run_provider_conformance(
    contract: ProviderReconciliationContract,
    target: ProviderConformanceTarget,
    *,
    invocation_id: str = "gei-conformance-1",
    request_digest: str = "sha256:" + "1" * 64,
    different_request_digest: str = "sha256:" + "2" * 64,
    terminal_evidence_digest: str = "sha256:" + "3" * 64,
) -> tuple[ProviderConformanceEvidence, ProviderConformanceRun]:
    _identity(contract, target)
    if request_digest == different_request_digest:
        raise ConformanceHarnessError("conformance requests must have distinct digests")

    cases = [
        _same_request_case(contract, target, invocation_id, request_digest),
        _different_request_case(contract, target, invocation_id, request_digest, different_request_digest),
        _lookup_identity_case(target, invocation_id, request_digest, different_request_digest),
        _absence_case(target, invocation_id, request_digest),
    ]
    if contract.terminal_evidence_lookup:
        cases.append(_terminal_case(target, invocation_id, request_digest, terminal_evidence_digest))

    evidence = ProviderConformanceEvidence(
        contract_digest=contract.digest,
        adapter_revision=target.adapter_revision,
        environment_scope=target.environment_scope,
        cases=tuple(cases),
    )
    run = ProviderConformanceRun(
        harness_version=HARNESS_VERSION,
        contract_digest=contract.digest,
        provider=target.provider,
        adapter=target.adapter,
        adapter_version=target.adapter_version,
        adapter_revision=target.adapter_revision,
        environment_scope=target.environment_scope,
        case_results=evidence.cases,
        conformance_evidence_digest=evidence.digest,
        all_required_cases_passed=all(case.passed for case in evidence.cases),
    )
    return evidence, run


@dataclass(slots=True)
class _ReferenceOperation:
    invocation_id: str
    request_digest: str
    provider_invocation_id: str
    terminal_evidence_digest: str | None = None


class ReferenceConformanceTarget:
    """Deterministic sandbox target used to validate the harness itself."""

    provider = "reference-provider"
    adapter = "reference-adapter"
    adapter_version = "1"
    environment_scope: EnvironmentScope = "sandbox"
    schema_version = REFERENCE_TARGET_SCHEMA

    def __init__(
        self,
        *,
        adapter_revision: str = "0" * 40,
        same_key_same_request: Literal["same_operation", "duplicate_rejected", "may_duplicate"] = "same_operation",
    ):
        if same_key_same_request not in {"same_operation", "duplicate_rejected", "may_duplicate"}:
            raise ValueError("unsupported reference duplicate semantics")
        self.adapter_revision = adapter_revision
        self.same_key_same_request = same_key_same_request
        self.reset()

    def reset(self) -> None:
        self._operations: dict[str, list[_ReferenceOperation]] = {}
        self._ordinal = 0

    def _result_digest(self, kind, payload) -> str:
        return sha256_digest(
            {
                "target": self.schema_version,
                "kind": kind,
                "payload": payload,
            }
        )

    def _new_operation(self, invocation_id: str, request_digest: str) -> _ReferenceOperation:
        self._ordinal += 1
        provider_invocation_id = stable_id(
            "refop",
            {
                "invocation_id": invocation_id,
                "request_digest": request_digest,
                "ordinal": self._ordinal,
            },
        )
        operation = _ReferenceOperation(invocation_id, request_digest, provider_invocation_id)
        self._operations.setdefault(invocation_id, []).append(operation)
        return operation

    def submit(self, invocation_id: str, request_digest: str) -> ConformanceSubmitResult:
        existing = self._operations.get(invocation_id, [])
        if existing:
            canonical = existing[0]
            if canonical.request_digest != request_digest:
                return ConformanceSubmitResult(
                    invocation_id,
                    request_digest,
                    "different_request_rejected",
                    None,
                    self._result_digest("different_request_rejected", (invocation_id, request_digest)),
                )
            if self.same_key_same_request == "duplicate_rejected":
                return ConformanceSubmitResult(
                    invocation_id,
                    request_digest,
                    "duplicate_rejected",
                    None,
                    self._result_digest("duplicate_rejected", canonical.provider_invocation_id),
                )
            if self.same_key_same_request == "same_operation":
                operation = canonical
            else:
                operation = self._new_operation(invocation_id, request_digest)
        else:
            operation = self._new_operation(invocation_id, request_digest)

        return ConformanceSubmitResult(
            invocation_id,
            request_digest,
            "accepted",
            operation.provider_invocation_id,
            self._result_digest("accepted", operation.provider_invocation_id),
        )

    def lookup(self, invocation_id: str, request_digest: str) -> ConformanceLookupResult:
        existing = self._operations.get(invocation_id, [])
        if not existing:
            return ConformanceLookupResult(
                invocation_id,
                request_digest,
                "absent",
                None,
                None,
                self._result_digest("absent", (invocation_id, request_digest)),
            )
        canonical = existing[0]
        if canonical.request_digest != request_digest:
            return ConformanceLookupResult(
                invocation_id,
                request_digest,
                "identity_mismatch",
                None,
                None,
                self._result_digest("identity_mismatch", (invocation_id, request_digest)),
            )
        if len(existing) > 1:
            return ConformanceLookupResult(
                invocation_id,
                request_digest,
                "unknown",
                None,
                None,
                self._result_digest(
                    "ambiguous_multiple_operations",
                    tuple(op.provider_invocation_id for op in existing),
                ),
            )
        if canonical.terminal_evidence_digest is not None:
            return ConformanceLookupResult(
                invocation_id,
                request_digest,
                "terminal",
                canonical.provider_invocation_id,
                canonical.terminal_evidence_digest,
                self._result_digest("terminal", canonical.provider_invocation_id),
            )
        return ConformanceLookupResult(
            invocation_id,
            request_digest,
            "accepted",
            canonical.provider_invocation_id,
            None,
            self._result_digest("accepted_lookup", canonical.provider_invocation_id),
        )

    def mark_terminal(
        self,
        invocation_id: str,
        request_digest: str,
        terminal_evidence_digest: str,
    ) -> None:
        existing = self._operations.get(invocation_id, [])
        if len(existing) != 1 or existing[0].request_digest != request_digest:
            raise ConformanceHarnessError("reference target cannot terminalize unknown or ambiguous invocation")
        existing[0].terminal_evidence_digest = terminal_evidence_digest
