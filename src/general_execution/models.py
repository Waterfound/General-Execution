from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest, stable_id

ExecutionMode = Literal["read_only", "bounded_write"]
ResultStatus = Literal["completed", "failed"]

VALID_EXECUTION_MODES = frozenset({"read_only", "bounded_write"})
VALID_RESULT_STATUSES = frozenset({"completed", "failed"})


def _nonempty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _unique(name: str, values: tuple[str, ...]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must not contain duplicates")


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    name: str
    uri: str
    digest: str

    def __post_init__(self) -> None:
        _nonempty("artifact.name", self.name)
        _nonempty("artifact.uri", self.uri)
        if not self.digest.startswith("sha256:") or len(self.digest) != 71:
            raise ValueError("artifact.digest must be a sha256:<64-hex> digest")
        try:
            int(self.digest[7:], 16)
        except ValueError as exc:
            raise ValueError("artifact.digest must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class ExecutionSpec:
    producer: str
    producer_revision: str
    task_kind: str
    objective: str
    source_revision: str
    required_capabilities: tuple[str, ...] = ()
    allowed_scopes: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    inputs: tuple[ArtifactRef, ...] = ()
    authority_ref: ArtifactRef | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    schema_version: str = "ge.execution-spec.v1"

    def __post_init__(self) -> None:
        for name in ("producer", "producer_revision", "task_kind", "objective", "source_revision"):
            _nonempty(name, getattr(self, name))
        for name in ("required_capabilities", "allowed_scopes", "forbidden_actions", "evidence_requirements"):
            _unique(name, getattr(self, name))
        keys = [key for key, _ in self.metadata]
        if len(keys) != len(set(keys)):
            raise ValueError("metadata keys must be unique")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def spec_id(self) -> str:
        return stable_id("ges", self)


@dataclass(frozen=True, slots=True)
class RunnerCapabilities:
    runner_id: str
    provider: str
    adapter: str
    adapter_version: str
    capabilities: tuple[str, ...]
    modes: tuple[ExecutionMode, ...] = ("read_only",)
    max_parallelism: int = 1

    def __post_init__(self) -> None:
        for name in ("runner_id", "provider", "adapter", "adapter_version"):
            _nonempty(name, getattr(self, name))
        _unique("capabilities", self.capabilities)
        _unique("modes", self.modes)
        if not self.modes or any(mode not in VALID_EXECUTION_MODES for mode in self.modes):
            raise ValueError("modes must contain only read_only or bounded_write")
        if self.max_parallelism < 1:
            raise ValueError("max_parallelism must be >= 1")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class RunnerRegistry:
    runners: tuple[RunnerCapabilities, ...]
    schema_version: str = "ge.runner-registry.v1"

    def __post_init__(self) -> None:
        ids = [runner.runner_id for runner in self.runners]
        if len(ids) != len(set(ids)):
            raise ValueError("runner ids must be unique")

    @property
    def digest(self) -> str:
        normalized = tuple(sorted(self.runners, key=lambda runner: runner.runner_id))
        return sha256_digest({"schema_version": self.schema_version, "runners": normalized})


@dataclass(frozen=True, slots=True)
class DispatchPlan:
    spec_id: str
    spec_digest: str
    registry_digest: str
    mode: ExecutionMode
    runner_id: str | None
    runner_capability_digest: str | None
    deferral_reason: Literal["no_compatible_runner"] | None
    schema_version: str = "ge.dispatch-plan.v1"

    def __post_init__(self) -> None:
        if self.mode not in VALID_EXECUTION_MODES:
            raise ValueError("mode must be read_only or bounded_write")
        if (self.runner_id is None) != (self.runner_capability_digest is None):
            raise ValueError("runner_id and runner_capability_digest must be both present or both absent")
        if self.runner_id is None and self.deferral_reason is None:
            raise ValueError("a deferred plan requires deferral_reason")
        if self.runner_id is not None and self.deferral_reason is not None:
            raise ValueError("an assigned plan cannot have deferral_reason")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def plan_id(self) -> str:
        return stable_id("gep", self)


@dataclass(frozen=True, slots=True)
class ExecutionSession:
    spec_id: str
    spec_digest: str
    plan_id: str
    plan_digest: str
    runner_id: str
    runner_capability_digest: str
    mode: ExecutionMode
    attempt: int
    state: Literal["bound", "running", "result_submitted", "revoked"] = "bound"
    result_digest: str | None = None
    schema_version: str = "ge.execution-session.v1"

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.mode not in VALID_EXECUTION_MODES:
            raise ValueError("mode must be read_only or bounded_write")
        if self.state == "result_submitted" and self.result_digest is None:
            raise ValueError("result_submitted state requires result_digest")
        if self.state != "result_submitted" and self.result_digest is not None:
            raise ValueError("only result_submitted state may carry result_digest")

    @property
    def session_id(self) -> str:
        identity = {
            "spec_digest": self.spec_digest,
            "plan_digest": self.plan_digest,
            "runner_id": self.runner_id,
            "runner_capability_digest": self.runner_capability_digest,
            "mode": self.mode,
            "attempt": self.attempt,
        }
        return stable_id("gex", identity)


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    session_id: str
    spec_id: str
    spec_digest: str
    runner_id: str
    attempt: int
    status: ResultStatus
    output_artifacts: tuple[ArtifactRef, ...] = ()
    evidence: tuple[ArtifactRef, ...] = ()
    summary: str = ""
    schema_version: str = "ge.result-envelope.v1"

    def __post_init__(self) -> None:
        for name in ("session_id", "spec_id", "spec_digest", "runner_id"):
            _nonempty(name, getattr(self, name))
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.status not in VALID_RESULT_STATUSES:
            raise ValueError("status must be completed or failed")

    @property
    def digest(self) -> str:
        return sha256_digest(self)
