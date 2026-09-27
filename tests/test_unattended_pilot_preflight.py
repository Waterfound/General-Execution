import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_unattended_pilot_preflight_is_process_separated_and_stops_at_human_gate(tmp_path):
    out = tmp_path / "pilot"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_unattended_pilot.py"),
            "--output",
            str(out),
        ],
        cwd=ROOT,
        check=True,
    )
    report = json.loads((out / "pilot-preflight-report.json").read_text())
    assert report["status"] == "PASS_NOT_ACTIVATED"
    assert report["process_invocations"] == 8
    assert report["state_transitions"] == 5
    assert report["final_generation"] == 5
    assert report["final_state"] == "human_gate"
    assert report["authority_stop"]
    assert report["human_required"]
    assert not report["chat_context_required"]
    assert not report["provider_trigger_enabled"]
    assert not report["unattended_runtime_enabled"]
    assert not report["real_activation_authorized"]
    assert len(report["worker_pids"]) == 8

    recovery = json.loads((out / "07-recovery.json").read_text())
    assert recovery["request"]["disposition"] == "external_input_required"
    assert recovery["request"]["human_required"]
    assert recovery["request"]["requested_action_ref"] == "authority://release-approval"


def test_unattended_pilot_preflight_refuses_evidence_overwrite(tmp_path):
    out = tmp_path / "pilot"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_unattended_pilot.py"),
            "--output",
            str(out),
        ],
        cwd=ROOT,
        check=True,
    )
    rerun = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_unattended_pilot.py"),
            "--output",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert rerun.returncode != 0
    assert "Refusing to overwrite unattended pilot evidence" in (rerun.stdout + rerun.stderr)
