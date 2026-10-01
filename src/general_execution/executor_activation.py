from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sqlite3
from pathlib import Path
from typing import Literal, Protocol

from .canonical import canonical_json, sha256_digest, stable_id
from .execution_launch_admission import ExecutionLaunchReceipt

CAPABILITY_SCHEMA = "ge.executor-activation-capability.v1"
INTENT_SCHEMA = "ge.executor-activation-intent.v1"
OBSERVATION_SCHEMA = "ge.executor-activation-observation.v1"
STATE_SCHEMA = "ge.executor-activation-state.v1"

ActivationOutcome = Literal[
    "EXECUTOR_ACCEPTED",
    "CONDITION_WAIT",
    "FAILED_ACTIVATION",
]
ActivationStatus = Literal[
    "prepared",
    "activation_unknown",
    "executor_accepted",
    "condition_wait",
    "failed_activation",
]
ReplayStatus = Literal["CREATED", "RECOVERED", "ALREADY_RECORDED"]


class ExecutorActivationError(ValueError):
    pass


def _nonempty(name: str, value: str | None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExecutorActivationError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
    ):
        raise ExecutorActivationError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ExecutorActivationError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


@dataclass(frozen=True, slots=True)
class ExecutorActivationCapability:
    executor: str
    adapter_id: str
    adapter_version: str
    evidence_ref: str
    evidence_digest: str
    available: bool = True
    idempotency_key: str = "dispatch_identity"
    idempotent_replay: bool = True
    authority_created: bool = False
    schema_version: str = CAPABILITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_SCHEMA:
            raise ExecutorActivationError("unsupported activation capability schema")
        for name in ("executor", "adapter_id", "adapter_version", "evidence_ref"):
            _nonempty(name, getattr(self, name))
        _digest("evidence_digest", self.evidence_digest)
        if self.idempotency_key != "dispatch_identity":
            raise ExecutorActivationError(
                "executor activation must be idempotent by dispatch_identity"
            )
        if not self.idempotent_replay:
            raise ExecutorActivationError(
                "executor activation adapter must support idempotent replay"
            )
        if self.authority_created:
            raise ExecutorActivationError(
                "executor activation capability cannot create authority"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutorActivationIntent:
    receipt_id: str
    receipt_digest: str
    order_digest: str
    workstream_id: str
    launch_id: str
    dispatch_identity: str
    owner: str
    repository: str
    executor: str
    authority_ref: str | None
    authority_binding_digest: str | None
    capability_digest: str
    authority_created: bool = False
    schema_version: str = INTENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != INTENT_SCHEMA:
            raise ExecutorActivationError("unsupported activation intent schema")
        for name in (
            "receipt_id",
            "workstream_id",
            "launch_id",
            "dispatch_identity",
            "owner",
            "repository",
            "executor",
        ):
            _nonempty(name, getattr(self, name))
        for name in ("receipt_digest", "order_digest", "capability_digest"):
            _digest(name, getattr(self, name))
        if self.authority_binding_digest is not None:
            _digest("authority_binding_digest", self.authority_binding_digest)
        if self.authority_created:
            raise ExecutorActivationError("activation intent cannot create authority")

    @property
    def activation_id(self) -> str:
        return stable_id("gea", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class NativeActivationObservation:
    activation_id: str
    dispatch_identity: str
    executor: str
    outcome: ActivationOutcome
    evidence_ref: str
    evidence_digest: str
    native_execution_ref: str | None = None
    condition_ref: str | None = None
    failure_reason: str | None = None
    idempotency_key: str = "dispatch_identity"
    authority_created: bool = False
    schema_version: str = OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != OBSERVATION_SCHEMA:
            raise ExecutorActivationError("unsupported activation observation schema")
        for name in (
            "activation_id",
            "dispatch_identity",
            "executor",
            "evidence_ref",
        ):
            _nonempty(name, getattr(self, name))
        _digest("evidence_digest", self.evidence_digest)
        if self.idempotency_key != "dispatch_identity":
            raise ExecutorActivationError(
                "activation observation must bind dispatch_identity idempotency"
            )
        if self.authority_created:
            raise ExecutorActivationError(
                "activation observation cannot create authority"
            )
        if self.outcome == "EXECUTOR_ACCEPTED":
            _nonempty("native_execution_ref", self.native_execution_ref)
            if self.condition_ref is not None or self.failure_reason is not None:
                raise ExecutorActivationError(
                    "accepted activation cannot carry wait/failure fields"
                )
        elif self.outcome == "CONDITION_WAIT":
            _nonempty("condition_ref", self.condition_ref)
            if self.native_execution_ref is not None or self.failure_reason is not None:
                raise ExecutorActivationError(
                    "condition wait cannot claim native execution or failure"
                )
        elif self.outcome == "FAILED_ACTIVATION":
            _nonempty("failure_reason", self.failure_reason)
            if self.native_execution_ref is not None or self.condition_ref is not None:
                raise ExecutorActivationError(
                    "failed activation cannot claim native execution or condition"
                )
        else:
            raise ExecutorActivationError("unsupported activation outcome")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutorActivationState:
    intent: ExecutorActivationIntent
    status: ActivationStatus
    revision: int
    previous_state_digest: str | None = None
    observation_digest: str | None = None
    native_execution_ref: str | None = None
    condition_ref: str | None = None
    failure_reason: str | None = None
    authority_created: bool = False
    schema_version: str = STATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != STATE_SCHEMA:
            raise ExecutorActivationError("unsupported activation state schema")
        if self.authority_created:
            raise ExecutorActivationError("activation state cannot create authority")
        if self.status == "prepared":
            if self.revision != 0 or self.previous_state_digest is not None:
                raise ExecutorActivationError(
                    "prepared activation must be revision 0 without predecessor"
                )
            if any(
                value is not None
                for value in (
                    self.observation_digest,
                    self.native_execution_ref,
                    self.condition_ref,
                    self.failure_reason,
                )
            ):
                raise ExecutorActivationError(
                    "prepared activation cannot claim activation evidence"
                )
        elif self.status == "activation_unknown":
            if self.revision != 1 or self.previous_state_digest is None:
                raise ExecutorActivationError(
                    "activation_unknown must be revision 1 with predecessor"
                )
            if any(
                value is not None
                for value in (
                    self.observation_digest,
                    self.native_execution_ref,
                    self.condition_ref,
                    self.failure_reason,
                )
            ):
                raise ExecutorActivationError(
                    "activation_unknown cannot claim an observed outcome"
                )
        elif self.status in {
            "executor_accepted",
            "condition_wait",
            "failed_activation",
        }:
            if self.revision != 2 or self.previous_state_digest is None:
                raise ExecutorActivationError(
                    "observed activation state must be revision 2 with predecessor"
                )
            if self.observation_digest is None:
                raise ExecutorActivationError(
                    "observed activation state requires observation digest"
                )
            _digest("observation_digest", self.observation_digest)
            if self.status == "executor_accepted":
                _nonempty("native_execution_ref", self.native_execution_ref)
            elif self.status == "condition_wait":
                _nonempty("condition_ref", self.condition_ref)
            else:
                _nonempty("failure_reason", self.failure_reason)
        else:
            raise ExecutorActivationError("unsupported activation state")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutorActivationResult:
    state: ExecutorActivationState
    replay_status: ReplayStatus

    @property
    def native_execution_ref(self) -> str | None:
        return self.state.native_execution_ref


class ExecutorActivationAdapter(Protocol):
    capability: ExecutorActivationCapability

    def activate(
        self,
        intent: ExecutorActivationIntent,
    ) -> NativeActivationObservation:
        ...


def prepare_executor_activation(
    receipt: ExecutionLaunchReceipt,
    capability: ExecutorActivationCapability,
) -> ExecutorActivationIntent:
    if receipt.disposition != "ADMITTED":
        raise ExecutorActivationError(
            "executor activation requires an ADMITTED launch receipt"
        )
    if receipt.execution_triggered:
        raise ExecutorActivationError(
            "EAC-01 cannot consume a receipt that already claims execution"
        )
    if not all(
        (
            receipt.launch_id,
            receipt.dispatch_identity,
            receipt.owner,
            receipt.repository,
            receipt.executor,
        )
    ):
        raise ExecutorActivationError(
            "ADMITTED receipt lacks complete activation identity"
        )
    if receipt.executor != capability.executor:
        raise ExecutorActivationError("activation capability executor mismatch")
    return ExecutorActivationIntent(
        receipt_id=receipt.receipt_id,
        receipt_digest=receipt.digest,
        order_digest=receipt.order_digest,
        workstream_id=receipt.workstream_id,
        launch_id=receipt.launch_id,
        dispatch_identity=receipt.dispatch_identity,
        owner=receipt.owner,
        repository=receipt.repository,
        executor=receipt.executor,
        authority_ref=receipt.authority_ref,
        authority_binding_digest=receipt.authority_binding_digest,
        capability_digest=capability.digest,
    )


def initial_activation_state(
    intent: ExecutorActivationIntent,
) -> ExecutorActivationState:
    return ExecutorActivationState(intent=intent, status="prepared", revision=0)


def begin_activation(
    state: ExecutorActivationState,
) -> ExecutorActivationState:
    if state.status != "prepared":
        raise ExecutorActivationError("activation can begin only from prepared")
    return ExecutorActivationState(
        intent=state.intent,
        status="activation_unknown",
        revision=1,
        previous_state_digest=state.digest,
    )


def observe_activation(
    state: ExecutorActivationState,
    observation: NativeActivationObservation,
) -> ExecutorActivationState:
    if state.status != "activation_unknown":
        raise ExecutorActivationError(
            "native observation requires activation_unknown state"
        )
    intent = state.intent
    if observation.activation_id != intent.activation_id:
        raise ExecutorActivationError("activation observation identity mismatch")
    if observation.dispatch_identity != intent.dispatch_identity:
        raise ExecutorActivationError("activation dispatch identity mismatch")
    if observation.executor != intent.executor:
        raise ExecutorActivationError("activation executor mismatch")

    common = dict(
        intent=intent,
        revision=2,
        previous_state_digest=state.digest,
        observation_digest=observation.digest,
    )
    if observation.outcome == "EXECUTOR_ACCEPTED":
        return ExecutorActivationState(
            **common,
            status="executor_accepted",
            native_execution_ref=observation.native_execution_ref,
        )
    if observation.outcome == "CONDITION_WAIT":
        return ExecutorActivationState(
            **common,
            status="condition_wait",
            condition_ref=observation.condition_ref,
        )
    return ExecutorActivationState(
        **common,
        status="failed_activation",
        failure_reason=observation.failure_reason,
    )


def activation_state_to_dict(
    state: ExecutorActivationState,
) -> dict[str, object]:
    return asdict(state)


def activation_state_from_dict(
    data: dict[str, object],
) -> ExecutorActivationState:
    if not isinstance(data, dict) or data.get("schema_version") != STATE_SCHEMA:
        raise ExecutorActivationError("unsupported activation state document")
    payload = dict(data)
    intent_data = payload.get("intent")
    if not isinstance(intent_data, dict):
        raise ExecutorActivationError("activation state requires intent")
    try:
        intent = ExecutorActivationIntent(**intent_data)
        payload["intent"] = intent
        return ExecutorActivationState(**payload)
    except (TypeError, ValueError) as exc:
        raise ExecutorActivationError("invalid activation state document") from exc


def serialize_activation_state(state: ExecutorActivationState) -> str:
    return canonical_json(activation_state_to_dict(state))


def deserialize_activation_state(value: str) -> ExecutorActivationState:
    try:
        document = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExecutorActivationError("activation state is not valid JSON") from exc
    return activation_state_from_dict(document)


class SqliteExecutorActivationStore:
    """Crash-safe activation state keyed by the ELG-01 dispatch identity."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS executor_activation (
                    dispatch_identity TEXT PRIMARY KEY,
                    activation_id TEXT NOT NULL UNIQUE,
                    state_digest TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _decode(row: tuple[object, ...]) -> ExecutorActivationState:
        dispatch_identity, activation_id, state_digest, revision, state_json = row
        state = deserialize_activation_state(str(state_json))
        if (
            state.intent.dispatch_identity != dispatch_identity
            or state.intent.activation_id != activation_id
            or state.digest != state_digest
            or state.revision != revision
        ):
            raise ExecutorActivationError(
                "durable executor activation row metadata mismatch"
            )
        return state

    def initialize(
        self,
        intent: ExecutorActivationIntent,
    ) -> ExecutorActivationState:
        state = initial_activation_state(intent)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT dispatch_identity, activation_id, state_digest, revision, state_json
                FROM executor_activation
                WHERE dispatch_identity = ?
                """,
                (intent.dispatch_identity,),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if existing.intent != intent:
                    raise ExecutorActivationError(
                        "dispatch identity already bound to another activation intent"
                    )
                connection.commit()
                return existing
            connection.execute(
                """
                INSERT INTO executor_activation(
                    dispatch_identity, activation_id, state_digest, revision, state_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    intent.dispatch_identity,
                    intent.activation_id,
                    state.digest,
                    state.revision,
                    serialize_activation_state(state),
                ),
            )
            connection.commit()
            return state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, dispatch_identity: str) -> ExecutorActivationState:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT dispatch_identity, activation_id, state_digest, revision, state_json
                FROM executor_activation
                WHERE dispatch_identity = ?
                """,
                (dispatch_identity,),
            ).fetchone()
        if row is None:
            raise ExecutorActivationError("executor activation state does not exist")
        return self._decode(row)

    def compare_and_swap(
        self,
        previous: ExecutorActivationState,
        next_state: ExecutorActivationState,
    ) -> ExecutorActivationState:
        if previous.intent != next_state.intent:
            raise ExecutorActivationError(
                "activation transition changed immutable intent"
            )
        if next_state.previous_state_digest != previous.digest:
            raise ExecutorActivationError(
                "activation transition predecessor mismatch"
            )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE executor_activation
                SET state_digest = ?, revision = ?, state_json = ?
                WHERE dispatch_identity = ? AND state_digest = ? AND revision = ?
                """,
                (
                    next_state.digest,
                    next_state.revision,
                    serialize_activation_state(next_state),
                    previous.intent.dispatch_identity,
                    previous.digest,
                    previous.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise ExecutorActivationError(
                    "executor activation compare-and-swap conflict"
                )
            connection.commit()
            return next_state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _condition_wait_observation(
    intent: ExecutorActivationIntent,
    capability: ExecutorActivationCapability,
) -> NativeActivationObservation:
    return NativeActivationObservation(
        activation_id=intent.activation_id,
        dispatch_identity=intent.dispatch_identity,
        executor=intent.executor,
        outcome="CONDITION_WAIT",
        condition_ref=f"executor://{intent.executor}/available",
        evidence_ref=capability.evidence_ref,
        evidence_digest=capability.evidence_digest,
    )


def activate_or_reconcile_executor(
    store: SqliteExecutorActivationStore,
    receipt: ExecutionLaunchReceipt,
    capability: ExecutorActivationCapability,
    adapter: ExecutorActivationAdapter,
) -> ExecutorActivationResult:
    """Drive one receipt-bound activation lineage with idempotent replay."""

    if adapter.capability != capability:
        raise ExecutorActivationError("adapter capability binding mismatch")

    intent = prepare_executor_activation(receipt, capability)
    state = store.initialize(intent)
    if state.status in {
        "executor_accepted",
        "condition_wait",
        "failed_activation",
    }:
        return ExecutorActivationResult(
            state=state,
            replay_status="ALREADY_RECORDED",
        )

    replay_status: ReplayStatus
    if state.status == "prepared":
        state = store.compare_and_swap(state, begin_activation(state))
        replay_status = "CREATED"
    elif state.status == "activation_unknown":
        replay_status = "RECOVERED"
    else:
        raise ExecutorActivationError("unsupported activation recovery state")

    if not capability.available:
        observation = _condition_wait_observation(intent, capability)
    else:
        observation = adapter.activate(intent)

    observed = observe_activation(state, observation)
    try:
        committed = store.compare_and_swap(state, observed)
    except ExecutorActivationError:
        current = store.load(intent.dispatch_identity)
        if current == observed:
            committed = current
            replay_status = "ALREADY_RECORDED"
        else:
            raise
    return ExecutorActivationResult(
        state=committed,
        replay_status=replay_status,
    )
