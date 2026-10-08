"""Read-only, evidence-first WRM-T1 observation projection.

This module never authorizes work, estimates a manual baseline, or claims ROI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


_COUNTERS = (
    "machine_state_transitions",
    "process_invocations",
    "human_interventions_requested",
    "human_interventions_genuinely_required",
    "observable_human_active_minutes",
    "retries",
    "rework_events",
    "recovery_events",
    "provenance_items_expected",
    "provenance_items_present",
    "autonomous_resolutions",
    "resolution_opportunities",
)
_FIELDS = set(_COUNTERS) | {
    "workflow_id", "representative_workflow_class", "intent_timestamp",
    "terminal_timestamp", "terminal_state", "evidence_refs",
}
_COMPLETED = {"DONE", "DONE_TECHNICAL", "DONE_CANONICAL"}
_UNPROVEN = (
    "approvals_eliminated", "operator_hours_saved",
    "matched_latency_reduction_seconds", "coordination_tax_removed",
    "recovery_improvement", "avoidable_rework_reduced",
    "control_plane_leverage", "monetary_risk_reduction", "roi",
    "willingness_to_pay",
)


def _timestamp(value: object, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO-8601 timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must have an explicit timezone")
    return parsed.astimezone(timezone.utc)


def _rate(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def project_value_proof(observation: Mapping[str, object]) -> dict[str, object]:
    """Validate observed facts and derive only metrics supported by those facts.

    Missing facts stay null. A single observation cannot prove economic savings.
    """
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    unknown = set(observation) - _FIELDS
    if unknown:
        raise ValueError(f"unknown observation fields: {sorted(unknown)}")
    for key in ("workflow_id", "representative_workflow_class", "terminal_state"):
        if not isinstance(observation.get(key), str) or not observation[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    counts: dict[str, int | None] = {}
    for key in _COUNTERS:
        value = observation.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{key} must be a nonnegative integer or null")
        counts[key] = value
    for smaller, larger in (
        ("human_interventions_genuinely_required", "human_interventions_requested"),
        ("provenance_items_present", "provenance_items_expected"),
        ("autonomous_resolutions", "resolution_opportunities"),
    ):
        if counts[smaller] is not None and counts[larger] is not None:
            if counts[smaller] > counts[larger]:
                raise ValueError(f"{smaller} cannot exceed {larger}")
    refs = observation.get("evidence_refs")
    if refs is not None and (
        not isinstance(refs, list)
        or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        raise ValueError("evidence_refs must be a list of unique nonempty strings or null")
    start = _timestamp(observation.get("intent_timestamp"), "intent_timestamp")
    end = _timestamp(observation.get("terminal_timestamp"), "terminal_timestamp")
    if start is not None and end is not None and end < start:
        raise ValueError("terminal_timestamp precedes intent_timestamp")
    elapsed = (end - start).total_seconds() if start and end else None
    return {
        "schema_version": "wrm.t1.value-proof-observation.v1",
        "authority_created": False,
        "execution_triggered": False,
        "raw_observation": {key: observation.get(key) for key in sorted(_FIELDS)},
        "derived": {
            "observed_elapsed_seconds": elapsed,
            "mission_completion_latency_seconds": (
                elapsed if observation["terminal_state"] in _COMPLETED else None
            ),
            "autonomous_resolution_rate": _rate(
                counts["autonomous_resolutions"], counts["resolution_opportunities"]
            ),
            "provenance_coverage": _rate(
                counts["provenance_items_present"], counts["provenance_items_expected"]
            ),
        },
        "unproven_value_claims": {key: None for key in _UNPROVEN},
        "evidence_level": "OBSERVED_CAPABILITY_NOT_ECONOMIC_ROI",
    }
