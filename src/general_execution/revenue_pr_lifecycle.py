"""Read-only PR lifecycle projection for WRM-T1 natural evidence.

A pull request is a *process segment*, not necessarily a complete mission.
PR created_at MUST NOT be promoted to mission intent_timestamp; PR merged_at
MUST NOT be promoted to verified mission completion or customer value.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Mapping


_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_FIELDS = {
    "repository_full_name", "number", "html_url", "created_at",
    "merged_at", "merged", "merge_commit_sha",
}


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def project_pr_lifecycle(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Project an independently verifiable PR segment, never an ROI estimate."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("snapshot must be a mapping")
    unknown = set(snapshot) - _FIELDS
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    repo = snapshot.get("repository_full_name")
    number = snapshot.get("number")
    if not isinstance(repo, str) or not _REPO.fullmatch(repo):
        raise ValueError("invalid repository_full_name")
    if type(number) is not int or number < 1:
        raise ValueError("number must be a positive integer")
    url = f"https://github.com/{repo}/pull/{number}"
    if snapshot.get("html_url") != url:
        raise ValueError("PR URL must match repository and number")
    merged = snapshot.get("merged")
    if type(merged) is not bool:
        raise ValueError("merged must be boolean")
    created = _utc(snapshot.get("created_at"), "created_at")
    merged_at = snapshot.get("merged_at")
    merge_sha = snapshot.get("merge_commit_sha")
    if merged:
        if merged_at is None or not isinstance(merge_sha, str) or not _SHA.fullmatch(merge_sha):
            raise ValueError("merged PR requires merged_at and merge commit SHA")
        terminal = _utc(merged_at, "merged_at")
        if terminal < created:
            raise ValueError("merged_at precedes created_at")
        elapsed = (terminal - created).total_seconds()
    else:
        if merged_at is not None or merge_sha is not None:
            raise ValueError("unmerged PR cannot have merge evidence")
        terminal = None
        elapsed = None
    refs = [url]
    if merged:
        refs.append(f"https://github.com/{repo}/commit/{merge_sha}")
    return {
        "schema_version": "wrm.t1.github-pr-lifecycle.v1",
        "authority_created": False,
        "execution_triggered": False,
        "segment_kind": "github_pull_request_lifecycle",
        "source": {
            "repository_full_name": repo,
            "number": number,
            "created_at": created.isoformat(),
            "merged_at": terminal.isoformat() if terminal else None,
            "merge_commit_sha": merge_sha,
            "evidence_refs": refs,
        },
        "derived": {
            "observed_pr_created_to_merge_seconds": elapsed,
            "mission_intent_timestamp": None,
            "verified_mission_terminal_timestamp": None,
            "mission_completion_latency_seconds": None,
            "human_active_minutes": None,
            "approvals_eliminated": None,
            "operator_hours_saved": None,
            "matched_latency_reduction_seconds": None,
            "coordination_tax_removed": None,
            "rework_avoided": None,
            "recovery_improvement": None,
            "autonomous_resolution_rate": None,
            "audit_coverage": None,
            "roi": None,
            "willingness_to_pay": None,
        },
        "evidence_level": "OBSERVED_PR_SEGMENT_NOT_MISSION_OR_ECONOMIC_VALUE",
    }
