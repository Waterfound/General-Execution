"""Read-only provider telemetry for WRM-T1; never infer customer value from CI.

GitHub Actions job timestamps measure an observed provider job span, not
mission intent-to-terminal latency, human time, coordination tax, or ROI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


def _time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} requires an explicit timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} lacks timezone")
    return parsed.astimezone(timezone.utc)


def project_github_actions_jobs(
    run: Mapping[str, object], jobs_page: Mapping[str, object]
) -> dict[str, object]:
    """Project an observed GitHub Actions run and a *complete* jobs page.

    A truncated or incomplete jobs page yields null timing, never an
    apparently complete measurement. No network, writes, or authority.
    """
    if not isinstance(run, Mapping) or not isinstance(jobs_page, Mapping):
        raise ValueError("run and jobs_page must be mappings")
    run_id = run.get("id")
    if type(run_id) is not int or run_id < 1:
        raise ValueError("run.id must be a positive integer")
    run_url = run.get("html_url")
    if not isinstance(run_url, str) or not run_url.startswith(
        "https://github.com/"
    ):
        raise ValueError("run.html_url must be a GitHub URL")
    name = run.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("run.name must be nonempty")
    status = run.get("status")
    if status not in ("queued", "in_progress", "completed"):
        raise ValueError("unsupported run.status")
    conclusion = run.get("conclusion")
    if conclusion is not None and not isinstance(conclusion, str):
        raise ValueError("run.conclusion must be a string or null")
    if status != "completed" and conclusion is not None:
        raise ValueError("incomplete run cannot have a conclusion")
    head_sha = run.get("head_sha")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("run.head_sha must be 40 hex characters")
    try:
        int(head_sha, 16)
    except ValueError as exc:
        raise ValueError("run.head_sha must be hexadecimal") from exc

    total = jobs_page.get("total_count")
    jobs = jobs_page.get("jobs")
    if type(total) is not int or total < 0 or not isinstance(jobs, list):
        raise ValueError("jobs_page requires total_count and jobs")
    if len(jobs) > total:
        raise ValueError("jobs page exceeds total_count")
    ids: set[int] = set()
    completed = 0
    intervals: list[tuple[datetime, datetime]] = []
    for job in jobs:
        if not isinstance(job, Mapping):
            raise ValueError("job must be a mapping")
        job_id = job.get("id")
        if type(job_id) is not int or job_id < 1 or job_id in ids:
            raise ValueError("job ids must be unique positive integers")
        ids.add(job_id)
        job_status = job.get("status")
        if job_status not in ("queued", "in_progress", "completed", "waiting", "pending"):
            raise ValueError("unsupported job.status")
        if job_status == "completed":
            completed += 1
            start, end = job.get("started_at"), job.get("completed_at")
            if start is not None and end is not None:
                parsed_start = _time(start, "job.started_at")
                parsed_end = _time(end, "job.completed_at")
                if parsed_end < parsed_start:
                    raise ValueError("job completion precedes start")
                intervals.append((parsed_start, parsed_end))
        elif job.get("completed_at") is not None:
            raise ValueError("noncompleted job cannot have completed_at")

    complete = status == "completed" and len(jobs) == total and completed == total
    # For zero jobs, no execution time can be observed.
    span = None
    if complete and total > 0 and len(intervals) == total:
        span = (max(end for _, end in intervals) - min(start for start, _ in intervals)).total_seconds()

    return {
        "schema_version": "wrm.t1.github-actions-provider-telemetry.v1",
        "scope": "CI_PROVIDER_JOB_SPAN_ONLY_NOT_CUSTOMER_MISSION",
        "run_id": run_id,
        "run_name": name,
        "run_status": status,
        "run_conclusion": conclusion,
        "head_sha": head_sha,
        "jobs_expected": total,
        "jobs_observed": len(jobs),
        "jobs_completed": completed,
        "complete_job_evidence": complete,
        "observed_ci_job_span_seconds": span,
        "source_refs": [run_url],
        "human_interventions_requested": None,
        "human_interventions_genuinely_required": None,
        "observable_human_active_minutes": None,
        "mission_completion_latency_seconds": None,
        "coordination_tax_removed": None,
        "operator_hours_saved": None,
        "autonomous_resolution_rate": None,
        "rework_avoided": None,
        "recovery_improvement": None,
        "roi": None,
        "willingness_to_pay": None,
        "authority_created": False,
        "execution_triggered": False,
    }
