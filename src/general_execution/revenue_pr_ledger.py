"""Evidence-first, read-only PR recovery and approval ledger.

No GitHub access, authority delegation, financial claims or mutating operations.
The caller must provide a verifiable snapshot of PR, check and policy receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Mapping
from urllib.parse import urlparse

_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_GOOD = {"success"}
_BAD = {"failure", "timed_out", "cancelled", "action_required", "neutral", "skipped", "stale"}
_PENDING = {"queued", "in_progress", "pending", "requested", "waiting"}
_VALUE_UNKNOWN = (
    "operator_hours_saved", "coordination_tax_removed", "matched_latency_reduction_seconds",
    "recovery_improvement", "avoidable_rework_reduced", "control_plane_leverage",
    "customer_roi", "willingness_to_pay", "revenue",
)


def _obj(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _keys(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown {label} fields: {sorted(unknown)}")


def _url(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an HTTPS URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{label} must be an HTTPS URL")
    return value


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(f"{label} must be a full commit SHA")
    return value.lower()


def _int(value: object, label: str, *, allow_zero: bool = True) -> int:
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("observed_at must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must have an explicit timezone")


def project_pr_ledger(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Project one supplied snapshot; missing policies are UNKNOWN, never zero."""
    data = _obj(snapshot, "snapshot")
    _keys(data, {"schema_version", "observed_at", "pr", "requirements", "checks", "reviews", "threads"}, "snapshot")
    if data.get("schema_version") != "wrm.pr-ledger-input.v1":
        raise ValueError("unsupported snapshot schema")
    _timestamp(data.get("observed_at"))
    pr = _obj(data.get("pr"), "pr")
    _keys(pr, {"number", "url", "head_sha", "state", "merged", "draft", "merge_commit_sha"}, "pr")
    number = _int(pr.get("number"), "pr.number", allow_zero=False)
    pr_url = _url(pr.get("url"), "pr.url")
    head = _sha(pr.get("head_sha"), "pr.head_sha")
    if pr.get("state") not in {"open", "closed"}:
        raise ValueError("pr.state must be open or closed")
    if type(pr.get("merged")) is not bool or type(pr.get("draft")) is not bool:
        raise ValueError("pr.merged and pr.draft must be booleans")
    if pr["merged"] and pr["state"] != "closed":
        raise ValueError("merged PR cannot be open")
    merge_sha = None
    if pr.get("merge_commit_sha") is not None:
        merge_sha = _sha(pr["merge_commit_sha"], "pr.merge_commit_sha")
    if not pr["merged"] and merge_sha is not None:
        raise ValueError("unmerged PR cannot claim a merge commit")

    requirements = data.get("requirements")
    required_checks = required_approvals = require_conversations_resolved = None
    rule_url = None
    if requirements is not None:
        rule = _obj(requirements, "requirements")
        _keys(rule, {"source_ref", "required_checks", "required_approvals", "require_conversations_resolved"}, "requirements")
        rule_url = _url(rule.get("source_ref"), "requirements.source_ref")
        if rule.get("require_conversations_resolved") is not None:
            if type(rule["require_conversations_resolved"]) is not bool:
                raise ValueError("require_conversations_resolved must be boolean or null")
            require_conversations_resolved = rule["require_conversations_resolved"]
        if rule.get("required_checks") is not None:
            names = rule["required_checks"]
            if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
                raise ValueError("required_checks must be a list of nonempty names or null")
            if len(set(names)) != len(names):
                raise ValueError("duplicate required check names")
            required_checks = names
        if rule.get("required_approvals") is not None:
            required_approvals = _int(rule["required_approvals"], "required_approvals")

    checks = data.get("checks")
    reviews = data.get("reviews")
    threads = data.get("threads")
    if checks is not None and not isinstance(checks, list):
        raise ValueError("checks must be an array or null")
    if reviews is not None and not isinstance(reviews, list):
        raise ValueError("reviews must be an array or null")
    if threads is not None and not isinstance(threads, list):
        raise ValueError("threads must be an array or null")
    check_by_name = {}
    check_refs = []
    for raw in checks or []:
        item = _obj(raw, "check")
        _keys(item, {"name", "head_sha", "status", "conclusion", "url"}, "check")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or name in check_by_name:
            raise ValueError("check names must be unique and nonempty")
        if _sha(item.get("head_sha"), "check.head_sha") != head:
            raise ValueError("check belongs to a different PR head")
        status = item.get("status")
        conclusion = item.get("conclusion")
        if status not in {"queued", "in_progress", "completed", "pending", "requested", "waiting"}:
            raise ValueError("unsupported check status")
        if status == "completed" and conclusion not in _GOOD | _BAD:
            raise ValueError("completed check needs an explicit conclusion")
        if status != "completed" and conclusion is not None:
            raise ValueError("non-completed check cannot have conclusion")
        check_by_name[name] = item
        check_refs.append(_url(item.get("url"), "check.url"))

    approval_by_user = {}
    review_refs = []
    for raw in reviews or []:
        item = _obj(raw, "review")
        _keys(item, {"user", "state", "commit_sha", "url"}, "review")
        user = item.get("user")
        if not isinstance(user, str) or not user.strip() or user in approval_by_user:
            raise ValueError("reviews must have unique nonempty users; collapse review history first")
        if item.get("state") not in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED"}:
            raise ValueError("unsupported review state")
        commit = _sha(item.get("commit_sha"), "review.commit_sha")
        approval_by_user[user] = item["state"] == "APPROVED" and commit == head
        review_refs.append(_url(item.get("url"), "review.url"))

    seen_thread_ids = set()
    unresolved_threads = 0 if threads is not None else None
    for raw in threads or []:
        item = _obj(raw, "thread")
        _keys(item, {"id", "url", "is_resolved", "head_sha"}, "thread")
        thread_id = item.get("id")
        if not isinstance(thread_id, str) or not thread_id or thread_id in seen_thread_ids:
            raise ValueError("thread IDs must be unique and nonempty")
        seen_thread_ids.add(thread_id)
        if type(item.get("is_resolved")) is not bool:
            raise ValueError("thread.is_resolved must be boolean")
        if _sha(item.get("head_sha"), "thread.head_sha") != head:
            raise ValueError("thread receipt from stale PR head")
        review_refs.append(_url(item.get("url"), "thread.url"))
        if not item["is_resolved"]:
            unresolved_threads += 1

    missing = []
    failed = []
    pending = []
    if required_checks is None:
        missing.append("required_check_policy")
    elif checks is None and required_checks:
        missing.append("check_receipts")
    else:
        for name in required_checks:
            item = check_by_name.get(name)
            if item is None:
                missing.append(f"check:{name}")
            elif item["status"] in _PENDING:
                pending.append(name)
            elif item["conclusion"] in _BAD:
                failed.append(name)
    if require_conversations_resolved is None:
        missing.append("conversation_resolution_policy")
    elif require_conversations_resolved and threads is None:
        missing.append("thread_receipts")
    if required_approvals is None:
        missing.append("required_review_policy")
    elif required_approvals and reviews is None:
        missing.append("review_receipts")
    approvals = sum(approval_by_user.values()) if reviews is not None else None
    if pr["merged"]:
        disposition = "MERGED_RECORDED" if merge_sha else "INSUFFICIENT_EVIDENCE"
        if not merge_sha:
            missing.append("merge_commit_sha")
    elif pr["state"] == "closed":
        disposition = "CLOSED_UNMERGED"
    elif pr["draft"]:
        disposition = "DRAFT"
    elif missing:
        disposition = "INSUFFICIENT_EVIDENCE"
    elif failed:
        disposition = "BLOCKED_CHECK_FAILURE"
    elif pending:
        disposition = "WAITING_FOR_CHECKS"
    elif require_conversations_resolved and unresolved_threads:
        disposition = "BLOCKED_UNRESOLVED_THREADS"
    elif approvals is not None and required_approvals is not None and approvals < required_approvals:
        disposition = "HUMAN_GATE"
    else:
        disposition = "SNAPSHOT_READY_FOR_AUTHORIZED_REVIEW"
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    refs = sorted(set([pr_url] + ([rule_url] if rule_url else []) + check_refs + review_refs))
    return {
        "schema_version": "wrm.pr-ledger-output.v1",
        "evidence_level": "SUPPLIED_SNAPSHOT_NOT_INDEPENDENTLY_ATTESTED",
        "freshness_scope": "AS_OF_SUPPLIED_OBSERVED_AT_ONLY",
        "pr_number": number,
        "pr_head_sha": head,
        "observed_at": data["observed_at"],
        "source_snapshot_sha256": "sha256:" + hashlib.sha256(canonical.encode()).hexdigest(),
        "disposition": disposition,
        "missing_evidence": sorted(set(missing)),
        "failed_required_checks": sorted(failed),
        "pending_required_checks": sorted(pending),
        "verified_current_head_approvals": approvals,
        "required_approvals": required_approvals,
        "require_conversations_resolved": require_conversations_resolved,
        "unresolved_review_threads": unresolved_threads,
        "evidence_refs": refs,
        "authority_created": False,
        "execution_triggered": False,
        "economic_claims": {key: None for key in _VALUE_UNKNOWN},
    }
