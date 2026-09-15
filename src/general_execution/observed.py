from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .canonical import sha256_digest
from .capacity import (
    CapacityLease,
    CapacityRelease,
    release_capacity_for_outcome,
    verify_capacity_state,
)
from .dispatch import (
    DispatchIntentError,
    DispatchIntentState,
    SqliteDispatchIntentStore,
    serialize_dispatch_state,
)
from .durable import DurableCapacityError, DurableCapacityHead, SqliteCapacityHeadStore
from .models import DispatchPlan, ExecutionSession, ExecutionSpec, RunnerCapabilities, RunnerRegistry
from .physical import PhysicalOutcomeBundle, verify_physical_outcome
from .physical_wire import (
    PhysicalOutcomeCodecError,
    deserialize_physical_outcome,
    serialize_physical_outcome,
)

OBSERVED_OUTCOME_SCHEMA = "ge.durable-observed-outcome.v1"


@dataclass(frozen=True, slots=True)
class DurableObservedOutcome:
    intent_id: str
    dispatch_state_digest: str
    runner_id: str
    lease_id: str
    lease_digest: str
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    request_digest: str
    physical_attempt: int
    outcome_digest: str
    observation_digest: str
    receipt_digest: str
    transport_status: str
    outcome: PhysicalOutcomeBundle
    schema_version: str = OBSERVED_OUTCOME_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != OBSERVED_OUTCOME_SCHEMA:
            raise ValueError("unsupported durable observed outcome schema")
        if self.physical_attempt < 1:
            raise ValueError("physical_attempt must be >= 1")
        for name in ("intent_id", "runner_id", "lease_id", "authorization_id", "invocation_id", "transport_status"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "dispatch_state_digest",
            "lease_digest",
            "authorization_digest",
            "request_digest",
            "outcome_digest",
            "observation_digest",
            "receipt_digest",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc
        auth = self.outcome.authorization
        request = auth.request
        receipt = self.outcome.receipt
        if (
            self.runner_id != request.runner_id
            or self.authorization_id != auth.authorization_id
            or self.authorization_digest != auth.digest
            or self.invocation_id != request.invocation_id
            or self.request_digest != request.digest
            or self.physical_attempt != auth.physical_attempt
            or self.outcome_digest != self.outcome.digest
            or self.observation_digest != self.outcome.observation.digest
            or self.receipt_digest != receipt.digest
            or self.transport_status != receipt.transport_status
        ):
            raise ValueError("durable observed outcome metadata does not match outcome")

    @property
    def digest(self) -> str:
        return sha256_digest(
            {
                "schema_version": self.schema_version,
                "intent_id": self.intent_id,
                "dispatch_state_digest": self.dispatch_state_digest,
                "runner_id": self.runner_id,
                "lease_id": self.lease_id,
                "lease_digest": self.lease_digest,
                "authorization_id": self.authorization_id,
                "authorization_digest": self.authorization_digest,
                "invocation_id": self.invocation_id,
                "request_digest": self.request_digest,
                "physical_attempt": self.physical_attempt,
                "outcome_digest": self.outcome_digest,
                "observation_digest": self.observation_digest,
                "receipt_digest": self.receipt_digest,
                "transport_status": self.transport_status,
            }
        )


@dataclass(frozen=True, slots=True)
class ObservedOutcomeReleaseRecovery:
    intent_id: str
    outcome_digest: str
    release_digest: str
    committed_state_digest: str
    committed_generation: int
    durable_head_digest: str
    idempotent: bool
    schema_version: str = "ge.observed-outcome-release-recovery.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.observed-outcome-release-recovery.v1":
            raise ValueError("unsupported observed outcome release recovery schema")
        if not self.intent_id or not self.intent_id.strip():
            raise ValueError("intent_id must be non-empty")
        if self.committed_generation < 1:
            raise ValueError("committed_generation must be >= 1")
        for name in ("outcome_digest", "release_digest", "committed_state_digest", "durable_head_digest"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")
            try:
                int(value[7:], 16)
            except ValueError as exc:
                raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _verify_outcome_against_dispatch(state: DispatchIntentState, outcome: PhysicalOutcomeBundle) -> bool:
    if state.status != "observed":
        return False
    intent = state.intent
    auth = outcome.authorization
    request = auth.request
    receipt = outcome.receipt
    return (
        intent.authorization_id == auth.authorization_id
        and intent.authorization_digest == auth.digest
        and intent.invocation_id == request.invocation_id
        and intent.request_digest == request.digest
        and intent.runner_id == request.runner_id
        and intent.runner_capability_digest == request.runner_capability_digest
        and intent.session_id == request.session_id
        and intent.logical_attempt == request.attempt
        and intent.physical_attempt == auth.physical_attempt
        and state.provider_invocation_id == receipt.provider_invocation_id
        and state.observation_digest == outcome.observation.digest
        and state.receipt_digest == receipt.digest
        and state.outcome_digest == outcome.digest
        and state.transport_status == receipt.transport_status
    )


def _durable_record(state: DispatchIntentState, outcome: PhysicalOutcomeBundle) -> DurableObservedOutcome:
    if not _verify_outcome_against_dispatch(state, outcome):
        raise DispatchIntentError("observed physical outcome does not match durable dispatch state")
    intent = state.intent
    auth = outcome.authorization
    return DurableObservedOutcome(
        intent_id=intent.intent_id,
        dispatch_state_digest=state.digest,
        runner_id=intent.runner_id,
        lease_id=intent.lease_id,
        lease_digest=intent.lease_digest,
        authorization_id=intent.authorization_id,
        authorization_digest=intent.authorization_digest,
        invocation_id=intent.invocation_id,
        request_digest=intent.request_digest,
        physical_attempt=auth.physical_attempt,
        outcome_digest=outcome.digest,
        observation_digest=outcome.observation.digest,
        receipt_digest=outcome.receipt.digest,
        transport_status=outcome.receipt.transport_status,
        outcome=outcome,
    )


class SqliteDurableObservedOutcomeStore(SqliteDispatchIntentStore):
    """Dispatch outbox that atomically retains the full admitted physical outcome."""

    def __init__(self, path: str | Path):
        super().__init__(path)
        self._ensure_observed_schema()

    def _ensure_observed_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dispatch_observed_outcomes (
                    intent_id TEXT PRIMARY KEY,
                    runner_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    lease_digest TEXT NOT NULL,
                    authorization_id TEXT NOT NULL UNIQUE,
                    authorization_digest TEXT NOT NULL,
                    invocation_id TEXT NOT NULL UNIQUE,
                    request_digest TEXT NOT NULL,
                    physical_attempt INTEGER NOT NULL,
                    dispatch_state_digest TEXT NOT NULL,
                    outcome_digest TEXT NOT NULL,
                    observation_digest TEXT NOT NULL,
                    receipt_digest TEXT NOT NULL,
                    transport_status TEXT NOT NULL,
                    outcome_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _outcome_columns() -> str:
        return (
            "intent_id, runner_id, lease_id, lease_digest, authorization_id, authorization_digest, "
            "invocation_id, request_digest, physical_attempt, dispatch_state_digest, outcome_digest, "
            "observation_digest, receipt_digest, transport_status, outcome_json"
        )

    @classmethod
    def _decode_outcome_row(cls, row, state: DispatchIntentState) -> DurableObservedOutcome:
        (
            intent_id,
            runner_id,
            lease_id,
            lease_digest,
            authorization_id,
            authorization_digest,
            invocation_id,
            request_digest,
            physical_attempt,
            dispatch_state_digest,
            outcome_digest,
            observation_digest,
            receipt_digest,
            transport_status,
            outcome_json,
        ) = row
        try:
            outcome = deserialize_physical_outcome(outcome_json)
        except PhysicalOutcomeCodecError as exc:
            raise DispatchIntentError("durable observed outcome payload is invalid") from exc
        record = _durable_record(state, outcome)
        if (
            intent_id != record.intent_id
            or runner_id != record.runner_id
            or lease_id != record.lease_id
            or lease_digest != record.lease_digest
            or authorization_id != record.authorization_id
            or authorization_digest != record.authorization_digest
            or invocation_id != record.invocation_id
            or request_digest != record.request_digest
            or physical_attempt != record.physical_attempt
            or dispatch_state_digest != record.dispatch_state_digest
            or outcome_digest != record.outcome_digest
            or observation_digest != record.observation_digest
            or receipt_digest != record.receipt_digest
            or transport_status != record.transport_status
        ):
            raise DispatchIntentError("durable observed outcome metadata mismatch")
        return record

    def load_observed_outcome(self, intent_id: str) -> DurableObservedOutcome:
        with self._connect() as connection:
            state_row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if state_row is None:
                raise DispatchIntentError("durable dispatch intent does not exist")
            state = self._decode_row(state_row)
            outcome_row = connection.execute(
                f"SELECT {self._outcome_columns()} FROM dispatch_observed_outcomes WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
        if state.status != "observed":
            if outcome_row is not None:
                raise DispatchIntentError("non-observed dispatch state has durable outcome bytes")
            raise DispatchIntentError("dispatch intent has no observed physical outcome")
        if outcome_row is None:
            raise DispatchIntentError("observed dispatch state is missing durable physical outcome bytes")
        return self._decode_outcome_row(outcome_row, state)

    def record_observed(
        self,
        intent_id: str,
        expected_state_digest: str,
        spec: ExecutionSpec,
        registry: RunnerRegistry,
        plan: DispatchPlan,
        session: ExecutionSession,
        runner: RunnerCapabilities,
        outcome: PhysicalOutcomeBundle,
    ) -> DispatchIntentState:
        if not verify_physical_outcome(spec, registry, plan, session, runner, outcome):
            raise DispatchIntentError("physical outcome does not verify")
        outcome_json = serialize_physical_outcome(outcome)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            state_row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if state_row is None:
                raise DispatchIntentError("durable dispatch intent does not exist")
            current = self._decode_row(state_row)
            existing_outcome_row = connection.execute(
                f"SELECT {self._outcome_columns()} FROM dispatch_observed_outcomes WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()

            if current.status == "observed":
                if expected_state_digest not in {current.digest, current.previous_state_digest}:
                    raise DispatchIntentError("stale durable dispatch intent state")
                if existing_outcome_row is None:
                    raise DispatchIntentError("observed dispatch state is missing durable physical outcome bytes")
                existing = self._decode_outcome_row(existing_outcome_row, current)
                if existing.outcome != outcome or existing_outcome_row[-1] != outcome_json:
                    raise DispatchIntentError("dispatch intent already has a different durable physical outcome")
                connection.commit()
                return current

            if current.digest != expected_state_digest:
                raise DispatchIntentError("stale durable dispatch intent state")
            if current.status != "submission_unknown":
                raise DispatchIntentError("provider observation requires submission_unknown state")
            if existing_outcome_row is not None:
                raise DispatchIntentError("non-observed dispatch state already has durable outcome bytes")

            intent = current.intent
            auth = outcome.authorization
            receipt = outcome.receipt
            if (
                auth.authorization_id != intent.authorization_id
                or auth.digest != intent.authorization_digest
                or auth.request.invocation_id != intent.invocation_id
                or auth.request.digest != intent.request_digest
                or auth.request.runner_id != intent.runner_id
                or auth.request.runner_capability_digest != intent.runner_capability_digest
                or auth.physical_attempt != intent.physical_attempt
            ):
                raise DispatchIntentError("physical outcome does not belong to durable dispatch intent")

            new_state = DispatchIntentState(
                intent=intent,
                status="observed",
                revision=2,
                previous_state_digest=current.digest,
                provider_invocation_id=receipt.provider_invocation_id,
                observation_digest=outcome.observation.digest,
                receipt_digest=receipt.digest,
                outcome_digest=outcome.digest,
                transport_status=receipt.transport_status,
            )
            record = _durable_record(new_state, outcome)

            cursor = connection.execute(
                """
                UPDATE dispatch_intents
                SET state_digest = ?, revision = ?, state_json = ?
                WHERE intent_id = ? AND runner_id = ? AND lease_id = ?
                  AND state_digest = ? AND revision = ?
                """,
                (
                    new_state.digest,
                    new_state.revision,
                    serialize_dispatch_state(new_state),
                    intent.intent_id,
                    intent.runner_id,
                    intent.lease_id,
                    current.digest,
                    current.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise DispatchIntentError("durable dispatch compare-and-swap failed")
            connection.execute(
                """
                INSERT INTO dispatch_observed_outcomes (
                    intent_id, runner_id, lease_id, lease_digest, authorization_id, authorization_digest,
                    invocation_id, request_digest, physical_attempt, dispatch_state_digest, outcome_digest,
                    observation_digest, receipt_digest, transport_status, outcome_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.intent_id,
                    record.runner_id,
                    record.lease_id,
                    record.lease_digest,
                    record.authorization_id,
                    record.authorization_digest,
                    record.invocation_id,
                    record.request_digest,
                    record.physical_attempt,
                    record.dispatch_state_digest,
                    record.outcome_digest,
                    record.observation_digest,
                    record.receipt_digest,
                    record.transport_status,
                    outcome_json,
                ),
            )

            committed_state_row = connection.execute(
                f"SELECT {self._select_columns()} FROM dispatch_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            committed_outcome_row = connection.execute(
                f"SELECT {self._outcome_columns()} FROM dispatch_observed_outcomes WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if committed_state_row is None or committed_outcome_row is None:
                raise DispatchIntentError("observed outcome transaction is incomplete")
            committed = self._decode_row(committed_state_row)
            if committed != new_state:
                raise DispatchIntentError("observed dispatch state does not match candidate")
            if self._decode_outcome_row(committed_outcome_row, committed).outcome != outcome:
                raise DispatchIntentError("durable physical outcome does not match candidate")
            connection.commit()
            return committed
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise DispatchIntentError("durable observed outcome uniqueness constraint rejected commit") from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def recover_observed_for_runner(self, runner_id: str) -> tuple[DurableObservedOutcome, ...]:
        states = self.load_for_runner(runner_id)
        return tuple(
            self.load_observed_outcome(state.intent.intent_id)
            for state in states
            if state.status == "observed"
        )


def _matching_active_lease(state, record: DurableObservedOutcome) -> CapacityLease | None:
    matches = [
        lease
        for lease in state.active_leases
        if lease.lease_id == record.lease_id
        and lease.digest == record.lease_digest
        and lease.authorization_id == record.authorization_id
        and lease.authorization_digest == record.authorization_digest
        and lease.invocation_id == record.invocation_id
        and lease.physical_attempt == record.physical_attempt
    ]
    if len(matches) > 1:
        raise DurableCapacityError("observed outcome matches multiple active capacity leases")
    return matches[0] if matches else None


def _matching_release(state, record: DurableObservedOutcome) -> CapacityRelease | None:
    matches = [
        release
        for release in state.releases
        if release.lease_id == record.lease_id
        and release.lease_digest == record.lease_digest
        and release.authorization_id == record.authorization_id
        and release.authorization_digest == record.authorization_digest
        and release.invocation_id == record.invocation_id
        and release.physical_attempt == record.physical_attempt
        and release.release_kind == "terminal_outcome"
        and release.outcome_digest == record.outcome_digest
        and release.receipt_digest == record.receipt_digest
        and release.transport_status == record.transport_status
    ]
    if len(matches) > 1:
        raise DurableCapacityError("observed outcome has duplicate canonical capacity releases")
    return matches[0] if matches else None


def _idempotent_release_recovery(
    state,
    head: DurableCapacityHead,
    record: DurableObservedOutcome,
) -> ObservedOutcomeReleaseRecovery | None:
    release = _matching_release(state, record)
    if release is None:
        return None
    return ObservedOutcomeReleaseRecovery(
        intent_id=record.intent_id,
        outcome_digest=record.outcome_digest,
        release_digest=release.digest,
        committed_state_digest=state.digest,
        committed_generation=state.generation,
        durable_head_digest=head.digest,
        idempotent=True,
    )


def release_observed_capacity_after_restart(
    dispatch_store: SqliteDurableObservedOutcomeStore,
    capacity_store: SqliteCapacityHeadStore,
    intent_id: str,
    spec: ExecutionSpec,
    registry: RunnerRegistry,
    plan: DispatchPlan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
) -> ObservedOutcomeReleaseRecovery:
    dispatch_state = dispatch_store.load(intent_id)
    if dispatch_state.status != "observed":
        raise DispatchIntentError("capacity release recovery requires observed dispatch state")
    record = dispatch_store.load_observed_outcome(intent_id)
    outcome = record.outcome
    if not verify_physical_outcome(spec, registry, plan, session, runner, outcome):
        raise DispatchIntentError("durable physical outcome no longer verifies against execution context")

    capacity_state, capacity_head = capacity_store.load(runner)
    if not verify_capacity_state(capacity_state, runner):
        raise DurableCapacityError("canonical capacity state does not replay")
    active = _matching_active_lease(capacity_state, record)
    if active is None:
        recovered = _idempotent_release_recovery(capacity_state, capacity_head, record)
        if recovered is None:
            raise DurableCapacityError("durable observed outcome is neither active nor canonically released")
        return recovered

    new_state, grant, _ = release_capacity_for_outcome(
        capacity_state,
        spec,
        registry,
        plan,
        session,
        runner,
        active,
        outcome,
    )
    try:
        committed_head: DurableCapacityHead = capacity_store.commit(
            runner,
            capacity_state.digest,
            new_state,
        )
    except DurableCapacityError:
        latest_state, latest_head = capacity_store.load(runner)
        recovered = _idempotent_release_recovery(latest_state, latest_head, record)
        if recovered is not None:
            return recovered
        raise
    return ObservedOutcomeReleaseRecovery(
        intent_id=record.intent_id,
        outcome_digest=record.outcome_digest,
        release_digest=grant.release.digest,
        committed_state_digest=new_state.digest,
        committed_generation=new_state.generation,
        durable_head_digest=committed_head.digest,
        idempotent=False,
    )
