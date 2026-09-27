from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from .canonical import sha256_digest, stable_id

GENERAL_EXECUTION_REPOSITORY_URL = "https://github.com/Waterfound/General-Execution.git"
VERCEL_SANDBOX_PROVIDER = "vercel-sandbox"
VERCEL_SANDBOX_RUNTIME = "node24"
VERCEL_SANDBOX_TIMEOUT_MS = 300_000
VERCEL_SANDBOX_PYTHON = "python3.13"
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class VercelSandboxConformanceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VercelSandboxConformanceSpec:
    revision: str
    repository_url: str = GENERAL_EXECUTION_REPOSITORY_URL
    runtime: str = VERCEL_SANDBOX_RUNTIME
    timeout_ms: int = VERCEL_SANDBOX_TIMEOUT_MS
    schema_version: str = "ge.vercel-sandbox-conformance-spec.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.vercel-sandbox-conformance-spec.v1":
            raise ValueError("unsupported Vercel Sandbox conformance spec schema")
        if not REVISION_PATTERN.fullmatch(self.revision):
            raise ValueError("revision must be exactly 40 lowercase hexadecimal characters")
        if self.repository_url != GENERAL_EXECUTION_REPOSITORY_URL:
            raise ValueError("Vercel Sandbox conformance is restricted to the General Execution repository")
        if self.runtime != VERCEL_SANDBOX_RUNTIME:
            raise ValueError("Vercel Sandbox conformance runtime is protocol-fixed to node24")
        if self.timeout_ms != VERCEL_SANDBOX_TIMEOUT_MS:
            raise ValueError("Vercel Sandbox conformance timeout is protocol-fixed")

    @property
    def spec_id(self) -> str:
        return stable_id("gevspec", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class SandboxCommandEvidence:
    command_id: str
    executable: str
    args: tuple[str, ...]
    exit_code: int
    stdout_digest: str
    stderr_digest: str
    schema_version: str = "ge.sandbox-command-evidence.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.sandbox-command-evidence.v1":
            raise ValueError("unsupported sandbox command evidence schema")
        if not self.command_id or not self.command_id.strip():
            raise ValueError("command_id must be non-empty")
        if not self.executable or not self.executable.strip():
            raise ValueError("executable must be non-empty")
        if not isinstance(self.exit_code, int):
            raise ValueError("exit_code must be an integer")
        for name in ("stdout_digest", "stderr_digest"):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{name} must be sha256:<64-hex>")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class _FixedCommand:
    command_id: str
    executable: str
    args: tuple[str, ...]


def _fixed_commands() -> tuple[_FixedCommand, ...]:
    return (
        _FixedCommand("verify_revision", "git", ("rev-parse", "HEAD")),
        _FixedCommand(
            "provision_python",
            "sudo",
            ("dnf", "-y", "-q", "install", "python3.13", "python3.13-pip"),
        ),
        _FixedCommand(
            "sqlite_probe",
            VERCEL_SANDBOX_PYTHON,
            ("-c", "import sys, sqlite3; print(sys.version); print(sqlite3.sqlite_version)"),
        ),
        _FixedCommand(
            "install_dev",
            VERCEL_SANDBOX_PYTHON,
            ("-m", "pip", "install", "-e", ".[dev]", "--disable-pip-version-check"),
        ),
        _FixedCommand("compileall", VERCEL_SANDBOX_PYTHON, ("-m", "compileall", "-q", "src")),
        _FixedCommand("pytest", VERCEL_SANDBOX_PYTHON, ("-m", "pytest", "-q")),
    )


def _evidence_matches_fixed_prefix(evidence: tuple[SandboxCommandEvidence, ...]) -> bool:
    commands = _fixed_commands()
    if not evidence or len(evidence) > len(commands):
        return False
    return all(
        item.command_id == expected.command_id
        and item.executable == expected.executable
        and item.args == expected.args
        for item, expected in zip(evidence, commands, strict=False)
    )


@dataclass(frozen=True, slots=True)
class VercelSandboxConformanceRun:
    spec_id: str
    spec_digest: str
    provider: str
    sandbox_id: str
    repository_url: str
    requested_revision: str
    observed_revision: str | None
    runtime: str
    command_evidence: tuple[SandboxCommandEvidence, ...]
    revision_verified: bool
    stopped: bool
    stop_error_digest: str | None
    all_passed: bool
    team_id: str | None = None
    project_id: str | None = None
    schema_version: str = "ge.vercel-sandbox-conformance-run.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.vercel-sandbox-conformance-run.v1":
            raise ValueError("unsupported Vercel Sandbox conformance run schema")
        if self.provider != VERCEL_SANDBOX_PROVIDER:
            raise ValueError("provider must be vercel-sandbox")
        if not self.sandbox_id or not self.sandbox_id.strip():
            raise ValueError("sandbox_id must be non-empty")
        if self.repository_url != GENERAL_EXECUTION_REPOSITORY_URL:
            raise ValueError("run repository mismatch")
        if not REVISION_PATTERN.fullmatch(self.requested_revision):
            raise ValueError("requested_revision must be exact lowercase Git SHA")
        if self.observed_revision is not None and not REVISION_PATTERN.fullmatch(self.observed_revision):
            raise ValueError("observed_revision must be exact lowercase Git SHA")
        if self.runtime != VERCEL_SANDBOX_RUNTIME:
            raise ValueError("run runtime mismatch")
        if not _evidence_matches_fixed_prefix(self.command_evidence):
            raise ValueError("command evidence is not the protocol-fixed command prefix")

        first_exit = self.command_evidence[0].exit_code
        expected_revision_verified = first_exit == 0 and self.observed_revision == self.requested_revision
        if self.revision_verified != expected_revision_verified:
            raise ValueError("revision_verified does not match revision command evidence")

        if len(self.command_evidence) < len(_fixed_commands()):
            if self.revision_verified and self.command_evidence[-1].exit_code == 0:
                raise ValueError("successful command prefix cannot terminate before the fixed sequence completes")

        if self.stop_error_digest is not None:
            if not self.stop_error_digest.startswith("sha256:") or len(self.stop_error_digest) != 71:
                raise ValueError("stop_error_digest must be sha256:<64-hex>")
        if self.stopped == (self.stop_error_digest is not None):
            raise ValueError("stopped and stop_error_digest are inconsistent")

        expected_pass = (
            self.revision_verified
            and self.stopped
            and len(self.command_evidence) == len(_fixed_commands())
            and all(item.exit_code == 0 for item in self.command_evidence)
        )
        if self.all_passed != expected_pass:
            raise ValueError("all_passed does not match command/revision/stop evidence")

    @property
    def run_id(self) -> str:
        return stable_id("gevsrun", self)

    @property
    def digest(self) -> str:
        return sha256_digest(self)


class SandboxLike(Protocol):
    def run_command(self, executable: str, args: Sequence[str]): ...
    def stop(self): ...


SandboxFactory = Callable[[VercelSandboxConformanceSpec, str | None, str | None, str | None], SandboxLike]


def _string_output(value) -> str:
    if callable(value):
        value = value()
    if inspect.isawaitable(value):
        raise VercelSandboxConformanceError("sync conformance runner received asynchronous command output")
    if hasattr(value, "read") and callable(value.read):
        value = value.read()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None:
        return ""
    return str(value)


def _command_result(result) -> tuple[int, str, str]:
    exit_code = getattr(result, "exit_code", None)
    if exit_code is None:
        exit_code = getattr(result, "exitCode", None)
    if not isinstance(exit_code, int):
        raise VercelSandboxConformanceError("sandbox command result has no integer exit code")
    if not hasattr(result, "stdout") or not hasattr(result, "stderr"):
        raise VercelSandboxConformanceError("sandbox command result is missing stdout/stderr")
    return exit_code, _string_output(result.stdout), _string_output(result.stderr)


def _sandbox_id(sandbox: SandboxLike) -> str:
    # Current Vercel SDKs expose the stable, unique Sandbox identity primarily
    # through ``name``. Older SDK generations exposed id-shaped attributes.
    # Accept both forms without weakening the requirement for a non-empty,
    # provider-issued stable identity.
    for attribute in ("name", "sandbox_id", "sandboxId", "id"):
        value = getattr(sandbox, attribute, None)
        if callable(value):
            value = value()
        if isinstance(value, str) and value.strip():
            return value
    raise VercelSandboxConformanceError("Vercel Sandbox did not expose a stable sandbox identity")


def _default_sandbox_factory(
    spec: VercelSandboxConformanceSpec,
    token: str | None,
    team_id: str | None,
    project_id: str | None,
) -> SandboxLike:
    try:
        from vercel.sandbox import Sandbox
    except ImportError as exc:
        raise VercelSandboxConformanceError(
            "Vercel Python SDK is unavailable; install the optional vercel-sandbox dependency"
        ) from exc

    kwargs = {
        "runtime": spec.runtime,
        "source": {
            "type": "git",
            "url": spec.repository_url,
            "revision": spec.revision,
        },
        "timeout": spec.timeout_ms,
    }
    if token is not None:
        kwargs["token"] = token
    if team_id is not None:
        kwargs["team_id"] = team_id
    if project_id is not None:
        kwargs["project_id"] = project_id

    try:
        sandbox = Sandbox.create(**kwargs)
    except Exception as exc:
        raise VercelSandboxConformanceError("Vercel Sandbox creation failed") from exc
    if inspect.isawaitable(sandbox):
        raise VercelSandboxConformanceError("sync conformance runner received asynchronous Sandbox.create result")
    return sandbox


def _command_evidence(command: _FixedCommand, exit_code: int, stdout: str, stderr: str) -> SandboxCommandEvidence:
    return SandboxCommandEvidence(
        command_id=command.command_id,
        executable=command.executable,
        args=command.args,
        exit_code=exit_code,
        stdout_digest=sha256_digest({"stream": "stdout", "text": stdout}),
        stderr_digest=sha256_digest({"stream": "stderr", "text": stderr}),
    )


def verify_vercel_sandbox_conformance_run(
    spec: VercelSandboxConformanceSpec,
    run: VercelSandboxConformanceRun,
) -> bool:
    if run.spec_id != spec.spec_id or run.spec_digest != spec.digest:
        return False
    if (
        run.provider != VERCEL_SANDBOX_PROVIDER
        or run.repository_url != spec.repository_url
        or run.requested_revision != spec.revision
        or run.runtime != spec.runtime
        or not _evidence_matches_fixed_prefix(run.command_evidence)
    ):
        return False

    first_exit = run.command_evidence[0].exit_code
    if run.revision_verified != (first_exit == 0 and run.observed_revision == spec.revision):
        return False
    if len(run.command_evidence) < len(_fixed_commands()):
        if run.revision_verified and run.command_evidence[-1].exit_code == 0:
            return False

    expected_pass = (
        run.revision_verified
        and run.stopped
        and len(run.command_evidence) == len(_fixed_commands())
        and all(item.exit_code == 0 for item in run.command_evidence)
    )
    return run.all_passed == expected_pass


def run_vercel_sandbox_conformance(
    spec: VercelSandboxConformanceSpec,
    *,
    team_id: str | None = None,
    project_id: str | None = None,
    token: str | None = None,
    sandbox_factory: SandboxFactory | None = None,
) -> VercelSandboxConformanceRun:
    """Run the protocol-fixed General Execution conformance sequence in Vercel Sandbox.

    Credentials are used only to authenticate the sandbox provider and are never
    stored in the returned evidence. The caller cannot supply repository, runtime,
    or command argv beyond the exact Git revision encoded in ``spec``.
    """

    factory = sandbox_factory or _default_sandbox_factory
    sandbox = factory(spec, token, team_id, project_id)
    evidence: list[SandboxCommandEvidence] = []
    observed_revision: str | None = None
    revision_verified = False
    stopped = False
    stop_error_digest: str | None = None
    sandbox_id: str | None = None

    try:
        sandbox_id = _sandbox_id(sandbox)
        for command in _fixed_commands():
            result = sandbox.run_command(command.executable, list(command.args))
            if inspect.isawaitable(result):
                raise VercelSandboxConformanceError("sync conformance runner received asynchronous run_command result")
            exit_code, stdout, stderr = _command_result(result)
            item = _command_evidence(command, exit_code, stdout, stderr)
            evidence.append(item)

            if command.command_id == "verify_revision":
                candidate = stdout.strip()
                observed_revision = candidate if REVISION_PATTERN.fullmatch(candidate) else None
                revision_verified = exit_code == 0 and observed_revision == spec.revision
                if not revision_verified:
                    break
            elif exit_code != 0:
                break
    finally:
        try:
            # The pinned SDK defaults to a non-blocking stop request. Wait for
            # provider-confirmed termination before admitting clean shutdown.
            if "blocking" in inspect.signature(sandbox.stop).parameters:
                stop_result = sandbox.stop(blocking=True)
            else:
                stop_result = sandbox.stop()
            if inspect.isawaitable(stop_result):
                raise VercelSandboxConformanceError("sync conformance runner received asynchronous stop result")
            stopped = True
        except Exception as exc:
            stopped = False
            stop_error_digest = sha256_digest(
                {"error_type": type(exc).__name__, "message": str(exc)}
            )

    if sandbox_id is None:
        raise VercelSandboxConformanceError("Vercel Sandbox identity was not established")

    all_passed = (
        revision_verified
        and stopped
        and len(evidence) == len(_fixed_commands())
        and all(item.exit_code == 0 for item in evidence)
    )
    run = VercelSandboxConformanceRun(
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        provider=VERCEL_SANDBOX_PROVIDER,
        sandbox_id=sandbox_id,
        repository_url=spec.repository_url,
        requested_revision=spec.revision,
        observed_revision=observed_revision,
        runtime=spec.runtime,
        command_evidence=tuple(evidence),
        revision_verified=revision_verified,
        stopped=stopped,
        stop_error_digest=stop_error_digest,
        all_passed=all_passed,
        team_id=team_id,
        project_id=project_id,
    )
    if not verify_vercel_sandbox_conformance_run(spec, run):
        raise VercelSandboxConformanceError("constructed Vercel Sandbox conformance evidence did not verify")
    return run
