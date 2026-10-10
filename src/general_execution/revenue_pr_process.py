"""Fail-closed observation of a GitHub PR process segment, not a business mission."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Mapping

from .revenue_value_proof import project_value_proof

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_ALLOWED = frozenset({
    "repository_full_name", "number", "created_at", "merged_at",
    "merged", "state", "merge_commit_sha",
})


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} requires a timestamp")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is invalid") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f"{field} requires an explicit timezone")
    return timestamp.astimezone(timezone.utc)


def observe_pr_process(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Project only provider-observed process time; all economic deltas stay unknown."""
    if not isinstance(snapshot, Mapping) or set(snapshot) - _ALLOWED:
        raise ValueError("unknown or malformed PR snapshot")
    repo, number = snapshot.get("repository_full_name"), snapshot.get("number")
    if not isinstance(repo, str) or not _REPO.fullmatch(repo):
        raise ValueError("invalid repository")
    if type(number) is not int or number < 1:
        raise ValueError("invalid PR number")
    merged, state = snapshot.get("merged"), snapshot.get("state")
    if type(merged) is not bool or state not in ("open", "closed"):
        raise ValueError("invalid observed PR state")
    if merged and state != "closed":
        raise ValueError("merged PR must be closed")
    created = _utc(snapshot.get("created_at"), "created_at")
    merged_at, sha = snapshot.get("merged_at"), snapshot.get("merge_commit_sha")
    if merged:
        if sha is None or not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise ValueError("merged PR requires observed merge commit")
        terminal = _utc(merged_at, "merged_at")
        if terminal < created:
            raise ValueError("PR merge precedes creation")
    else:
        if merged_at is not None or sha is not None:
            raise ValueError("unmerged PR cannot contain merge receipts")
        terminal = None
    pr_url = f"https://github.com/{repo}/pull/{number}"
    refs = [pr_url]
    if terminal is not None:
        refs.append(f"https://github.com/{repo}/commit/{sha}")
    projected = project_value_proof({
        "workflow_id": f"github-pr:{repo}#{number}",
        "representative_workflow_class": "github-pr-process-segment",
        "terminal_state": "PR_SEGMENT_MERGED" if merged else "PR_SEGMENT_UNMERGED",
        "intent_timestamp": None,
        "terminal_timestamp": None,
        "evidence_refs": refs,
    })
    return {
        "schema_version": "wrm.t1.github-pr-process-segment.v1",
        "authority_created": False,
        "execution_triggered": False,
        "source": "github-provider-pr-metadata",
        "provider_observation": {
            "repository_full_name": repo,
            "number": number,
            "created_at": created.isoformat(),
            "merged_at": terminal.isoformat() if terminal else None,
            "merge_commit_sha": sha,
            "evidence_refs": refs,
        },
        "observed_pr_open_to_merge_seconds": (
            (terminal - created).total_seconds() if terminal else None
        ),
        "pr_process_duration_is_mission_latency": False,
        "value_proof": projected,
        "economic_value_proven": False,
    }
