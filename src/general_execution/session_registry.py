from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .canonical import sha256_digest, stable_id
from .models import ExecutionSession, RunnerCapabilities
from .result_handoff import LogicalResultSubmission, verify_logical_result_submission
from .session import SessionError, revoke_session, start_session
from .wire import session_from_dict, session_to_dict

SessionTransitionKind = Literal["register", "start", "revoke", "submit_result"]
VALID_SESSION_TRANSITION_KINDS = frozenset({"register", "start", "revoke", "submit_result"})


class SessionRegistryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SessionRegistryTransition:
    kind: SessionTransitionKind
    revision: int
    session_id: str
    expected_session_digest: str | None
    source_session: ExecutionSession | None
    target_session: ExecutionSession
    result_submission_id: str | None = None
    result_submission_digest: str | None = None
    schema_version: str = "ge.session-registry-transition.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.session-registry-transition.v1":
            raise ValueError("unsupported session registry transition schema")
        if self.kind not in VALID_SESSION_TRANSITION_KINDS:
            raise ValueError("unsupported session registry transition kind")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must be non-empty")
        if self.kind == "register":
            if self.revision != 1 or self.source_session is not None or self.expected_session_digest is not None:
                raise ValueError("register transition must be revision 1 without a predecessor")
        else:
            if self.revision < 2 or self.source_session is None or self.expected_session_digest is None:
                raise ValueError("non-register transition requires a predecessor")
            _require_sha256("expected_session_digest", self.expected_session_digest)
        if self.kind == "submit_result":
            if not self.result_submission_id or not self.result_submission_digest:
                raise ValueError("submit_result transition requires logical result submission binding")
            _require_sha256("result_submission_digest", self.result_submission_digest)
        elif self.result_submission_id is not None or self.result_submission_digest is not None:
            raise ValueError("only submit_result may carry logical result submission binding")

    @property
    def transition_id(self) -> str:
        return stable_id("gesrt", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _same_logical_identity(a: ExecutionSession, b: ExecutionSession) -> bool:
    return (
        a.session_id == b.session_id
        and a.spec_id == b.spec_id
        and a.spec_digest == b.spec_digest
        and a.plan_id == b.plan_id
        and a.plan_digest == b.plan_digest
        and a.runner_id == b.runner_id
        and a.runner_capability_digest == b.runner_capability_digest
        and a.mode == b.mode
        and a.attempt == b.attempt
    )


def session_registry_transition_to_dict(transition: SessionRegistryTransition) -> dict[str, Any]:
    return {
        "schema_version": transition.schema_version,
        "kind": transition.kind,
        "revision": transition.revision,
        "session_id": transition.session_id,
        "expected_session_digest": transition.expected_session_digest,
        "source_session": session_to_dict(transition.source_session) if transition.source_session else None,
        "target_session": session_to_dict(transition.target_session),
        "result_submission_id": transition.result_submission_id,
        "result_submission_digest": transition.result_submission_digest,
    }


def session_registry_transition_from_dict(data: dict[str, Any]) -> SessionRegistryTransition:
    if data.get("schema_version") != "ge.session-registry-transition.v1":
        raise SessionRegistryError("unsupported session registry transition schema")
    try:
        source = data.get("source_session")
        return SessionRegistryTransition(
            kind=str(data["kind"]),
            revision=int(data["revision"]),
            session_id=str(data["session_id"]),
            expected_session_digest=(
                str(data["expected_session_digest"]) if data.get("expected_session_digest") is not None else None
            ),
            source_session=session_from_dict(source) if source is not None else None,
            target_session=session_from_dict(data["target_session"]),
            result_submission_id=(
                str(data["result_submission_id"]) if data.get("result_submission_id") is not None else None
            ),
            result_submission_digest=(
                str(data["result_submission_digest"]) if data.get("result_submission_digest") is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionRegistryError("invalid session registry transition payload") from exc


def register_session_transition(session: ExecutionSession) -> SessionRegistryTransition:
    if session.state != "bound":
        raise SessionRegistryError("only a bound Session can be registered")
    transition = SessionRegistryTransition(
        kind="register",
        revision=1,
        session_id=session.session_id,
        expected_session_digest=None,
        source_session=None,
        target_session=session,
    )
    if not verify_session_registry_transition(transition):
        raise SessionRegistryError("constructed register transition did not verify")
    return transition


def start_session_transition(current: ExecutionSession, revision: int) -> SessionRegistryTransition:
    try:
        target = start_session(current)
    except SessionError as exc:
        raise SessionRegistryError("Session cannot start from current state") from exc
    transition = SessionRegistryTransition(
        kind="start",
        revision=revision,
        session_id=current.session_id,
        expected_session_digest=sha256_digest(current),
        source_session=current,
        target_session=target,
    )
    if not verify_session_registry_transition(transition):
        raise SessionRegistryError("constructed start transition did not verify")
    return transition


def revoke_session_transition(current: ExecutionSession, revision: int) -> SessionRegistryTransition:
    try:
        target = revoke_session(current)
    except SessionError as exc:
        raise SessionRegistryError("Session cannot be revoked from current state") from exc
    transition = SessionRegistryTransition(
        kind="revoke",
        revision=revision,
        session_id=current.session_id,
        expected_session_digest=sha256_digest(current),
        source_session=current,
        target_session=target,
    )
    if not verify_session_registry_transition(transition):
        raise SessionRegistryError("constructed revoke transition did not verify")
    return transition


def submit_session_transition(
    current: ExecutionSession,
    submission: LogicalResultSubmission,
    runner: RunnerCapabilities,
    revision: int,
) -> SessionRegistryTransition:
    if not verify_logical_result_submission(submission, current, runner):
        raise SessionRegistryError("logical result submission does not reproduce from current Session")
    transition = SessionRegistryTransition(
        kind="submit_result",
        revision=revision,
        session_id=current.session_id,
        expected_session_digest=sha256_digest(current),
        source_session=current,
        target_session=submission.submitted_session,
        result_submission_id=submission.submission_id,
        result_submission_digest=submission.digest,
    )
    if not verify_session_registry_transition(transition):
        raise SessionRegistryError("constructed submit_result transition did not verify structurally")
    return transition


def verify_session_registry_transition(transition: SessionRegistryTransition) -> bool:
    target = transition.target_session
    if transition.session_id != target.session_id:
        return False
    if transition.kind == "register":
        return target.state == "bound" and target.result_digest is None

    source = transition.source_session
    if source is None:
        return False
    if transition.session_id != source.session_id or not _same_logical_identity(source, target):
        return False
    if transition.expected_session_digest != sha256_digest(source):
        return False
    try:
        if transition.kind == "start":
            return target == start_session(source)
        if transition.kind == "revoke":
            return target == revoke_session(source)
        if transition.kind == "submit_result":
            return (
                source.state == "running"
                and target.state == "result_submitted"
                and target.result_digest is not None
                and transition.result_submission_id is not None
                and transition.result_submission_digest is not None
            )
    except SessionError:
        return False
    return False


def verify_session_registry_chain(transitions: tuple[SessionRegistryTransition, ...]) -> bool:
    if not transitions:
        return False
    if transitions[0].kind != "register" or transitions[0].revision != 1:
        return False
    seen_ids: set[str] = set()
    current: ExecutionSession | None = None
    for revision, transition in enumerate(transitions, start=1):
        if transition.revision != revision or transition.transition_id in seen_ids:
            return False
        seen_ids.add(transition.transition_id)
        if not verify_session_registry_transition(transition):
            return False
        if revision == 1:
            if transition.source_session is not None:
                return False
        else:
            if current is None or transition.source_session != current:
                return False
            if current.state in {"revoked", "result_submitted"}:
                return False
        current = transition.target_session
    return True
