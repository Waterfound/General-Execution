from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_digest
from .resume_tick import (
    CoreVerificationReceipt,
    CoreVerificationRequirement,
)
from .vercel_sandbox import (
    VercelSandboxConformanceRun,
    VercelSandboxConformanceSpec,
    verify_vercel_sandbox_conformance_run,
)

CORE_VERIFICATION_MANIFEST_SCHEMA = "ge.core-verification-manifest.v1"
VERCEL_CORE_VERIFIER_REF = "verifier://vercel-sandbox-conformance/v1"


class CoreVerificationAdmissionError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CoreVerificationAdmissionError(f"{name} must be a non-empty string")


def _commit_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise CoreVerificationAdmissionError(
            f"{name} must be a 40-character commit SHA"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise CoreVerificationAdmissionError(
            f"{name} must be hexadecimal"
        ) from exc


@dataclass(frozen=True, slots=True)
class CoreVerificationManifest:
    target_revision: str
    suite_ref: str
    focused_test_path: str
    focused_test_count: int
    verifier_ref: str = VERCEL_CORE_VERIFIER_REF
    require_full_repository_pytest: bool = True
    schema_version: str = CORE_VERIFICATION_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CORE_VERIFICATION_MANIFEST_SCHEMA:
            raise CoreVerificationAdmissionError(
                "unsupported core verification manifest schema"
            )
        _commit_sha("target_revision", self.target_revision)
        for name in (
            "suite_ref",
            "focused_test_path",
            "verifier_ref",
        ):
            _nonempty(name, getattr(self, name))
        if not self.focused_test_path.startswith("tests/"):
            raise CoreVerificationAdmissionError(
                "focused_test_path must be under tests/"
            )
        if not isinstance(self.focused_test_count, int) or isinstance(
            self.focused_test_count, bool
        ):
            raise CoreVerificationAdmissionError(
                "focused_test_count must be an integer"
            )
        if self.focused_test_count < 1:
            raise CoreVerificationAdmissionError(
                "focused_test_count must be >= 1"
            )
        if self.verifier_ref != VERCEL_CORE_VERIFIER_REF:
            raise CoreVerificationAdmissionError(
                "core verification verifier is protocol-fixed"
            )
        if self.require_full_repository_pytest is not True:
            raise CoreVerificationAdmissionError(
                "core verification requires full repository pytest"
            )

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    def requirement(self) -> CoreVerificationRequirement:
        return CoreVerificationRequirement(
            required_revision=self.target_revision,
            required_suite_ref=self.suite_ref,
            required_verifier_ref=self.verifier_ref,
            minimum_test_count=self.focused_test_count,
        )


def _pytest_command_passed(run: VercelSandboxConformanceRun) -> bool:
    matches = tuple(
        item
        for item in run.command_evidence
        if item.command_id == "pytest"
    )
    return len(matches) == 1 and matches[0].exit_code == 0


def admit_vercel_core_verification(
    manifest: CoreVerificationManifest,
    spec: VercelSandboxConformanceSpec,
    run: VercelSandboxConformanceRun,
    *,
    executed_at: str,
) -> CoreVerificationReceipt:
    _nonempty("executed_at", executed_at)

    if spec.revision != manifest.target_revision:
        raise CoreVerificationAdmissionError(
            "verification spec does not target manifest revision"
        )
    if not verify_vercel_sandbox_conformance_run(spec, run):
        raise CoreVerificationAdmissionError(
            "Vercel Sandbox conformance evidence does not verify"
        )
    if not run.all_passed:
        raise CoreVerificationAdmissionError(
            "Vercel Sandbox conformance run is not fully green"
        )
    if not run.revision_verified or run.observed_revision != manifest.target_revision:
        raise CoreVerificationAdmissionError(
            "Vercel Sandbox did not verify the exact manifest revision"
        )
    if not run.stopped or run.stop_error_digest is not None:
        raise CoreVerificationAdmissionError(
            "Vercel Sandbox did not shut down cleanly"
        )
    if manifest.require_full_repository_pytest and not _pytest_command_passed(run):
        raise CoreVerificationAdmissionError(
            "full repository pytest evidence is missing or failed"
        )

    return CoreVerificationReceipt(
        target_revision=manifest.target_revision,
        suite_ref=manifest.suite_ref,
        evidence_ref=f"vercel-sandbox-run:{run.run_id}",
        evidence_digest=run.digest,
        verifier_ref=manifest.verifier_ref,
        executed_at=executed_at,
        passed=True,
        test_count=manifest.focused_test_count,
    )
