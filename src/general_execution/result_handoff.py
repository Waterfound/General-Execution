from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import sha256_digest, stable_id
from .models import ExecutionSession, ResultEnvelope, RunnerCapabilities
from .reconciliation import ReconciliationCandidate, verify_reconciliation_candidate
from .session import SessionError, submit_result
from .wire import result_from_dict, result_to_dict, session_from_dict, session_to_dict


class ResultHandoffError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PendingLogicalResult:
    runner_id: str
    runner_capability_digest: str
    session_id: str
    logical_attempt: int
    spec_id: str
    spec_digest: str
    authorization_id: str
    reconciliation_id: str
    reconciliation_digest: str
    result: ResultEnvelope
    schema_version: str = "ge.pending-logical-result.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.pending-logical-result.v1":
            raise ValueError("unsupported pending logical result schema")
        for name in ("runner_id", "session_id", "spec_id", "authorization_id", "reconciliation_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.logical_attempt < 1:
            raise ValueError("logical_attempt must be >= 1")
        for name in ("runner_capability_digest", "spec_digest", "reconciliation_digest"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc
        if (
            self.result.session_id != self.session_id
            or self.result.spec_id != self.spec_id
            or self.result.spec_digest != self.spec_digest
            or self.result.runner_id != self.runner_id
            or self.result.attempt != self.logical_attempt
        ):
            raise ValueError("pending result is not bound to the declared logical execution identity")

    @property
    def pending_id(self) -> str:
        return stable_id(
            "geplr",
            {
                "runner_id": self.runner_id,
                "session_id": self.session_id,
                "logical_attempt": self.logical_attempt,
                "reconciliation_id": self.reconciliation_id,
                "result_digest": self.result.digest,
            },
        )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def pending_logical_result_to_dict(pending: PendingLogicalResult) -> dict[str, Any]:
    return {
        "schema_version": pending.schema_version,
        "runner_id": pending.runner_id,
        "runner_capability_digest": pending.runner_capability_digest,
        "session_id": pending.session_id,
        "logical_attempt": pending.logical_attempt,
        "spec_id": pending.spec_id,
        "spec_digest": pending.spec_digest,
        "authorization_id": pending.authorization_id,
        "reconciliation_id": pending.reconciliation_id,
        "reconciliation_digest": pending.reconciliation_digest,
        "result": result_to_dict(pending.result),
    }


def pending_logical_result_from_dict(data: dict[str, Any]) -> PendingLogicalResult:
    if data.get("schema_version") != "ge.pending-logical-result.v1":
        raise ResultHandoffError("unsupported pending logical result schema")
    try:
        return PendingLogicalResult(
            runner_id=str(data["runner_id"]),
            runner_capability_digest=str(data["runner_capability_digest"]),
            session_id=str(data["session_id"]),
            logical_attempt=int(data["logical_attempt"]),
            spec_id=str(data["spec_id"]),
            spec_digest=str(data["spec_digest"]),
            authorization_id=str(data["authorization_id"]),
            reconciliation_id=str(data["reconciliation_id"]),
            reconciliation_digest=str(data["reconciliation_digest"]),
            result=result_from_dict(data["result"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ResultHandoffError("invalid pending logical result payload") from exc


def pending_logical_result_from_reconciliation(
    candidate: ReconciliationCandidate,
    runner: RunnerCapabilities,
) -> PendingLogicalResult | None:
    if not verify_reconciliation_candidate(candidate, runner):
        raise ResultHandoffError("reconciliation candidate failed verification")
    result = candidate.outcome.result
    if result is None:
        return None
    record = candidate.record
    pending = PendingLogicalResult(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        session_id=record.session_id,
        logical_attempt=record.logical_attempt,
        spec_id=record.spec_id,
        spec_digest=record.spec_digest,
        authorization_id=record.authorization_id,
        reconciliation_id=record.reconciliation_id,
        reconciliation_digest=record.digest,
        result=result,
    )
    if not verify_pending_logical_result(pending, runner):
        raise ResultHandoffError("constructed pending logical result did not verify")
    return pending


def verify_pending_logical_result(pending: PendingLogicalResult, runner: RunnerCapabilities) -> bool:
    return (
        pending.runner_id == runner.runner_id
        and pending.runner_capability_digest == runner.digest
        and pending.result.session_id == pending.session_id
        and pending.result.spec_id == pending.spec_id
        and pending.result.spec_digest == pending.spec_digest
        and pending.result.runner_id == runner.runner_id
        and pending.result.attempt == pending.logical_attempt
    )


@dataclass(frozen=True, slots=True)
class LogicalResultSubmission:
    pending: PendingLogicalResult
    source_session_digest: str
    submitted_session: ExecutionSession
    schema_version: str = "ge.logical-result-submission.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.logical-result-submission.v1":
            raise ValueError("unsupported logical result submission schema")
        if not self.source_session_digest.startswith("sha256:") or len(self.source_session_digest) != 71:
            raise ValueError("source_session_digest must be sha256:<64-hex>")
        try:
            int(self.source_session_digest[7:], 16)
        except ValueError as exc:
            raise ValueError("source_session_digest must contain 64 hexadecimal characters") from exc
        if self.submitted_session.state != "result_submitted":
            raise ValueError("submitted_session must be result_submitted")
        if self.submitted_session.result_digest != self.pending.result.digest:
            raise ValueError("submitted_session result digest does not match pending result")

    @property
    def submission_id(self) -> str:
        return stable_id(
            "gels",
            {
                "pending_id": self.pending.pending_id,
                "pending_digest": self.pending.digest,
                "submitted_session_digest": sha256_digest(self.submitted_session),
            },
        )

    @property
    def digest(self) -> str:
        return sha256_digest(
            {
                "schema_version": self.schema_version,
                "pending_id": self.pending.pending_id,
                "pending_digest": self.pending.digest,
                "source_session_digest": self.source_session_digest,
                "submitted_session": session_to_dict(self.submitted_session),
            }
        )


def logical_result_submission_to_dict(submission: LogicalResultSubmission) -> dict[str, Any]:
    return {
        "schema_version": submission.schema_version,
        "pending_id": submission.pending.pending_id,
        "pending_digest": submission.pending.digest,
        "source_session_digest": submission.source_session_digest,
        "submitted_session": session_to_dict(submission.submitted_session),
    }


def logical_result_submission_from_dict(
    data: dict[str, Any],
    pending: PendingLogicalResult,
) -> LogicalResultSubmission:
    if data.get("schema_version") != "ge.logical-result-submission.v1":
        raise ResultHandoffError("unsupported logical result submission schema")
    if data.get("pending_id") != pending.pending_id or data.get("pending_digest") != pending.digest:
        raise ResultHandoffError("logical submission payload does not reference the exact pending result")
    try:
        return LogicalResultSubmission(
            pending=pending,
            source_session_digest=str(data["source_session_digest"]),
            submitted_session=session_from_dict(data["submitted_session"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ResultHandoffError("invalid logical result submission payload") from exc


def prepare_logical_result_submission(
    pending: PendingLogicalResult,
    session: ExecutionSession,
    runner: RunnerCapabilities,
) -> LogicalResultSubmission:
    if not verify_pending_logical_result(pending, runner):
        raise ResultHandoffError("pending logical result failed verification")
    if session.state != "running":
        raise ResultHandoffError("logical result submission requires a running Session")
    if (
        session.session_id != pending.session_id
        or session.attempt != pending.logical_attempt
        or session.spec_id != pending.spec_id
        or session.spec_digest != pending.spec_digest
        or session.runner_id != runner.runner_id
        or session.runner_capability_digest != runner.digest
    ):
        raise ResultHandoffError("Session does not match the pending logical result")
    try:
        submitted = submit_result(session, pending.result)
    except SessionError as exc:
        raise ResultHandoffError("pending result could not be submitted to the exact Session") from exc
    candidate = LogicalResultSubmission(
        pending=pending,
        source_session_digest=sha256_digest(session),
        submitted_session=submitted,
    )
    if not verify_logical_result_submission(candidate, session, runner):
        raise ResultHandoffError("constructed logical result submission did not verify")
    return candidate


def verify_logical_result_submission(
    submission: LogicalResultSubmission,
    source_session: ExecutionSession,
    runner: RunnerCapabilities,
) -> bool:
    if not verify_pending_logical_result(submission.pending, runner):
        return False
    if submission.source_session_digest != sha256_digest(source_session):
        return False
    if source_session.state != "running":
        return False
    try:
        expected = submit_result(source_session, submission.pending.result)
    except SessionError:
        return False
    return submission.submitted_session == expected
