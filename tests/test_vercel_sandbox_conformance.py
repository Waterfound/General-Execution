from dataclasses import fields, replace

import pytest

from general_execution.vercel_sandbox import (
    GENERAL_EXECUTION_REPOSITORY_URL,
    VERCEL_SANDBOX_PYTHON,
    VERCEL_SANDBOX_RUNTIME,
    VercelSandboxConformanceError,
    VercelSandboxConformanceRun,
    VercelSandboxConformanceSpec,
    run_vercel_sandbox_conformance,
    verify_vercel_sandbox_conformance_run,
)

REVISION = "a" * 40
OTHER_REVISION = "b" * 40


class FakeCommandResult:
    def __init__(self, exit_code=0, stdout="", stderr="", *, callable_streams=False):
        self.exit_code = exit_code
        if callable_streams:
            self.stdout = lambda: stdout
            self.stderr = lambda: stderr
        else:
            self.stdout = stdout
            self.stderr = stderr


class FakeSandbox:
    def __init__(self, results, *, sandbox_id="sbx-general-execution", stop_error=None):
        self.sandbox_id = sandbox_id
        self.results = list(results)
        self.commands = []
        self.stop_error = stop_error
        self.stop_called = False

    def run_command(self, executable, args):
        self.commands.append((executable, tuple(args)))
        if not self.results:
            raise AssertionError("runner executed an unexpected command")
        return self.results.pop(0)

    def stop(self):
        self.stop_called = True
        if self.stop_error is not None:
            raise self.stop_error
        return None


def successful_results(revision=REVISION, *, callable_streams=False):
    return [
        FakeCommandResult(0, revision + "\n", callable_streams=callable_streams),
        FakeCommandResult(0, "python provisioned\n", callable_streams=callable_streams),
        FakeCommandResult(0, "3.13.14\n3.40.0\n", callable_streams=callable_streams),
        FakeCommandResult(0, "installed\n", callable_streams=callable_streams),
        FakeCommandResult(0, "", callable_streams=callable_streams),
        FakeCommandResult(0, "157 passed\n", callable_streams=callable_streams),
    ]


def factory_for(sandbox, capture=None):
    def factory(spec, token, team_id, project_id):
        if capture is not None:
            capture.append((spec, token, team_id, project_id))
        return sandbox

    return factory


def test_successful_run_executes_only_protocol_fixed_sequence_and_verifies():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox(successful_results())
    run = run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))

    assert run.all_passed is True
    assert run.revision_verified is True
    assert run.observed_revision == REVISION
    assert run.stopped is True
    assert sandbox.stop_called is True
    assert [item.command_id for item in run.command_evidence] == [
        "verify_revision",
        "provision_python",
        "sqlite_probe",
        "install_dev",
        "compileall",
        "pytest",
    ]
    assert sandbox.commands == [
        ("git", ("rev-parse", "HEAD")),
        ("sudo", ("dnf", "-y", "-q", "install", "python3.13", "python3.13-pip")),
        (
            VERCEL_SANDBOX_PYTHON,
            ("-c", "import sys, sqlite3; print(sys.version); print(sqlite3.sqlite_version)"),
        ),
        (
            VERCEL_SANDBOX_PYTHON,
            (
                "-m",
                "pip",
                "install",
                "-e",
                ".[dev]",
                "--disable-pip-version-check",
            ),
        ),
        (VERCEL_SANDBOX_PYTHON, ("-m", "compileall", "-q", "src")),
        (VERCEL_SANDBOX_PYTHON, ("-m", "pytest", "-q")),
    ]
    assert verify_vercel_sandbox_conformance_run(spec, run)


def test_spec_rejects_arbitrary_repository_runtime_timeout_and_revision_shape():
    with pytest.raises(ValueError):
        VercelSandboxConformanceSpec("A" * 40)
    with pytest.raises(ValueError):
        VercelSandboxConformanceSpec("a" * 39)
    with pytest.raises(ValueError):
        VercelSandboxConformanceSpec(REVISION, repository_url="https://example.invalid/repo.git")
    with pytest.raises(ValueError):
        VercelSandboxConformanceSpec(REVISION, runtime="python3.13")
    with pytest.raises(ValueError):
        VercelSandboxConformanceSpec(REVISION, timeout_ms=1)

    names = {field.name for field in fields(VercelSandboxConformanceSpec)}
    assert "commands" not in names
    assert GENERAL_EXECUTION_REPOSITORY_URL.endswith("General-Execution.git")
    assert VERCEL_SANDBOX_RUNTIME == "node24"
    assert VERCEL_SANDBOX_PYTHON == "python3.13"


