"""Read-only projection of historical pilot evidence; capability is not ROI."""
from general_execution.revenue_value_proof import project_value_proof


def project_pilot(report, receipt, report_ref, receipt_ref):
    """Fail closed on source mismatch and preserve unknown economic outcomes."""
    if not isinstance(report, dict) or not isinstance(receipt, dict):
        raise ValueError("source type")
    if not report_ref or not receipt_ref or report_ref == receipt_ref:
        raise ValueError("source references")
    if report.get("status") != "PASS_STOPPED_AT_HUMAN_GATE":
        raise ValueError("pilot status")
    if report.get("final_state") != "human_gate" or report.get("authority_stop") is not True:
        raise ValueError("authority stop")
    if receipt.get("status") != "PASS_VERIFIED" or receipt.get("report_digest_recalculated") is not True:
        raise ValueError("receipt status")
    if receipt.get("report_digest") != report.get("report_digest"):
        raise ValueError("digest mismatch")
    if str(receipt.get("provider_run_id")) != report.get("provider_run_id"):
        raise ValueError("run mismatch")
    runtime = receipt.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("runtime")
    for key in ("state_transitions", "process_invocations", "final_state", "authority_stop"):
        if runtime.get(key) != report.get(key):
            raise ValueError("runtime mismatch")
    for key in ("state_transitions", "process_invocations"):
        if type(report.get(key)) is not int or report[key] < 0:
            raise ValueError("counter")
    return project_value_proof({
        "workflow_id": report["activation_id"],
        "representative_workflow_class": "historical-capability-control",
        "terminal_state": "HUMAN_GATE",
        "machine_state_transitions": report["state_transitions"],
        "process_invocations": report["process_invocations"],
        "evidence_refs": [report_ref, receipt_ref],
    })
