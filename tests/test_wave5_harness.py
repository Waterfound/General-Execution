"""Unit-only provider doubles; these tests never produce live verification evidence."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from general_execution import run_vercel_sandbox_conformance


@pytest.fixture
def harness():
    path = Path(__file__).resolve().parents[1] / "scripts/verify_wave5_core.py"
    spec = importlib.util.spec_from_file_location("wave5_harness_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_provider(*, pytest_exit=0, stop_error=False):
    def run(spec, **kwargs):
        class Sandbox:
            name = "sbx-unit-test-only"
            index = 0

            def run_command(self, executable, args):
                self.index += 1
                return SimpleNamespace(
                    exit_code=pytest_exit if self.index == 6 else 0,
                    stdout=spec.revision + "\n" if self.index == 1 else "unit fixture\n",
                    stderr="",
                )

            def stop(self, *, blocking=False):
                assert blocking
                if stop_error:
                    raise RuntimeError("unit-test shutdown failure")

        return run_vercel_sandbox_conformance(spec, sandbox_factory=lambda *_: Sandbox())
    return run


def test_success_keeps_exact_manifest_and_admitted_receipt(harness, monkeypatch):
    monkeypatch.setattr(harness, "run_vercel_sandbox_conformance", fake_provider())
    code, output = harness.execute_verification()
    assert code == 0 and output["status"] == "PASS"
    assert output["receipt"]["target_revision"] == harness.WAVE5_REVISION
    assert output["receipt"]["evidence_digest"] == output["run_digest"]


@pytest.mark.parametrize("kwargs", [{"pytest_exit": 1}, {"stop_error": True}])
def test_failed_run_is_retained_without_receipt(harness, monkeypatch, kwargs):
    monkeypatch.setattr(harness, "run_vercel_sandbox_conformance", fake_provider(**kwargs))
    code, output = harness.execute_verification()
    assert code == 1 and output["status"] == "FAIL"
    assert output["run"] and output["run_digest"]
    assert not output["run"]["all_passed"]
    assert output["receipt"] is None and output["receipt_digest"] is None


def test_provider_error_never_exposes_exception_credentials(harness, monkeypatch):
    def error(*args, **kwargs):
        raise RuntimeError("provider echoed token-secret-do-not-record")
    monkeypatch.setattr(harness, "run_vercel_sandbox_conformance", error)
    code, output = harness.execute_verification()
    assert code == 2 and output["status"] == "ERROR"
    assert output["receipt"] is None and output["run"] is None
    assert "token-secret" not in json.dumps(output)
    assert output["error_type"] == "RuntimeError"


def test_artifact_cannot_be_overwritten_or_rerun(harness, monkeypatch, tmp_path):
    output = tmp_path / "receipt.json"
    output.write_text("existing evidence")
    def unexpected():
        pytest.fail("provider must not be invoked for an existing artifact")
    monkeypatch.setattr(harness, "execute_verification", unexpected)
    with pytest.raises(FileExistsError):
        harness.main(["--output", str(output)])
    assert output.read_text() == "existing evidence"


def test_failure_artifact_is_persisted(harness, monkeypatch, tmp_path):
    monkeypatch.setattr(harness, "run_vercel_sandbox_conformance", fake_provider(pytest_exit=1))
    output = tmp_path / "failed.json"
    assert harness.main(["--output", str(output)]) == 1
    assert json.loads(output.read_text())["status"] == "FAIL"


def test_revision_override_is_rejected_before_provider(harness, monkeypatch):
    def unexpected():
        pytest.fail("revision override must not invoke provider")
    monkeypatch.setattr(harness, "execute_verification", unexpected)
    with pytest.raises(SystemExit) as exc:
        harness.main(["--revision", "f" * 40])
    assert exc.value.code == 2
