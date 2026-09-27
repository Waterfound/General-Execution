import pytest

from general_execution import (
    CoreVerificationAdmissionError,
    CoreVerificationManifest,
    VercelSandboxConformanceSpec,
    admit_vercel_core_verification,
    run_vercel_sandbox_conformance,
)

REVISION = "8f6494eca2c730de49b2e6ebfeb085cad1f33744"


class FakeCommandResult:
    def __init__(self, exit_code=0, stdout="", stderr=""):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class FakeSandbox:
    def __init__(self, results, *, stop_error=None):
        self.name = "sbx-wave5-verification"
        self.results = list(results)
        self.stop_error = stop_error

    def run_command(self, executable, args):
        if not self.results:
            raise AssertionError("unexpected command")
        return self.results.pop(0)

    def stop(self):
        if self.stop_error is not None:
            raise self.stop_error
        return None


def manifest(**changes):
    values = dict(
        target_revision=REVISION,
        suite_ref="tests://durable-execution/wave5-asp/full-repository",
        focused_test_path="tests/test_asp_transition.py",
        focused_test_count=18,
    )
    values.update(changes)
    return CoreVerificationManifest(**values)


def successful_results(revision=REVISION):
    return [
        FakeCommandResult(0, revision + "\n"),
        FakeCommandResult(0, "python provisioned\n"),
        FakeCommandResult(0, "3.13.14\n3.40.0\n"),
        FakeCommandResult(0, "installed\n"),
        FakeCommandResult(0, ""),
        FakeCommandResult(0, "all tests passed\n"),
    ]


def run(results=None, *, revision=REVISION, stop_error=None):
    spec = VercelSandboxConformanceSpec(revision)
    sandbox = FakeSandbox(
        successful_results(revision) if results is None else results,
        stop_error=stop_error,
    )
    evidence = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=lambda *_: sandbox,
    )
    return spec, evidence


def test_manifest_produces_exact_resume_tick_requirement():
    m = manifest()
    requirement = m.requirement()
    assert requirement.required_revision == REVISION
    assert requirement.required_suite_ref == m.suite_ref
    assert requirement.required_verifier_ref == m.verifier_ref
    assert requirement.minimum_test_count == 18


def test_manifest_rejects_unbounded_or_caller_selected_verifier():
    with pytest.raises(
        CoreVerificationAdmissionError,
        match="protocol-fixed",
    ):
        manifest(verifier_ref="verifier://caller-selected")
    with pytest.raises(
        CoreVerificationAdmissionError,
        match="requires full repository pytest",
    ):
        manifest(require_full_repository_pytest=False)


def test_green_exact_revision_admits_core_verification_receipt():
    m = manifest()
    spec, evidence = run()

    receipt = admit_vercel_core_verification(
        m,
        spec,
        evidence,
        executed_at="2026-09-23T16:45:00Z",
    )

    assert receipt.target_revision == REVISION
    assert receipt.suite_ref == m.suite_ref
    assert receipt.verifier_ref == m.verifier_ref
    assert receipt.evidence_ref == f"vercel-sandbox-run:{evidence.run_id}"
    assert receipt.evidence_digest == evidence.digest
    assert receipt.test_count == 18
    assert receipt.passed


def test_receipt_satisfies_manifest_requirement_exactly():
    m = manifest()
    spec, evidence = run()
    receipt = admit_vercel_core_verification(
        m,
        spec,
        evidence,
        executed_at="2026-09-23T16:45:00Z",
    )
    requirement = m.requirement()

    assert receipt.target_revision == requirement.required_revision
    assert receipt.suite_ref == requirement.required_suite_ref
    assert receipt.verifier_ref == requirement.required_verifier_ref
    assert receipt.test_count >= requirement.minimum_test_count


def test_wrong_spec_revision_is_rejected_even_when_that_run_is_green():
    m = manifest()
    other = "1" * 40
    spec, evidence = run(revision=other)

    with pytest.raises(
        CoreVerificationAdmissionError,
        match="does not target manifest revision",
    ):
        admit_vercel_core_verification(
            m,
            spec,
            evidence,
            executed_at="2026-09-23T16:45:00Z",
        )


def test_failed_pytest_cannot_admit_core_verification():
    m = manifest()
    results = successful_results()
    results[-1] = FakeCommandResult(1, "", "pytest failed")
    spec, evidence = run(results)

    assert not evidence.all_passed
    with pytest.raises(
        CoreVerificationAdmissionError,
        match="not fully green",
    ):
        admit_vercel_core_verification(
            m,
            spec,
            evidence,
            executed_at="2026-09-23T16:45:00Z",
        )


def test_shutdown_failure_cannot_admit_core_verification():
    m = manifest()
    spec, evidence = run(stop_error=RuntimeError("shutdown failed"))

    assert not evidence.all_passed
    assert not evidence.stopped
    with pytest.raises(
        CoreVerificationAdmissionError,
        match="not fully green",
    ):
        admit_vercel_core_verification(
            m,
            spec,
            evidence,
            executed_at="2026-09-23T16:45:00Z",
        )


def test_truncated_command_sequence_cannot_fabricate_receipt():
    m = manifest()
    spec = VercelSandboxConformanceSpec(REVISION)
    sandbox = FakeSandbox(
        [
            FakeCommandResult(0, REVISION + "\n"),
            FakeCommandResult(1, "", "provision failed"),
        ]
    )
    evidence = run_vercel_sandbox_conformance(
        spec,
        sandbox_factory=lambda *_: sandbox,
    )

    with pytest.raises(
        CoreVerificationAdmissionError,
        match="not fully green",
    ):
        admit_vercel_core_verification(
            m,
            spec,
            evidence,
            executed_at="2026-09-23T16:45:00Z",
        )


def test_manifest_focused_test_count_is_source_bound_metadata_not_runtime_claim():
    m = manifest()
    spec, evidence = run()
    receipt = admit_vercel_core_verification(
        m,
        spec,
        evidence,
        executed_at="2026-09-23T16:45:00Z",
    )

    # The Vercel runner proves full-repository pytest PASS at the exact Git SHA.
    # The manifest's focused count names the minimum Wave 5 cases that exact
    # source revision is known to contain; it is not parsed from stdout.
    assert receipt.test_count == m.focused_test_count
    assert receipt.evidence_digest == evidence.digest
