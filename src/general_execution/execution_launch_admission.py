from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from .canonical import canonical_json, sha256_digest, stable_id

ORDER_SCHEMA = "ge.execution-launch-order.v1"
AUTHORITY_SCHEMA = "ge.execution-launch-authority-binding.v1"
EXECUTOR_SCHEMA = "ge.execution-launch-executor-binding.v1"
RECEIPT_SCHEMA = "ge.execution-launch-receipt.v1"

LaunchDisposition = Literal[
    "ADMITTED",
    "HUMAN_GATE",
    "REJECTED",
    "FAILED_BEFORE_LAUNCH",
]
ExecutorAvailability = Literal["AVAILABLE", "UNAVAILABLE"]

VALID_DISPOSITIONS = {
    "ADMITTED",
    "HUMAN_GATE",
    "REJECTED",
    "FAILED_BEFORE_LAUNCH",
}
VALID_AVAILABILITY = {"AVAILABLE", "UNAVAILABLE"}
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ExecutionLaunchAdmissionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionLaunchAdmissionError(f"{name} must be a non-empty string")


def _optional_nonempty(name: str, value: str | None) -> None:
    if value is not None:
        _nonempty(name, value)


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise ExecutionLaunchAdmissionError(f"{name} must be sha256:<64-hex>")


