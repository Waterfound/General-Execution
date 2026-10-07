from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from general_execution.canonical import sha256_digest
from general_execution.canonical_constitution import (
    CANONICAL_CONSTITUTION_ARTIFACT_PATH,
    CANONICAL_CONSTITUTION_ID,
    CANONICAL_CONSTITUTION_REPOSITORY,
    CANONICAL_CONSTITUTION_REVISION,
)
from general_execution.execution_launch_admission import (
    ExecutionLaunchOrder,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
    launch_order_to_dict,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_constitutional_launch_admission.py"


def make_order() -> ExecutionLaunchOrder:
    return ExecutionLaunchOrder(
        workstream_id="constitutional-launch-host-test",
        owner="engineering",
        repository="Waterfound/General-Execution",
        executor="build_colony",
        objective="Exercise constitutionally governed durable launch host",
        order_ref="order://constitutional-launch-host-test",
        source_revision="a" * 40,
        required_authority_scopes=("candidate_write",),
        authority=LaunchAuthorityBinding(
            actor="Waterfound",
            authority_ref="authority://constitutional-launch-host-test",
            authority_boundary="Test-only candidate authority.",
            granted_scopes=("candidate_write",),
        ),
        executor_binding=LaunchExecutorBinding(
            executor="build_colony",
            availability="AVAILABLE",
            evidence_ref="executor://build-colony/test",
            evidence_digest=sha256_digest({"executor": "build_colony", "test": True}),
        ),
    )


def assessment(order: ExecutionLaunchOrder, disposition: str) -> dict:
    return {
        "workstream_id": order.workstream_id,
        "subject_digest": order.digest,
        "disposition": disposition,
        "basis_refs": (
            [] if disposition == "OUT_OF_SCOPE"
            else ["CCC:1750"]
        ),
        "reason": f"test {disposition}",
        "assessor": "canonical-constitution-test",
        "assessment_ref": "assessment://constitutional-launch-host-test",
        "constitution_id": CANONICAL_CONSTITUTION_ID,
        "constitution_repository": CANONICAL_CONSTITUTION_REPOSITORY,
        "constitution_revision": CANONICAL_CONSTITUTION_REVISION,
        "constitution_artifact_path": CANONICAL_CONSTITUTION_ARTIFACT_PATH,
        "schema_version": "ge.canonical-constitution-assessment.v1",
    }


def run(tmp_path: Path, disposition: str):
    order = make_order()
    order_path = tmp_path / "order.json"
    assessment_path = tmp_path / "assessment.json"
    constitutional_receipt = tmp_path / "constitutional-receipt.json"
    launch_receipt = tmp_path / "launch-receipt.json"
    result_path = tmp_path / "result.json"
    order_path.write_text(json.dumps(launch_order_to_dict(order)), encoding="utf-8")
    assessment_path.write_text(
        json.dumps(assessment(order, disposition)), encoding="utf-8"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--order",
            str(order_path),
            "--constitutional-assessment",
            str(assessment_path),
            "--authenticated-actor",
            "Waterfound",
            "--authenticated-order-digest",
            order.digest,
            "--constitutional-receipt-out",
            str(constitutional_receipt),
            "--launch-receipt-out",
            str(launch_receipt),
            "--result-out",
            str(result_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed, constitutional_receipt, launch_receipt, result_path


def test_compatible_materializes_constitutional_and_launch_receipts(tmp_path):
    completed, constitutional_receipt, launch_receipt, result_path = run(
        tmp_path, "COMPATIBLE"
    )
    assert completed.returncode == 0, completed.stderr
    assert constitutional_receipt.exists()
    assert launch_receipt.exists()
    result = json.loads(result_path.read_text())
    assert result["constitutional_gate_passed"] is True
    assert result["constitutional_admission_disposition"] == "ADMITTED"
    assert result["launch_admission_materialized"] is True
    assert result["launch_disposition"] == "ADMITTED"
    assert result["authority_created"] is False
    assert result["execution_triggered"] is False


def test_incompatible_stops_before_launch_receipt(tmp_path):
    completed, constitutional_receipt, launch_receipt, result_path = run(
        tmp_path, "INCOMPATIBLE"
    )
    assert completed.returncode == 0, completed.stderr
    assert constitutional_receipt.exists()
    assert not launch_receipt.exists()
    result = json.loads(result_path.read_text())
    assert result["constitutional_gate_passed"] is False
    assert result["constitutional_admission_disposition"] == "REJECTED"
    assert result["launch_admission_materialized"] is False
    assert result["launch_receipt_id"] is None
    assert result["dispatch_identity"] is None


def test_interpretation_required_stops_before_launch_receipt(tmp_path):
    completed, _, launch_receipt, result_path = run(
        tmp_path, "INTERPRETATION_REQUIRED"
    )
    assert completed.returncode == 0, completed.stderr
    assert not launch_receipt.exists()
    result = json.loads(result_path.read_text())
    assert result["constitutional_admission_disposition"] == "INTERPRETATION_GATE"
    assert result["launch_admission_materialized"] is False


def test_changed_order_invalidates_assessment(tmp_path):
    order = make_order()
    order_path = tmp_path / "order.json"
    assessment_path = tmp_path / "assessment.json"
    constitutional_receipt = tmp_path / "constitutional-receipt.json"
    result_path = tmp_path / "result.json"
    original_assessment = assessment(order, "COMPATIBLE")

    changed = ExecutionLaunchOrder(
        workstream_id=order.workstream_id,
        owner=order.owner,
        repository=order.repository,
        executor=order.executor,
        objective="Changed objective",
        order_ref=order.order_ref,
        source_revision=order.source_revision,
        required_authority_scopes=order.required_authority_scopes,
        authority=order.authority,
        executor_binding=order.executor_binding,
    )
    order_path.write_text(json.dumps(launch_order_to_dict(changed)), encoding="utf-8")
    assessment_path.write_text(json.dumps(original_assessment), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--order",
            str(order_path),
            "--constitutional-assessment",
            str(assessment_path),
            "--authenticated-actor",
            "Waterfound",
            "--authenticated-order-digest",
            changed.digest,
            "--constitutional-receipt-out",
            str(constitutional_receipt),
            "--result-out",
            str(result_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "does not bind the exact execution order" in completed.stderr
    assert not constitutional_receipt.exists()
    assert not result_path.exists()


def test_durable_runtime_workflow_requires_paired_constitutional_assessment():
    workflow = (ROOT / ".github" / "workflows" / "durable-launch-admission.yml").read_text()
    assert '"constitutional-assessments/*.json"' in workflow
    assert "expected one launch order and one constitutional assessment" in workflow
    assert "run_constitutional_launch_admission.py" in workflow
    assert "--constitutional-assessment /tmp/constitutional-assessment.json" in workflow
    assert "runtime/constitutional-admission/" in workflow
    assert "constitutional_gate_passed" in workflow
    assert "ge.constitutionally-governed-workstream-binding.v1" in workflow