def test_revision_mismatch_fails_closed_before_provision_or_tests_and_stops():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox([FakeCommandResult(0, OTHER_REVISION + "\n")])
    run = run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))

    assert run.all_passed is False
    assert run.revision_verified is False
    assert run.observed_revision == OTHER_REVISION
    assert len(run.command_evidence) == 1
    assert sandbox.commands == [("git", ("rev-parse", "HEAD"))]
    assert sandbox.stop_called is True
    assert verify_vercel_sandbox_conformance_run(spec, run)


def test_nonzero_revision_command_never_verifies_even_if_stdout_contains_expected_sha():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox([FakeCommandResult(2, REVISION + "\n", "git error")])
    run = run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))

    assert run.observed_revision == REVISION
    assert run.revision_verified is False
    assert run.all_passed is False
    assert len(run.command_evidence) == 1
    assert verify_vercel_sandbox_conformance_run(spec, run)


def test_first_nonzero_conformance_command_stops_sequence():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox(
        [
            FakeCommandResult(0, REVISION + "\n"),
            FakeCommandResult(1, "", "dnf failed"),
            FakeCommandResult(0, "must not run"),
        ]
    )
    run = run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))

    assert run.revision_verified is True
    assert run.all_passed is False
    assert [item.command_id for item in run.command_evidence] == ["verify_revision", "provision_python"]
    assert len(sandbox.commands) == 2
    assert sandbox.stop_called is True


def test_stop_failure_is_evidence_and_prevents_all_passed():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox(successful_results(), stop_error=RuntimeError("stop unavailable"))
    run = run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))

    assert len(run.command_evidence) == 6
    assert run.revision_verified is True
    assert run.stopped is False
    assert run.stop_error_digest is not None
    assert run.all_passed is False
    assert verify_vercel_sandbox_conformance_run(spec, run)


def test_credentials_are_used_for_factory_but_never_enter_run_evidence():
    spec = VercelSandboxConformanceSpec(REVISION)
    captured = []
    sandbox = FakeSandbox(successful_results())
    run = run_vercel_sandbox_conformance(
        spec,
        team_id="team-test",
        project_id="prj-test",
        token="super-secret-token",
        sandbox_factory=factory_for(sandbox, captured),
    )

    assert captured == [(spec, "super-secret-token", "team-test", "prj-test")]
    assert run.team_id == "team-test"
    assert run.project_id == "prj-test"
    assert "super-secret-token" not in repr(run)
    assert "super-secret-token" not in run.digest


def test_callable_command_streams_are_supported_and_digest_is_deterministic():
    spec = VercelSandboxConformanceSpec(REVISION)
    first = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=factory_for(FakeSandbox(successful_results(callable_streams=True))),
    )
    second = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=factory_for(FakeSandbox(successful_results(callable_streams=True))),
    )
    assert first == second
    assert first.digest == second.digest
    assert first.all_passed is True


def test_missing_sandbox_identity_still_stops_before_failing():
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox(successful_results(), sandbox_id="")
    with pytest.raises(VercelSandboxConformanceError, match="stable sandbox identity"):
        run_vercel_sandbox_conformance(spec, sandbox_factory=factory_for(sandbox))
    assert sandbox.stop_called is True
    assert sandbox.commands == []


def test_command_sequence_tampering_is_rejected_by_run_model():
    spec = VercelSandboxConformanceSpec(REVISION)
    run = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=factory_for(FakeSandbox(successful_results())),
    )
    tampered_command = replace(run.command_evidence[3], args=("-c", "arbitrary"))
    with pytest.raises(ValueError, match="protocol-fixed command prefix"):
        replace(
            run,
            command_evidence=run.command_evidence[:3] + (tampered_command,) + run.command_evidence[4:],
        )


def test_artificially_truncated_success_prefix_is_rejected():
    spec = VercelSandboxConformanceSpec(REVISION)
    run = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=factory_for(FakeSandbox(successful_results())),
    )
    with pytest.raises(ValueError, match="cannot terminate"):
        VercelSandboxConformanceRun(
            spec_id=run.spec_id,
            spec_digest=run.spec_digest,
            provider=run.provider,
            sandbox_id=run.sandbox_id,
            repository_url=run.repository_url,
            requested_revision=run.requested_revision,
            observed_revision=run.observed_revision,
            runtime=run.runtime,
            command_evidence=run.command_evidence[:3],
            revision_verified=True,
            stopped=True,
            stop_error_digest=None,
            all_passed=False,
        )
