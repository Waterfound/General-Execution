from datetime import datetime, timedelta, timezone

import pytest

from general_execution.portfolio_backup import (
    BackupContractError,
    BackupHealth,
    BackupPolicy,
    BackupRepositorySpec,
    ProviderScheduleBinding,
    RepositoryBackupObservation,
    assess_portfolio_backup,
    build_recovery_capsule,
)


NOW = datetime(2026, 10, 8, 3, 0, tzinfo=timezone.utc)


def spec(name="Waterfound/FAE-testnet"):
    return BackupRepositorySpec(name, f"https://github.com/{name}.git", f"gitlab://backup/{name}")


def observation(name="Waterfound/FAE-testnet", **overrides):
    values = dict(
        repository_id=name,
        source_head="a" * 40,
        mirror_head="a" * 40,
        observed_at=NOW,
        last_verified_mirror_at=NOW - timedelta(minutes=20),
        last_immutable_snapshot_at=NOW - timedelta(hours=2),
        last_clean_restore_at=NOW - timedelta(days=2),
        mirror_integrity_ok=True,
        immutable_snapshot_verified=True,
        recovery_capsule_present=True,
    )
    values.update(overrides)
    return RepositoryBackupObservation(**values)


def schedule(enabled=True, cadence=60):
    return ProviderScheduleBinding("gitlab", "schedule://portfolio-backup/hourly", cadence, enabled, "backup-control")


def test_terminal_ready_requires_all_frozen_conditions():
    result = assess_portfolio_backup([spec()], [observation()], BackupPolicy(), schedule=schedule(), now=NOW)
    assert result.health is BackupHealth.GREEN
    assert result.unattended_launch_ready is True
    assert result.terminal_ready is True


def test_no_provider_schedule_fails_even_when_mirror_itself_is_perfect():
    result = assess_portfolio_backup([spec()], [observation()], BackupPolicy(), schedule=None, now=NOW)
    assert result.health is BackupHealth.FAILED
    assert result.unattended_launch_ready is False
    assert result.terminal_ready is False


def test_stale_mirror_is_degraded_and_not_terminal():
    result = assess_portfolio_backup(
        [spec()],
        [observation(last_verified_mirror_at=NOW - timedelta(minutes=61))],
        BackupPolicy(),
        schedule=schedule(),
        now=NOW,
    )
    assert result.health is BackupHealth.DEGRADED
    assert "mirror_stale" in result.repositories[0].reasons
    assert result.terminal_ready is False


def test_mirror_head_mismatch_is_visible_and_not_silently_green():
    result = assess_portfolio_backup(
        [spec()],
        [observation(mirror_head="b" * 40)],
        BackupPolicy(),
        schedule=schedule(),
        now=NOW,
    )
    assert result.health is BackupHealth.DEGRADED
    assert "mirror_head_mismatch" in result.repositories[0].reasons


def test_unverified_immutable_snapshot_fails_closed():
    result = assess_portfolio_backup(
        [spec()],
        [observation(immutable_snapshot_verified=False)],
        BackupPolicy(),
        schedule=schedule(),
        now=NOW,
    )
    assert result.health is BackupHealth.FAILED
    assert result.terminal_ready is False


def test_missing_repository_observation_fails_portfolio():
    specs = [spec("Waterfound/Systems"), spec("Waterfound/General-Execution")]
    result = assess_portfolio_backup(specs, [observation("Waterfound/Systems")], BackupPolicy(), schedule=schedule(), now=NOW)
    assert result.health is BackupHealth.FAILED
    missing = next(item for item in result.repositories if item.repository_id == "Waterfound/General-Execution")
    assert missing.reasons == ("observation_missing",)


def test_policy_cannot_weaken_hourly_requirement():
    with pytest.raises(BackupContractError):
        BackupPolicy(mirror_max_age_minutes=61)


def test_recovery_capsule_is_machine_readable_and_secret_free():
    capsule = build_recovery_capsule([spec("Waterfound/Systems"), spec("Waterfound/FAE-testnet")], BackupPolicy(), schedule=schedule())
    assert capsule["schema"] == "waterfound.portfolio-recovery-capsule.v1"
    assert capsule["contains_credentials"] is False
    assert capsule["authority_created"] is False
    assert capsule["schedule"]["cadence_minutes"] == 60
    assert capsule["recovery_order"] == sorted(capsule["recovery_order"])
