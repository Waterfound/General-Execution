from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .attempt_history import (
    AttemptHistoryEntry,
    assess_attempt_history,
    contexts_by_authorization,
    reconstruct_terminal_outcome,
)
from .canonical import sha256_digest, stable_id
from .capacity import reserve_capacity
from .cold_bootstrap import bootstrap_active_recovery_contexts
from .durable import build_durable_snapshot, recover_after_restart
from .persistence import SQLiteDurableHeadStore
from .physical import authorize_retry, observe_failure
from .reattachment import assess_provider_status, build_status_probe, reattachment_key_from_authorization
from .reconciliation import commit_reconciliation, plan_provider_outcome_reconciliation
from .recovery_context import SQLiteRecoveryContextStore, build_recovery_context
from .reference_bridge import query_reference_status, record_reference_terminal, register_reference_invocation
from .reference_registry import SQLiteReferenceJobRegistry
from .session_settlement import (
    DurableSessionRecord,
    SessionSettlementReceipt,
    SQLiteSessionSettlementStore,
)


class RetryLifecycleError(ValueError):
    pass


class RetryLifecycleIntegrityError(RetryLifecycleError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _require_distinct_paths(*paths: str | Path) -> None:
    resolved = [Path(path).resolve() for path in paths]
    if len(resolved) != len(set(resolved)):
        raise RetryLifecycleError("retry lifecycle stores must use distinct filesystem paths")


@dataclass(frozen=True, slots=True)
class FailureSettlementReceipt:
    session_id: str
    physical_attempt: int
    authorization_id: str
    transport_status: str
    outcome_digest: str
    physical_receipt_digest: str
    committed_head_digest: str
    session_record_digest: str
    schema_version: str = "ge.failure-settlement-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.failure-settlement-receipt.v1":
            raise ValueError("unsupported failure settlement receipt schema")
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        for name in ("session_id", "authorization_id", "transport_status"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.transport_status == "completed":
            raise ValueError("failure settlement cannot use completed transport status")
        for name in (
            "outcome_digest",
            "physical_receipt_digest",
            "committed_head_digest",
            "session_record_digest",
        ):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RetryPreparationReceipt:
    session_id: str
    prior_physical_attempt: int
    prior_outcome_digest: str
    prior_receipt_digest: str
    retry_physical_attempt: int
    retry_authorization_id: str
    retry_authorization_digest: str
    retry_context_id: str
    retry_context_digest: str
    committed_head_digest: str
    provider_key: str
    provider_job_id: str
    idempotent: bool
    schema_version: str = "ge.retry-preparation-receipt.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.retry-preparation-receipt.v1":
            raise ValueError("unsupported retry preparation receipt schema")
        if self.prior_physical_attempt < 1 or self.retry_physical_attempt != self.prior_physical_attempt + 1:
            raise ValueError("retry physical attempt must immediately follow prior attempt")
        for name in (
            "session_id",
            "retry_authorization_id",
            "retry_context_id",
            "provider_key",
            "provider_job_id",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "prior_outcome_digest",
            "prior_receipt_digest",
            "retry_authorization_digest",
            "retry_context_digest",
            "committed_head_digest",
        ):
            _require_sha256(name, getattr(self, name))

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _committed_session_ids(entries) -> set[str]:
    return {entry.session_id for entry in entries if entry.state != "orphan_context"}


def _one_session_record(
    session_store: SQLiteSessionSettlementStore,
    history_entries,
    *,
    require_running: bool,
):
    session_ids = _committed_session_ids(history_entries)
    if len(session_ids) != 1:
        raise RetryLifecycleError("reference retry lifecycle requires exactly one committed logical Session")
    record = session_store.load(next(iter(session_ids)))
    if record is None:
        raise RetryLifecycleIntegrityError("retry Session has no durable logical state")
    if require_running:
        expected = DurableSessionRecord(record.source_session, record.source_session)
        if record.current_session.state != "running" or record != expected:
            raise RetryLifecycleError("retry requires durable logical Session to remain running")
    return record


def _latest_failure(history, session_id: str) -> AttemptHistoryEntry:
    failures = [entry for entry in history.for_session(session_id) if entry.state == "settled_failure"]
    if not failures:
        raise RetryLifecycleError("no canonically settled physical failure is available for retry")
    return max(failures, key=lambda entry: entry.physical_attempt)


def _active_entries(history, session_id: str):
    return tuple(
        entry
        for entry in history.for_session(session_id)
        if entry.state in {"active_provider_unknown", "active_provider_running", "active_provider_terminal"}
    )


def settle_active_reference_failure(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
    *,
    transport_status: str = "timed_out",
    failure_code: str = "reference.retry.failure",
) -> FailureSettlementReceipt:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    if transport_status == "completed":
        raise RetryLifecycleError("failure lifecycle requires non-completed terminal transport status")

    session_store = SQLiteSessionSettlementStore(session_store_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)
    bindings = bootstrap_active_recovery_contexts(context_store, capacity_store)
    if len(bindings) != 1:
        raise RetryLifecycleError("failure settlement requires exactly one active physical attempt")
    binding = bindings[0]
    context, runner, source, recovered = (
        binding.context,
        binding.runner,
        binding.current_snapshot,
        binding.recovered_lease,
    )

    session_record = session_store.load(context.session.session_id)
    if session_record is None or session_record != DurableSessionRecord(context.session, context.session):
        raise RetryLifecycleIntegrityError("active physical failure requires exact durable running Session")

    probe = build_status_probe(source, runner, recovered)
    running = query_reference_status(provider_store, probe)
    if running.status != "running" or running.provider_invocation_id is None:
        raise RetryLifecycleError("reference failure requires provider attempt to be running")
    physical = observe_failure(
        context.authorization,
        transport_status,
        failure_code=failure_code,
        provider_invocation_id=running.provider_invocation_id,
    )
    key = reattachment_key_from_authorization(context.authorization, runner)
    record_reference_terminal(provider_store, key, physical)
    terminal = query_reference_status(provider_store, probe)
    assessment, outcome = assess_provider_status(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        context.authorization,
        probe,
        terminal,
    )
    if assessment.disposition != "terminal_outcome" or outcome is None or outcome.result is not None:
        raise RetryLifecycleIntegrityError("failure terminal state did not reconstruct result-free physical outcome")
    plan = plan_provider_outcome_reconciliation(
        source,
        context.spec,
        context.registry,
        context.plan,
        context.session,
        runner,
        recovered,
        outcome,
    )
    committed, _, _ = commit_reconciliation(capacity_store, runner, plan)
    if any(lease.authorization_id == context.authorization.authorization_id for lease in committed.state.active_leases):
        raise RetryLifecycleIntegrityError("failure reconciliation did not release failed authorization")
    still_running = session_store.load(context.session.session_id)
    if still_running != session_record:
        raise RetryLifecycleIntegrityError("physical failure unexpectedly changed logical Session")
    return FailureSettlementReceipt(
        session_id=context.session.session_id,
        physical_attempt=context.authorization.physical_attempt,
        authorization_id=context.authorization.authorization_id,
        transport_status=outcome.receipt.transport_status,
        outcome_digest=outcome.digest,
        physical_receipt_digest=outcome.receipt.digest,
        committed_head_digest=committed.head.digest,
        session_record_digest=still_running.digest,
    )


def prepare_retry_from_durable_failure(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> RetryPreparationReceipt:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    session_store = SQLiteSessionSettlementStore(session_store_path)
    context_store = SQLiteRecoveryContextStore(recovery_context_store_path)
    capacity_store = SQLiteDurableHeadStore(capacity_store_path)
    provider_store = SQLiteReferenceJobRegistry(provider_registry_path)

    history = assess_attempt_history(capacity_store_path, provider_registry_path, recovery_context_store_path)
    session_record = _one_session_record(session_store, history.entries, require_running=True)
    session_id = session_record.session_id
    prior_entry = _latest_failure(history, session_id)
    contexts = contexts_by_authorization(context_store)
    if prior_entry.authorization_id not in contexts:
        raise RetryLifecycleIntegrityError("latest failed authorization has no durable recovery context")
    prior_context, runner = contexts[prior_entry.authorization_id]
    prior_outcome = reconstruct_terminal_outcome(prior_context, runner, provider_store)
    if prior_outcome.digest != prior_entry.outcome_digest or prior_outcome.receipt.digest != prior_entry.receipt_digest:
        raise RetryLifecycleIntegrityError("latest failed outcome differs from durable attempt history")
    if prior_context.session != session_record.source_session:
        raise RetryLifecycleIntegrityError("retry history Session differs from durable logical Session")

    active = _active_entries(history, session_id)
    if active:
        if len(active) != 1:
            raise RetryLifecycleIntegrityError("logical Session has multiple active physical attempts")
        current_entry = active[0]
        if current_entry.physical_attempt != prior_entry.physical_attempt + 1:
            raise RetryLifecycleError("active physical attempt is not the expected retry successor")
        retry_context, retry_runner = contexts[current_entry.authorization_id]
        if retry_runner != runner:
            raise RetryLifecycleIntegrityError("active retry changed runner definition")
        auth = retry_context.authorization
        if (
            auth.previous_invocation_id != prior_context.authorization.request.invocation_id
            or auth.previous_receipt_digest != prior_outcome.receipt.digest
        ):
            raise RetryLifecycleIntegrityError("active retry predecessor binding is invalid")
        key = reattachment_key_from_authorization(auth, runner)
        registration_key, registration = register_reference_invocation(provider_store, auth, runner)
        if registration_key != key:
            raise RetryLifecycleIntegrityError("active retry provider key changed during recovery")
        current = capacity_store.load_current(runner)
        if current is None:
            raise RetryLifecycleIntegrityError("active retry has no canonical capacity head")
        return RetryPreparationReceipt(
            session_id=session_id,
            prior_physical_attempt=prior_entry.physical_attempt,
            prior_outcome_digest=prior_outcome.digest,
            prior_receipt_digest=prior_outcome.receipt.digest,
            retry_physical_attempt=auth.physical_attempt,
            retry_authorization_id=auth.authorization_id,
            retry_authorization_digest=auth.digest,
            retry_context_id=retry_context.context_id,
            retry_context_digest=retry_context.digest,
            committed_head_digest=current.head.digest,
            provider_key=key.provider_key,
            provider_job_id=registration.job_id,
            idempotent=registration.idempotent,
        )

    current = capacity_store.load_current(runner)
    if current is None:
        raise RetryLifecycleIntegrityError("retry source has no canonical capacity head")
    invocation_id = stable_id(
        "gei",
        {
            "session_id": session_id,
            "logical_attempt": session_record.source_session.attempt,
            "physical_attempt": prior_entry.physical_attempt + 1,
            "source_head_digest": current.head.digest,
            "prior_receipt_digest": prior_outcome.receipt.digest,
        },
    )
    auth = authorize_retry(
        prior_context.spec,
        prior_context.registry,
        prior_context.plan,
        prior_context.session,
        runner,
        prior_outcome,
        invocation_id=invocation_id,
    )
    next_state, _, _ = reserve_capacity(
        current.state,
        prior_context.spec,
        prior_context.registry,
        prior_context.plan,
        prior_context.session,
        runner,
        auth,
    )
    anchor = build_durable_snapshot(next_state, runner, previous=current)
    _, recovery = recover_after_restart(anchor, runner)
    recovered = [lease for lease in recovery.active_leases if lease.authorization_id == auth.authorization_id]
    if len(recovered) != 1:
        raise RetryLifecycleIntegrityError("retry anchor did not create one exact active lease")
    retry_context = build_recovery_context(
        anchor,
        prior_context.spec,
        prior_context.registry,
        prior_context.plan,
        prior_context.session,
        runner,
        auth,
        recovered[0],
    )

    # If this CAS loses to an unrelated writer, the saved context is a safe orphan.
    # A later retry call derives a new authorization from the then-current head digest.
    context_store.save(retry_context, anchor)
    capacity_store.compare_and_swap(anchor, runner, expected_head_digest=current.head.digest)
    key = reattachment_key_from_authorization(auth, runner)
    registered_key, registration = register_reference_invocation(provider_store, auth, runner)
    if registered_key != key:
        raise RetryLifecycleIntegrityError("retry provider registration changed deterministic key")
    return RetryPreparationReceipt(
        session_id=session_id,
        prior_physical_attempt=prior_entry.physical_attempt,
        prior_outcome_digest=prior_outcome.digest,
        prior_receipt_digest=prior_outcome.receipt.digest,
        retry_physical_attempt=auth.physical_attempt,
        retry_authorization_id=auth.authorization_id,
        retry_authorization_digest=auth.digest,
        retry_context_id=retry_context.context_id,
        retry_context_digest=retry_context.digest,
        committed_head_digest=anchor.head.digest,
        provider_key=key.provider_key,
        provider_job_id=registration.job_id,
        idempotent=False,
    )


def settle_latest_completed_result(
    session_store_path: str | Path,
    recovery_context_store_path: str | Path,
    capacity_store_path: str | Path,
    provider_registry_path: str | Path,
) -> SessionSettlementReceipt:
    _require_distinct_paths(
        session_store_path,
        recovery_context_store_path,
        capacity_store_path,
        provider_registry_path,
    )
    history = assess_attempt_history(capacity_store_path, provider_registry_path, recovery_context_store_path)
    session_store = SQLiteSessionSettlementStore(session_store_path)
    record = _one_session_record(session_store, history.entries, require_running=False)
    if _active_entries(history, record.session_id):
        raise RetryLifecycleError("logical result cannot settle while a physical attempt remains active")
    completed = [
        entry
        for entry in history.for_session(record.session_id)
        if entry.state == "settled_completed"
    ]
    if not completed:
        raise RetryLifecycleError("no canonically settled completed physical attempt exists")
    latest = max(completed, key=lambda entry: entry.physical_attempt)
    contexts = contexts_by_authorization(SQLiteRecoveryContextStore(recovery_context_store_path))
    if latest.authorization_id not in contexts:
        raise RetryLifecycleIntegrityError("latest completed authorization has no durable context")
    context, runner = contexts[latest.authorization_id]
    outcome = reconstruct_terminal_outcome(
        context,
        runner,
        SQLiteReferenceJobRegistry(provider_registry_path),
    )
    if outcome.digest != latest.outcome_digest or outcome.result is None:
        raise RetryLifecycleIntegrityError("latest completed history entry does not reproduce logical result")
    if context.session != record.source_session:
        raise RetryLifecycleIntegrityError("completed physical attempt Session differs from durable logical Session")
    return session_store.submit_result(record.source_session, outcome.result)