def _unique_sorted(name: str, values: tuple[str, ...]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ExecutionLaunchAdmissionError(f"{name} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ExecutionLaunchAdmissionError(f"{name} must not contain duplicates")
    if values != tuple(sorted(values)):
        raise ExecutionLaunchAdmissionError(f"{name} must be canonical-sorted")


def _exact(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ExecutionLaunchAdmissionError(f"{label} must be an object")
    actual = set(data)
    if actual != expected:
        raise ExecutionLaunchAdmissionError(
            f"{label} fields mismatch: missing={sorted(expected-actual)} "
            f"unknown={sorted(actual-expected)}"
        )
    return data


@dataclass(frozen=True, slots=True)
class LaunchAuthorityBinding:
    actor: str
    authority_ref: str
    authority_boundary: str
    granted_scopes: tuple[str, ...]
    schema_version: str = AUTHORITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != AUTHORITY_SCHEMA:
            raise ExecutionLaunchAdmissionError("unsupported authority binding schema")
        for name in ("actor", "authority_ref", "authority_boundary"):
            _nonempty(name, getattr(self, name))
        _unique_sorted("granted_scopes", self.granted_scopes)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class LaunchExecutorBinding:
    executor: str
    availability: ExecutorAvailability
    evidence_ref: str
    evidence_digest: str
    schema_version: str = EXECUTOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != EXECUTOR_SCHEMA:
            raise ExecutionLaunchAdmissionError("unsupported executor binding schema")
        _nonempty("executor", self.executor)
        if self.availability not in VALID_AVAILABILITY:
            raise ExecutionLaunchAdmissionError("unsupported executor availability")
        _nonempty("evidence_ref", self.evidence_ref)
        _digest("evidence_digest", self.evidence_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ExecutionLaunchOrder:
    workstream_id: str
    owner: str | None
    repository: str | None
    executor: str | None
    objective: str
    order_ref: str
    source_revision: str | None
    required_authority_scopes: tuple[str, ...]
    authority: LaunchAuthorityBinding | None
    executor_binding: LaunchExecutorBinding | None
    known_first_artifact_ref: str | None = None
    schema_version: str = ORDER_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ORDER_SCHEMA:
            raise ExecutionLaunchAdmissionError("unsupported execution launch order schema")
        _nonempty("workstream_id", self.workstream_id)
        _nonempty("objective", self.objective)
        _nonempty("order_ref", self.order_ref)
        _optional_nonempty("owner", self.owner)
        _optional_nonempty("executor", self.executor)
        _optional_nonempty("source_revision", self.source_revision)
        _optional_nonempty("known_first_artifact_ref", self.known_first_artifact_ref)
        if self.repository is not None:
            _nonempty("repository", self.repository)
            if not REPOSITORY_RE.fullmatch(self.repository):
                raise ExecutionLaunchAdmissionError("repository must be owner/repository")
        _unique_sorted("required_authority_scopes", self.required_authority_scopes)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def order_id(self) -> str:
        return stable_id("gelo", self)


@dataclass(frozen=True, slots=True)
class ExecutionLaunchReceipt:
    receipt_id: str
    order_id: str
    order_digest: str
    disposition: LaunchDisposition
    disposition_reason: str
    workstream_id: str
    owner: str | None
    repository: str | None
    executor: str | None
    launch_id: str | None
    dispatch_identity: str | None
    first_artifact_ref: str | None
    authority_ref: str | None
    authority_binding_digest: str | None
    executor_binding_digest: str | None
    recovery_required: bool
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RECEIPT_SCHEMA:
            raise ExecutionLaunchAdmissionError("unsupported execution launch receipt schema")
        if self.disposition not in VALID_DISPOSITIONS:
            raise ExecutionLaunchAdmissionError("unsupported launch disposition")
        for name in ("receipt_id", "order_id", "disposition_reason", "workstream_id"):
            _nonempty(name, getattr(self, name))
        _digest("order_digest", self.order_digest)
        for name in ("authority_binding_digest", "executor_binding_digest"):
            value = getattr(self, name)
            if value is not None:
                _digest(name, value)
        if self.authority_created or self.execution_triggered:
            raise ExecutionLaunchAdmissionError(
                "launch receipt cannot create authority or trigger execution"
            )
        if self.disposition == "ADMITTED":
            if not self.launch_id or not self.dispatch_identity:
                raise ExecutionLaunchAdmissionError(
                    "ADMITTED receipt requires launch and dispatch identity"
                )
            if self.owner is None or self.repository is None or self.executor is None:
                raise ExecutionLaunchAdmissionError(
                    "ADMITTED receipt requires complete ownership binding"
                )
        elif self.launch_id is not None or self.dispatch_identity is not None:
            raise ExecutionLaunchAdmissionError(
                "non-ADMITTED receipt cannot claim launch or dispatch identity"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class LaunchAdmissionResult:
    receipt: ExecutionLaunchReceipt
    replay_status: Literal["CREATED", "ALREADY_RECORDED"]


def authority_binding_from_dict(data: Any) -> LaunchAuthorityBinding | None:
    if data is None:
        return None
    obj = _exact(
        data,
        {"actor", "authority_ref", "authority_boundary", "granted_scopes", "schema_version"},
        "launch authority binding",
    )
    if not isinstance(obj["granted_scopes"], list):
        raise ExecutionLaunchAdmissionError("granted_scopes must be a list")
    return LaunchAuthorityBinding(
        actor=obj["actor"],
        authority_ref=obj["authority_ref"],
        authority_boundary=obj["authority_boundary"],
        granted_scopes=tuple(obj["granted_scopes"]),
        schema_version=obj["schema_version"],
    )


def executor_binding_from_dict(data: Any) -> LaunchExecutorBinding | None:
    if data is None:
        return None
    obj = _exact(
        data,
        {"executor", "availability", "evidence_ref", "evidence_digest", "schema_version"},
        "launch executor binding",
    )
    return LaunchExecutorBinding(**obj)


def execution_launch_order_from_dict(data: Any) -> ExecutionLaunchOrder:
    obj = _exact(
        data,
        {
            "workstream_id",
            "owner",
            "repository",
            "executor",
            "objective",
            "order_ref",
            "source_revision",
            "required_authority_scopes",
            "authority",
            "executor_binding",
            "known_first_artifact_ref",
            "schema_version",
        },
        "execution launch order",
    )
    if not isinstance(obj["required_authority_scopes"], list):
        raise ExecutionLaunchAdmissionError("required_authority_scopes must be a list")
    return ExecutionLaunchOrder(
        workstream_id=obj["workstream_id"],
        owner=obj["owner"],
        repository=obj["repository"],
        executor=obj["executor"],
        objective=obj["objective"],
        order_ref=obj["order_ref"],
        source_revision=obj["source_revision"],
        required_authority_scopes=tuple(obj["required_authority_scopes"]),
        authority=authority_binding_from_dict(obj["authority"]),
        executor_binding=executor_binding_from_dict(obj["executor_binding"]),
        known_first_artifact_ref=obj["known_first_artifact_ref"],
        schema_version=obj["schema_version"],
    )


def execution_launch_receipt_from_dict(data: Any) -> ExecutionLaunchReceipt:
    obj = _exact(
        data,
        {
            "receipt_id",
            "order_id",
            "order_digest",
            "disposition",
            "disposition_reason",
            "workstream_id",
            "owner",
            "repository",
            "executor",
            "launch_id",
            "dispatch_identity",
            "first_artifact_ref",
            "authority_ref",
            "authority_binding_digest",
            "executor_binding_digest",
            "recovery_required",
            "authority_created",
            "execution_triggered",
            "schema_version",
        },
        "execution launch receipt",
    )
    return ExecutionLaunchReceipt(**obj)


def launch_order_to_dict(order: ExecutionLaunchOrder) -> dict[str, Any]:
    return json.loads(canonical_json(order))


def launch_receipt_to_dict(receipt: ExecutionLaunchReceipt) -> dict[str, Any]:
    return json.loads(canonical_json(receipt))


def _receipt(
    order: ExecutionLaunchOrder,
    disposition: LaunchDisposition,
    reason: str,
) -> ExecutionLaunchReceipt:
    launch_id = None
    dispatch_identity = None
    recovery_required = False
    if disposition == "ADMITTED":
        seed = {
            "order_digest": order.digest,
            "workstream_id": order.workstream_id,
            "owner": order.owner,
            "repository": order.repository,
            "executor": order.executor,
        }
        launch_id = stable_id("gel", seed)
        dispatch_identity = stable_id(
            "geld",
            {
                "launch_id": launch_id,
                "executor": order.executor,
                "repository": order.repository,
            },
        )
        recovery_required = order.known_first_artifact_ref is None

    identity = {
        "order_digest": order.digest,
        "disposition": disposition,
        "reason": reason,
        "launch_id": launch_id,
        "dispatch_identity": dispatch_identity,
    }
    return ExecutionLaunchReceipt(
        receipt_id=stable_id("gelr", identity),
        order_id=order.order_id,
        order_digest=order.digest,
        disposition=disposition,
        disposition_reason=reason,
        workstream_id=order.workstream_id,
        owner=order.owner,
        repository=order.repository,
        executor=order.executor,
        launch_id=launch_id,
        dispatch_identity=dispatch_identity,
        first_artifact_ref=order.known_first_artifact_ref,
        authority_ref=order.authority.authority_ref if order.authority else None,
        authority_binding_digest=order.authority.digest if order.authority else None,
        executor_binding_digest=(
            order.executor_binding.digest if order.executor_binding else None
        ),
        recovery_required=recovery_required,
    )


def admit_execution_launch_order(
    order: ExecutionLaunchOrder,
    *,
    authenticated_order_digest: str,
    authenticated_actor: str,
) -> ExecutionLaunchReceipt:
    _digest("authenticated_order_digest", authenticated_order_digest)
    _nonempty("authenticated_actor", authenticated_actor)
    if authenticated_order_digest != order.digest:
        raise ExecutionLaunchAdmissionError("authenticated execution order digest mismatch")

    if order.owner is None:
        return _receipt(order, "REJECTED", "owner_binding_missing")
    if order.repository is None:
        return _receipt(order, "REJECTED", "repository_binding_missing")
    if order.executor is None:
        return _receipt(order, "REJECTED", "executor_binding_missing")

    authority = order.authority
    if order.required_authority_scopes:
        if authority is None:
            return _receipt(order, "HUMAN_GATE", "authority_binding_missing")
        if authority.actor != authenticated_actor:
            return _receipt(order, "REJECTED", "authority_actor_mismatch")
        missing = sorted(
            set(order.required_authority_scopes) - set(authority.granted_scopes)
        )
        if missing:
            return _receipt(
                order,
                "HUMAN_GATE",
                "authority_scope_missing:" + ",".join(missing),
            )

    executor = order.executor_binding
    if executor is None:
        return _receipt(order, "FAILED_BEFORE_LAUNCH", "executor_evidence_missing")
    if executor.executor != order.executor:
        return _receipt(order, "REJECTED", "executor_identity_mismatch")
    if executor.availability == "UNAVAILABLE":
        return _receipt(order, "FAILED_BEFORE_LAUNCH", "executor_unavailable")

    return _receipt(order, "ADMITTED", "launch_admitted")


def admit_or_replay_execution_launch(
    order: ExecutionLaunchOrder,
    *,
    authenticated_order_digest: str,
    authenticated_actor: str,
    existing_receipt: ExecutionLaunchReceipt | None = None,
) -> LaunchAdmissionResult:
    if existing_receipt is not None:
        if existing_receipt.workstream_id != order.workstream_id:
            raise ExecutionLaunchAdmissionError(
                "existing launch receipt belongs to another workstream"
            )
        if existing_receipt.order_digest != order.digest:
            raise ExecutionLaunchAdmissionError(
                "workstream already has a different execution launch order"
            )
        expected = admit_execution_launch_order(
            order,
            authenticated_order_digest=authenticated_order_digest,
            authenticated_actor=authenticated_actor,
        )
        if existing_receipt != expected:
            raise ExecutionLaunchAdmissionError(
                "existing launch receipt does not reproduce deterministically"
            )
        return LaunchAdmissionResult(existing_receipt, "ALREADY_RECORDED")

    receipt = admit_execution_launch_order(
        order,
        authenticated_order_digest=authenticated_order_digest,
        authenticated_actor=authenticated_actor,
    )
    return LaunchAdmissionResult(receipt, "CREATED")
