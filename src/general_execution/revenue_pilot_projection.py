"""Read-only WRM-T1 projection from verified unattended-pilot evidence."""
from __future__ import annotations
from collections.abc import Mapping
from .revenue_value_proof import project_value_proof


def project_verified_pilot(report: Mapping, validation: Mapping) -> dict:
    """Cross-check pilot and validator; preserve unknown economic metrics."""
    if report.get("schema_version") != "ge.unattended-pilot-live-report.v1":
        raise ValueError("unsupported pilot report")
    if validation.get("schema_version") != "ge.unattended-pilot-live-validation.v1":
        raise ValueError("unsupported pilot validation")
    if report.get("status") != "PASS_STOPPED_AT_HUMAN_GATE":
        raise ValueError("pilot did not pass at human gate")
    if validation.get("status") != "PASS_VERIFIED":
        raise ValueError("pilot validation did not pass")
    if validation.get("report_digest_recalculated") is not True:
        raise ValueError("prior digest verification missing")
    runtime = validation.get("runtime")
    authority = validation.get("authority")
    if not isinstance(runtime, Mapping) or not isinstance(authority, Mapping):
        raise ValueError("missing validation sections")
    for field in ("process_invocations", "state_transitions", "final_generation",
                  "final_state", "authority_stop", "human_required",
                  "chat_context_required", "real_provider_trigger_observed",
                  "bounded_unattended_execution_observed"):
        if type(report.get(field)) is not type(runtime.get(field)) or report.get(field) != runtime.get(field):
            raise ValueError(f"mismatched runtime field: {field}")
    for field in ("main_modified", "merge_performed", "release_performed",
                  "production_modified", "new_spend_authorized"):
        if report.get(field) is not False or authority.get(field) is not False:
            raise ValueError(f"authority boundary mismatch: {field}")
    for field in ("authority_stop", "human_required", "real_provider_trigger_observed",
                  "bounded_unattended_execution_observed"):
        if report.get(field) is not True:
            raise ValueError(f"missing capability observation: {field}")
    if report.get("final_state") != "human_gate" or report.get("chat_context_required") is not False:
        raise ValueError("unexpected terminal state")
    for field in ("provider", "tested_revision", "report_digest"):
        if report.get(field) != validation.get(field):
            raise ValueError(f"mismatched evidence: {field}")
    if str(report.get("provider_run_id")) != str(validation.get("provider_run_id")):
        raise ValueError("mismatched provider run")
    transitions, invocations = report.get("state_transitions"), report.get("process_invocations")
    if any(type(value) is not int or value < 0 for value in (transitions, invocations)):
        raise ValueError("invalid counters")
    identifier = report.get("activation_id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("invalid activation id")
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError("invalid report digest")
    observation = {
        "workflow_id": identifier,
        "representative_workflow_class": "bounded-provider-pilot-not-customer-workflow",
        "terminal_state": "HUMAN_GATE",
        "machine_state_transitions": transitions,
        "process_invocations": invocations,
        "evidence_refs": [digest, "github-actions-run:" + str(report["provider_run_id"])],
    }
    return {
        "schema_version": "wrm.t1.verified-pilot-projection.v1",
        "prior_validator_digest_attested": True,
        "independent_digest_recomputation": False,
        "customer_workflow_observed": False,
        "natural_comparable_available": False,
        "economic_roi_proven": False,
        "authority_created": False,
        "execution_triggered": False,
        "value_proof": project_value_proof(observation),
    }
