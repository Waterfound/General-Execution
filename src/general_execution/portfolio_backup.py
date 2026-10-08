"""Provider-neutral contracts for unattended portfolio backup readiness.

This module does not perform network or provider mutations. It evaluates whether
an externally configured backup system satisfies the frozen Waterfound portfolio
preservation contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


class BackupContractError(ValueError):
    pass


class BackupHealth(str, Enum):
    GREEN = "GREEN"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BackupRepositorySpec:
    repository_id: str
    source_url: str
    destination_id: str
    critical: bool = True


@dataclass(frozen=True)
class BackupPolicy:
    mirror_max_age_minutes: int = 60
    snapshot_max_age_hours: int = 24
    restore_rehearsal_max_age_days: int = 7

    def __post_init__(self) -> None:
        if not 1 <= self.mirror_max_age_minutes <= 60:
            raise BackupContractError("mirror_max_age_minutes must be in 1..60")
        if not 1 <= self.snapshot_max_age_hours <= 24:
            raise BackupContractError("snapshot_max_age_hours must be in 1..24")
        if not 1 <= self.restore_rehearsal_max_age_days <= 7:
            raise BackupContractError("restore_rehearsal_max_age_days must be in 1..7")


@dataclass(frozen=True)
class ProviderScheduleBinding:
    provider: str
    schedule_ref: str
    cadence_minutes: int
    enabled: bool
    control_ref: str

    def __post_init__(self) -> None:
        if not self.provider or not self.schedule_ref or not self.control_ref:
            raise BackupContractError("schedule binding requires provider, schedule_ref and control_ref")
        if not 1 <= self.cadence_minutes <= 60:
            raise BackupContractError("backup schedule cadence must be <= 60 minutes")


@dataclass(frozen=True)
class RepositoryBackupObservation:
    repository_id: str
    source_head: str
    mirror_head: str
    observed_at: datetime
    last_verified_mirror_at: datetime
    last_immutable_snapshot_at: datetime
    last_clean_restore_at: datetime
    mirror_integrity_ok: bool
    immutable_snapshot_verified: bool
    recovery_capsule_present: bool

    def __post_init__(self) -> None:
        for name in ("observed_at", "last_verified_mirror_at", "last_immutable_snapshot_at", "last_clean_restore_at"):
            value = getattr(self, name)
            if value.tzinfo is None:
                raise BackupContractError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class RepositoryBackupAssessment:
    repository_id: str
    health: BackupHealth
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioBackupAssessment:
    health: BackupHealth
    repositories: tuple[RepositoryBackupAssessment, ...]
    unattended_launch_ready: bool
    terminal_ready: bool


def _age_seconds(now: datetime, then: datetime) -> float:
    if now.tzinfo is None:
        raise BackupContractError("now must be timezone-aware")
    return (now - then).total_seconds()


def assess_repository_backup(
    spec: BackupRepositorySpec,
    observation: RepositoryBackupObservation,
    policy: BackupPolicy,
    *,
    now: datetime,
) -> RepositoryBackupAssessment:
    if spec.repository_id != observation.repository_id:
        raise BackupContractError("repository observation identity mismatch")

    reasons: list[str] = []
    if observation.source_head != observation.mirror_head:
        reasons.append("mirror_head_mismatch")
    if not observation.mirror_integrity_ok:
        reasons.append("mirror_integrity_failed")
    if _age_seconds(now, observation.last_verified_mirror_at) > policy.mirror_max_age_minutes * 60:
        reasons.append("mirror_stale")
    if _age_seconds(now, observation.last_immutable_snapshot_at) > policy.snapshot_max_age_hours * 3600:
        reasons.append("immutable_snapshot_stale")
    if not observation.immutable_snapshot_verified:
        reasons.append("immutable_snapshot_unverified")
    if _age_seconds(now, observation.last_clean_restore_at) > policy.restore_rehearsal_max_age_days * 86400:
        reasons.append("clean_restore_stale")
    if not observation.recovery_capsule_present:
        reasons.append("recovery_capsule_missing")

    hard = {"mirror_integrity_failed", "immutable_snapshot_unverified", "recovery_capsule_missing"}
    if any(reason in hard for reason in reasons):
        health = BackupHealth.FAILED
    elif reasons:
        health = BackupHealth.DEGRADED
    else:
        health = BackupHealth.GREEN
    return RepositoryBackupAssessment(spec.repository_id, health, tuple(reasons))


def assess_portfolio_backup(
    specs: Iterable[BackupRepositorySpec],
    observations: Iterable[RepositoryBackupObservation],
    policy: BackupPolicy,
    *,
    schedule: ProviderScheduleBinding | None,
    now: datetime,
) -> PortfolioBackupAssessment:
    spec_list = tuple(specs)
    obs_by_id = {item.repository_id: item for item in observations}
    results: list[RepositoryBackupAssessment] = []

    for spec in spec_list:
        observation = obs_by_id.get(spec.repository_id)
        if observation is None:
            results.append(
                RepositoryBackupAssessment(spec.repository_id, BackupHealth.FAILED, ("observation_missing",))
            )
            continue
        results.append(assess_repository_backup(spec, observation, policy, now=now))

    unattended = bool(schedule and schedule.enabled and schedule.cadence_minutes <= policy.mirror_max_age_minutes)
    if not unattended:
        health = BackupHealth.FAILED
    elif any(item.health is BackupHealth.FAILED for item in results):
        health = BackupHealth.FAILED
    elif any(item.health is BackupHealth.DEGRADED for item in results):
        health = BackupHealth.DEGRADED
    else:
        health = BackupHealth.GREEN

    terminal_ready = health is BackupHealth.GREEN and unattended
    return PortfolioBackupAssessment(health, tuple(results), unattended, terminal_ready)


def manifest_digest(specs: Iterable[BackupRepositorySpec], policy: BackupPolicy) -> str:
    payload = {
        "policy": {
            "mirror_max_age_minutes": policy.mirror_max_age_minutes,
            "snapshot_max_age_hours": policy.snapshot_max_age_hours,
            "restore_rehearsal_max_age_days": policy.restore_rehearsal_max_age_days,
        },
        "repositories": [
            {
                "repository_id": item.repository_id,
                "source_url": item.source_url,
                "destination_id": item.destination_id,
                "critical": item.critical,
            }
            for item in sorted(specs, key=lambda x: x.repository_id)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def build_recovery_capsule(
    specs: Iterable[BackupRepositorySpec],
    policy: BackupPolicy,
    *,
    schedule: ProviderScheduleBinding,
) -> dict:
    spec_list = tuple(specs)
    return {
        "schema": "waterfound.portfolio-recovery-capsule.v1",
        "manifest_digest": manifest_digest(spec_list, policy),
        "authority_created": False,
        "contains_credentials": False,
        "recovery_order": [item.repository_id for item in sorted(spec_list, key=lambda x: x.repository_id)],
        "instructions": [
            "Select the newest immutable snapshot whose digest and manifest both verify.",
            "Restore each repository into a clean destination without overwriting the only surviving copy.",
            "Verify all refs plus canonical HEAD/tree against the snapshot manifest.",
            "Run repository-native verification before declaring the restored repository usable.",
            "Recreate provider schedules from provider bindings; do not infer credentials or authority.",
        ],
        "schedule": {
            "provider": schedule.provider,
            "schedule_ref": schedule.schedule_ref,
            "cadence_minutes": schedule.cadence_minutes,
            "control_ref": schedule.control_ref,
        },
    }
