from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .canonical import sha256_digest
from .capacity import CapacityRelease
from .durable import RecoveredInFlightLease, recover_after_restart
from .physical import PhysicalOutcomeBundle
from .persistence import SQLiteDurableHeadStore
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .recovery_context import DurableRecoveryContext, SQLiteRecoveryContextStore, verify_recovery_context
from .reference_bridge import query_reference_status
from .reference_registry import SQLiteReferenceJobRegistry

AttemptState = Literal[
    "orphan_context",
    "active_provider_unknown",
    "active_provider_running",
    "active_provider_terminal",
    "settled_failure",
    "settled_completed",
    "settled_revocation",
]
ProviderState = Literal["absent", "not_found", "running", "terminal"]


class AttemptHistoryError(ValueError):
    pass


class AttemptHistoryIntegrityError(AttemptHistoryError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class AttemptHistoryEntry:
    session_id: str
    logical_attempt: int
    physical_attempt: int
    authorization_id: str
    authorization_digest: str
    context_id: str
    context_digest: str
    state: AttemptState
    provider_state: ProviderState
    current_head_digest: str | None
    provider_job_id: str | None = None
    transport_status: str | None = None
    outcome_digest: str | None = None
    receipt_digest: str | None = None
    release_digest: str | None = None
    schema_version: str = "ge.attempt-history-entry.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.attempt-history-entry.v1":
            raise ValueError("unsupported attempt history entry schema")
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError("attempt ordinals must be >= 1")
        if self.state not in {
            "orphan_context",
            "active_provider_unknown",
            "active_provider_running",
            "active_provider_terminal",
            "settled_failure",
            "settled_completed",
            "settled_revocation",
        }:
            raise ValueError("unsupported attempt history state")
        if self.provider_state not in {"absent", "not_found", "running", "terminal"}:
            raise ValueError("unsupported provider state")
        for name in ("session_id", "authorization_id", "context_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("authorization_digest", "context_digest"):
            _require_sha256(name, getattr(self, name))
        for name in ("current_head_digest", "outcome_digest", "receipt_digest", "release_digest"):
            value = getattr(self, name)
            if value is not None:
                _require_sha256(name, value)
        if self.state in {"settled_failure", "settled_completed", "active_provider_terminal"}:
            if self.provider_state != "terminal" or self.outcome_digest is None or self.receipt_digest is None:
                raise ValueError("terminal attempt state requires exact physical outcome and receipt")
        if self.state in {"settled_failure", "settled_completed", "settled_revocation"} and self.release_digest is None:
            raise ValueError("settled attempt state requires release digest")
        if self.state == "settled_completed" and self.transport_status != "completed":
            raise ValueError("settled_completed requires completed transport status")
        if self.state == "settled_failure" and self.transport_status in {None, "completed"}:
            raise ValueError("settled_failure requires non-completed terminal transport status")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def retry_eligible(self) -> bool:
        return self.state == "settled_failure"


@dataclass(frozen=True, slots=True)
class AttemptHistory:
    entries: tuple[AttemptHistoryEntry, ...]
    schema_version: str = "ge.attempt-history.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.attempt-history.v1":
            raise ValueError("unsupported attempt history schema")
        keys = [
            (entry.authorization_id, entry.context_id)
            for entry in self.entries
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("attempt history contains duplicate context identity")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    def for_session(self, session_id: str) -> tuple[AttemptHistoryEntry, ...]:
        return tuple(entry for entry in self.entries if entry.session_id == session_id)


def _history_extends_anchor(current, context: DurableRecoveryContext) -> bool:
    anchor = context.anchor_snapshot
    transitions = current.state.transitions
    prefix = anchor.state.transitions
    return len(transitions) >= len(prefix) and transitions[: len(prefix)] == prefix


def _anchor_lease(context: DurableRecoveryContext, runner) -> RecoveredInFlightLease:
    _, report = recover_after_restart(context.anchor_snapshot, runner)
    matches = [
        lease
        for lease in report.active_leases
        if lease.lease_id == context.recovered_lease_id
        and lease.lease_digest == context.recovered_lease_digest
        and lease.authorization_id == context.authorization.authorization_id
    ]
    if len(matches) != 1:
        raise AttemptHistoryIntegrityError("context anchor does not reproduce exact recovered lease")
    return matches[0]


def _matching_release(current, context: DurableRecoveryContext) -> CapacityRelease | None:
    matches = [
        release
        for release in current.state.releases
        if release.lease_id == context.recovered_lease_id
        and release.lease_digest == context.recovered_lease_digest
        and release.authorization_id == context.authorization.authorization_id
    ]
    if len(matches) > 1:
        raise AttemptHistoryIntegrityError("authorization has multiple canonical releases")
    return matches[0] if matches else None


def reconstruct_terminal_outcome(
    context: DurableRecoveryContext,
    runner,
    provider_store: SQLiteReferenceJobRegistry,
) -> PhysicalOutcomeBundle:
    recovered = _anchor_lease(context, runner)
    probe = build_status_probe(context.anchor_snapshot, runner, recovered)
    observation = query_reference_status(provider_store, probe)
    if observation.status != "terminal":
        raise AttemptHistoryError("provider does not expose terminal evidence for historical attempt")
    assessment, outcome = assess_provider_status(
        context.anchor_snapshot,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        observation,
    )
    if assessment.disposition != "terminal_outcome" or outcome is None:
        raise AttemptHistoryIntegrityError("historical terminal evidence failed physical-outcome admission")
    return outcome


def _entry_for_context(
    context: DurableRecoveryContext,
    runner,
    current,
    provider_store: SQLiteReferenceJobRegistry,
) -> AttemptHistoryEntry:
    authorization = context.authorization
    key = reattachment_key_from_authorization(authorization, runner)
    record = provider_store.lookup(key)
    provider_job_id = record.job_id if record is not None else None

    common = dict(
        session_id=context.session.session_id,
        logical_attempt=context.session.attempt,
        physical_attempt=authorization.physical_attempt,
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.digest,
        context_id=context.context_id,
        context_digest=context.digest,
        provider_job_id=provider_job_id,
    )

    if current is None:
        if record is not None:
            raise AttemptHistoryIntegrityError("provider identity exists for orphan recovery context")
        return AttemptHistoryEntry(
            **common,
            state="orphan_context",
            provider_state="absent",
            current_head_digest=None,
        )

    if not _history_extends_anchor(current, context):
        # A future orphan context may have been persisted from a stale head and never committed.
        active_ids = {lease.authorization_id for lease in current.state.active_leases}
        released_ids = {release.authorization_id for release in current.state.releases}
        if authorization.authorization_id not in active_ids | released_ids:
            if record is not None:
                raise AttemptHistoryIntegrityError("uncommitted recovery context has provider identity")
            return AttemptHistoryEntry(
                **common,
                state="orphan_context",
                provider_state="absent",
                current_head_digest=current.head.digest,
            )
        raise AttemptHistoryIntegrityError("canonical capacity history does not extend committed context anchor")

    _, recovery = recover_after_restart(current, runner)
    active = [
        lease
        for lease in recovery.active_leases
        if lease.authorization_id == authorization.authorization_id
    ]
    if len(active) > 1:
        raise AttemptHistoryIntegrityError("authorization appears multiple times in active capacity state")
    if active:
        exact = [
            lease
            for lease in active
            if lease.lease_id == context.recovered_lease_id
            and lease.lease_digest == context.recovered_lease_digest
        ]
        if len(exact) != 1 or not verify_recovery_context(current, context):
            raise AttemptHistoryIntegrityError("active attempt does not match durable recovery context")
        probe = build_status_probe(current, runner, exact[0])
        observation = query_reference_status(provider_store, probe)
        assessment, outcome = assess_provider_status(
            current,
            context.spec,
            context.registry,
            context.plan,
            context.session,
            runner,
            context.authorization,
            probe,
            observation,
        )
        if observation.status == "not_found":
            if assessment.disposition != "remain_unknown" or outcome is not None:
                raise AttemptHistoryIntegrityError("not_found attempt was not conservatively assessed")
            return AttemptHistoryEntry(
                **common,
                state="active_provider_unknown",
                provider_state="not_found",
                current_head_digest=current.head.digest,
            )
        if observation.status == "running":
            if assessment.disposition != "keep_running" or outcome is not None:
                raise AttemptHistoryIntegrityError("running attempt did not preserve occupancy")
            return AttemptHistoryEntry(
                **common,
                state="active_provider_running",
                provider_state="running",
                current_head_digest=current.head.digest,
            )
        if assessment.disposition != "terminal_outcome" or outcome is None:
            raise AttemptHistoryIntegrityError("active terminal attempt failed outcome reconstruction")
        return AttemptHistoryEntry(
            **common,
            state="active_provider_terminal",
            provider_state="terminal",
            current_head_digest=current.head.digest,
            transport_status=outcome.receipt.transport_status,
            outcome_digest=outcome.digest,
            receipt_digest=outcome.receipt.digest,
        )

    release = _matching_release(current, context)
    if release is None:
        # Context can be a harmless orphan created after its source head became stale.
        if record is None:
            return AttemptHistoryEntry(
                **common,
                state="orphan_context",
                provider_state="absent",
                current_head_digest=current.head.digest,
            )
        raise AttemptHistoryIntegrityError("historical context has provider identity but no active lease or release")

    if release.release_kind == "session_revoked":
        provider_state: ProviderState = "absent" if record is None else record.state  # type: ignore[assignment]
        return AttemptHistoryEntry(
            **common,
            state="settled_revocation",
            provider_state=provider_state,
            current_head_digest=current.head.digest,
            release_digest=release.digest,
        )

    outcome = reconstruct_terminal_outcome(context, runner, provider_store)
    if release.outcome_digest != outcome.digest or release.receipt_digest != outcome.receipt.digest:
        raise AttemptHistoryIntegrityError("canonical release differs from reconstructed terminal outcome")
    state: AttemptState = (
        "settled_completed" if outcome.receipt.transport_status == "completed" else "settled_failure"
    )
    return AttemptHistoryEntry(
        **common,
        state=state,
        provider_state="terminal",
        current_head_digest=current.head.digest,
        transport_status=outcome.receipt.transport_status,
        outcome_digest=outcome.digest,
        receipt_digest=outcome.receipt.digest,
        release_digest=release.digest,
    )


def assess_attempt_history(
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    recovery_context_store_path: str | Path,
) -> AttemptHistory:
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)
    entries: list[AttemptHistoryEntry] = []
    for context, runner in context_store.bootstrap_candidates():
        current = capacity_store.load_current(runner)
        entries.append(_entry_for_context(context, runner, current, provider_store))
    entries.sort(
        key=lambda entry: (
            entry.session_id,
            entry.logical_attempt,
            entry.physical_attempt,
            entry.authorization_id,
        )
    )
    return AttemptHistory(tuple(entries))


def contexts_by_authorization(
    context_store: SQLiteRecoveryContextStore,
) -> dict[str, tuple[DurableRecoveryContext, object]]:
    return {
        context.authorization.authorization_id: (context, runner)
        for context, runner in context_store.bootstrap_candidates()
    }
