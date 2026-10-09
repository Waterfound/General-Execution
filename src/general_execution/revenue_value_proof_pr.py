"""Read-only, conservative projection of observed GitHub PR lifecycle evidence.

A PR's creation is NOT mission intent; merging a PR is NOT proof of customer
value, human labor saved, autonomous completion, or economic ROI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping
import re

from .revenue_value_proof import project_value_proof

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _time(value: object, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an offset-aware ISO-8601 timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include timezone")
    return parsed.astimezone(timezone.utc)


def project_github_pr_lifecycle(pr: Mapping[str, object]) -> dict[str, object]:
    """Project provider-observed PR timing without fabricating mission metrics.

    Requires a trusted PR snapshot supplied by the caller. No provider calls,
    authority, execution, or background collection are performed.
    """
    if not isinstance(pr, Mapping):
        raise ValueError("PR snapshot must be a mapping")
    allowed = {"repo_full_name", "number", "created_at", "merged_at", "merged",
               "state", "head_sha", "base_sha"}
    unknown = set(pr) - allowed
    if unknown:
        raise ValueError(f"unexpected PR fields: {sorted(unknown)}")
    repo = pr.get("repo_full_name")
    if not isinstance(repo, str) or not _REPO.fullmatch(repo):
        raise ValueError("repo_full_name must be owner/repo")
    number = pr.get("number")
    if type(number) is not int or number <= 0:
        raise ValueError("PR number must be a positive integer")
    merged = pr.get("merged")
    if type(merged) is not bool:
        raise ValueError("merged must be an observed boolean")
    state = pr.get("state")
    if state not in ("open", "closed"):
        raise ValueError("state must be open or closed")
    if merged and state != "closed":
        raise ValueError("merged PR must be closed")
    for key in ("head_sha", "base_sha"):
        value = pr.get(key)
        if value is not None and (not isinstance(value, str) or not _SHA.fullmatch(value)):
            raise ValueError(f"{key} must be a lowercase 40-character SHA or null")
    created = _time(pr.get("created_at"), "created_at")
    merged_at = _time(pr.get("merged_at"), "merged_at")
    if created is None:
        raise ValueError("created_at must be observed")
    if merged != (merged_at is not None):
        raise ValueError("merged and merged_at disagree")
    if merged_at is not None and merged_at < created:
        raise ValueError("merged_at precedes created_at")
    url = f"https://github.com/{repo}/pull/{number}"
    observation = project_value_proof({
        "workflow_id": f"github-pr:{repo}#{number}",
        "representative_workflow_class": "software-pr-lifecycle",
        "terminal_state": "PR_MERGED_ONLY" if merged else "PR_NOT_MERGED",
        "intent_timestamp": None,  # PR creation is not mission intent.
        "terminal_timestamp": merged_at.isoformat() if merged_at else None,
        "evidence_refs": [url],
    })
    return {
        "schema_version": "wrm.t1.github-pr-lifecycle.v1",
        "source": "github-pr-metadata",
        "provider_snapshot": {key: pr.get(key) for key in sorted(allowed)},
        "evidence_url": url,
        "pr_open_to_merge_seconds": (merged_at - created).total_seconds() if merged_at else None,
        "pr_open_to_merge_is_mission_latency": False,
        "value_proof": observation,
        "customer_value_proven": False,
        "authority_created": False,
        "execution_triggered": False,
    }
