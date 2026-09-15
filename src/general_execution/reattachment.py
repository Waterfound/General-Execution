from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .canonical import sha256_digest, stable_id
from .durable import DurableCapacitySnapshot, RecoveredInFlightLease, recover_after_restart, verify_durable_snapshot
from .models import ExecutionSession, RunnerCapabilities
from .physical import (
    PhysicalAttemptAuthorization,
    PhysicalObservation,
    PhysicalOutcomeBundle,
    admit_physical_observation,
)

PROVIDER_REATTACHMENT_CAPABILITY = "provider.reattachment.v1"
ReattachmentStatus = Literal["running", "not_found", "terminal"]
ReattachmentDisposition = Literal["keep_running", "remain_unknown", "terminal_outcome"]
VALID_REATTACHMENT_STATUSES = frozenset({"running", "not_found", "terminal"})
VALID_REATTACHMENT_DISPOSITIONS = frozenset({"keep_running", "remain_unknown", "terminal_outcome"})


class ReattachmentError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


def _require_reattachment_capability(runner: RunnerCapabilities) -> None:
    if PROVIDER_REATTACHMENT_CAPABILITY not in runner.capabilities:
        raise ReattachmentError("runner does not advertise provider reattachment capability")


@dataclass(frozen=True, slots=True)
class ProviderReattachmentKey:
    runner_id: str
    runner_capability_digest: str
    provider: str
    adapter: str
    adapter_version: str
    session_id: str
    logical_attempt: int
    authorization_id: str
    authorization_digest: str
    invocation_id: str
    physical_attempt: int
    schema_version: str = "ge.provider-reattachment-key.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.provider-reattachment-key.v1":
            raise ValueError("unsupported provider reattachment key schema")
        for name in (
            "runner_id",
            "runner_capability_digest",
            "provider",
            "adapter",
            "adapter_version",
            "session_id",
            "authorization_id",
            "authorization_digest",
            "invocation_id",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.logical_attempt < 1 or self.physical_attempt < 1:
            raise ValueError("attempt ordinals must be >= 1")
        _require_sha256("runner_capability_digest", self.runner_capability_digest)
        _require_sha256("authorization_digest", self.authorization_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def key_id(self) -> str:
        return stable_id("gerk", self)

    @property
    def provider_key(self) -> str:
        return self.key_id


@dataclass(frozen=True, slots=True)
class ProviderStatusProbe:
    source_head_digest: str
    source_snapshot_digest: str
    recovered_lease: RecoveredInFlightLease
    reattachment_key: ProviderReattachmentKey
    schema_version: str = "ge.provider-status-probe.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.provider-status-probe.v1":
            raise ValueError("unsupported provider status probe schema")
        _require_sha256("source_head_digest", self.source_head_digest)
        _require_sha256("source_snapshot_digest", self.source_snapshot_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def probe_id(self) -> str:
        return stable_id("gerp", self)


@dataclass(frozen=True, slots=True)
class ProviderStatusObservation:
    probe_digest: str
    reattachment_key_digest: str
    provider_key: str
    status: ReattachmentStatus
    provider_invocation_id: str | None = None
    physical_observation: PhysicalObservation | None = None
    detail_digest: str | None = None
    schema_version: str = "ge.provider-status-observation.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.provider-status-observation.v1":
            raise ValueError("unsupported provider status observation schema")
        if self.status not in VALID_REATTACHMENT_STATUSES:
            raise ValueError("unsupported provider reattachment status")
        _require_sha256("probe_digest", self.probe_digest)
        _require_sha256("reattachment_key_digest", self.reattachment_key_digest)
        if not self.provider_key or not self.provider_key.strip():
            raise ValueError("provider_key must be non-empty")
        if self.detail_digest is not None:
            _require_sha256("detail_digest", self.detail_digest)
        if self.status == "terminal":
            if self.physical_observation is None:
                raise ValueError("terminal provider status requires physical_observation")
        elif self.physical_observation is not None:
            raise ValueError("non-terminal provider status cannot carry physical_observation")
        if self.status == "not_found" and self.provider_invocation_id is not None:
            raise ValueError("not_found provider status cannot carry provider_invocation_id")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProviderReattachmentAssessment:
    probe_digest: str
    observation_digest: str
    disposition: ReattachmentDisposition
    provider_invocation_id: str | None = None
    outcome_digest: str | None = None
    schema_version: str = "ge.provider-reattachment-assessment.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.provider-reattachment-assessment.v1":
            raise ValueError("unsupported provider reattachment assessment schema")
        if self.disposition not in VALID_REATTACHMENT_DISPOSITIONS:
            raise ValueError("unsupported provider reattachment disposition")
        _require_sha256("probe_digest", self.probe_digest)
        _require_sha256("observation_digest", self.observation_digest)
        if self.disposition == "terminal_outcome":
            if self.outcome_digest is None:
                raise ValueError("terminal_outcome disposition requires outcome_digest")
            _require_sha256("outcome_digest", self.outcome_digest)
        elif self.outcome_digest is not None:
            raise ValueError("non-terminal disposition cannot carry outcome_digest")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def reattachment_key_from_authorization(
    authorization: PhysicalAttemptAuthorization,
    runner: RunnerCapabilities,
) -> ProviderReattachmentKey:
    _require_reattachment_capability(runner)
    request = authorization.request
    if request.runner_id != runner.runner_id or request.runner_capability_digest != runner.digest:
        raise ReattachmentError("physical authorization is not bound to this runner")
    return ProviderReattachmentKey(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        provider=runner.provider,
        adapter=runner.adapter,
        adapter_version=runner.adapter_version,
        session_id=request.session_id,
        logical_attempt=request.attempt,
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.digest,
        invocation_id=request.invocation_id,
        physical_attempt=authorization.physical_attempt,
    )


def reattachment_key_from_recovered(
    recovered: RecoveredInFlightLease,
    runner: RunnerCapabilities,
) -> ProviderReattachmentKey:
    _require_reattachment_capability(runner)
    return ProviderReattachmentKey(
        runner_id=runner.runner_id,
        runner_capability_digest=runner.digest,
        provider=runner.provider,
        adapter=runner.adapter,
        adapter_version=runner.adapter_version,
        session_id=recovered.session_id,
        logical_attempt=recovered.logical_attempt,
        authorization_id=recovered.authorization_id,
        authorization_digest=recovered.authorization_digest,
        invocation_id=recovered.invocation_id,
        physical_attempt=recovered.physical_attempt,
    )


def verify_reattachment_key(
    authorization: PhysicalAttemptAuthorization,
    recovered: RecoveredInFlightLease,
    runner: RunnerCapabilities,
) -> bool:
    try:
        return reattachment_key_from_authorization(authorization, runner) == reattachment_key_from_recovered(
            recovered, runner
        )
    except ReattachmentError:
        return False


def build_status_probe(
    source: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    recovered: RecoveredInFlightLease,
) -> ProviderStatusProbe:
    _require_reattachment_capability(runner)
    if not verify_durable_snapshot(source, runner):
        raise ReattachmentError("source durable snapshot is invalid")
    _, report = recover_after_restart(source, runner)
    if recovered not in report.active_leases:
        raise ReattachmentError("recovered lease is not active in source durable head")
    return ProviderStatusProbe(
        source_head_digest=source.head.digest,
        source_snapshot_digest=source.digest,
        recovered_lease=recovered,
        reattachment_key=reattachment_key_from_recovered(recovered, runner),
    )


def verify_status_probe(
    source: DurableCapacitySnapshot,
    runner: RunnerCapabilities,
    probe: ProviderStatusProbe,
) -> bool:
    try:
        expected = build_status_probe(source, runner, probe.recovered_lease)
    except ReattachmentError:
        return False
    return probe == expected


def observe_provider_running(
    probe: ProviderStatusProbe,
    *,
    provider_invocation_id: str | None = None,
    detail_digest: str | None = None,
) -> ProviderStatusObservation:
    return ProviderStatusObservation(
        probe_digest=probe.digest,
        reattachment_key_digest=probe.reattachment_key.digest,
        provider_key=probe.reattachment_key.provider_key,
        status="running",
        provider_invocation_id=provider_invocation_id,
        detail_digest=detail_digest,
    )


def observe_provider_not_found(
    probe: ProviderStatusProbe,
    *,
    detail_digest: str | None = None,
) -> ProviderStatusObservation:
    return ProviderStatusObservation(
        probe_digest=probe.digest,
        reattachment_key_digest=probe.reattachment_key.digest,
        provider_key=probe.reattachment_key.provider_key,
        status="not_found",
        detail_digest=detail_digest,
    )


def observe_provider_terminal(
    probe: ProviderStatusProbe,
    physical_observation: PhysicalObservation,
    *,
    detail_digest: str | None = None,
) -> ProviderStatusObservation:
    return ProviderStatusObservation(
        probe_digest=probe.digest,
        reattachment_key_digest=probe.reattachment_key.digest,
        provider_key=probe.reattachment_key.provider_key,
        status="terminal",
        provider_invocation_id=physical_observation.provider_invocation_id,
        physical_observation=physical_observation,
        detail_digest=detail_digest,
    )


def verify_status_observation(
    probe: ProviderStatusProbe,
    observation: ProviderStatusObservation,
) -> bool:
    if (
        observation.probe_digest != probe.digest
        or observation.reattachment_key_digest != probe.reattachment_key.digest
        or observation.provider_key != probe.reattachment_key.provider_key
    ):
        return False
    physical = observation.physical_observation
    if observation.status == "terminal":
        if physical is None:
            return False
        if (
            physical.authorization_id != probe.recovered_lease.authorization_id
            or physical.invocation_id != probe.recovered_lease.invocation_id
        ):
            return False
        if observation.provider_invocation_id != physical.provider_invocation_id:
            return False
        return True
    if physical is not None:
        return False
    if observation.status == "not_found" and observation.provider_invocation_id is not None:
        return False
    return observation.status in {"running", "not_found"}


def assess_provider_status(
    source: DurableCapacitySnapshot,
    spec,
    registry,
    execution_plan,
    session: ExecutionSession,
    runner: RunnerCapabilities,
    authorization: PhysicalAttemptAuthorization,
    probe: ProviderStatusProbe,
    observation: ProviderStatusObservation,
) -> tuple[ProviderReattachmentAssessment, PhysicalOutcomeBundle | None]:
    if not verify_status_probe(source, runner, probe):
        raise ReattachmentError("provider status probe does not reproduce from recovery state")
    if not verify_reattachment_key(authorization, probe.recovered_lease, runner):
        raise ReattachmentError("physical authorization does not reproduce recovered reattachment key")
    if not verify_status_observation(probe, observation):
        raise ReattachmentError("provider status observation is not bound to the exact probe")

    if observation.status == "running":
        return (
            ProviderReattachmentAssessment(
                probe_digest=probe.digest,
                observation_digest=observation.digest,
                disposition="keep_running",
                provider_invocation_id=observation.provider_invocation_id,
            ),
            None,
        )
    if observation.status == "not_found":
        return (
            ProviderReattachmentAssessment(
                probe_digest=probe.digest,
                observation_digest=observation.digest,
                disposition="remain_unknown",
            ),
            None,
        )

    physical = observation.physical_observation
    assert physical is not None
    try:
        outcome = admit_physical_observation(
            spec,
            registry,
            execution_plan,
            session,
            runner,
            authorization,
            physical,
        )
    except ValueError as exc:
        raise ReattachmentError("terminal provider observation failed physical-outcome admission") from exc
    assessment = ProviderReattachmentAssessment(
        probe_digest=probe.digest,
        observation_digest=observation.digest,
        disposition="terminal_outcome",
        provider_invocation_id=physical.provider_invocation_id,
        outcome_digest=outcome.digest,
    )
    return assessment, outcome
