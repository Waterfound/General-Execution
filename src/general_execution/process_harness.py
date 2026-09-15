from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .canonical import sha256_digest

WorkerPhase = Literal["prepare", "resume"]


class ProcessHarnessError(ValueError):
    pass


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must contain 64 hexadecimal characters") from exc


@dataclass(frozen=True, slots=True)
class ProcessWorkerResult:
    phase: WorkerPhase
    process_token: str
    pid: int
    ppid: int
    payload: dict
    payload_digest: str
    schema_version: str = "ge.process-worker-result.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.process-worker-result.v1":
            raise ValueError("unsupported process worker result schema")
        if self.phase not in {"prepare", "resume"}:
            raise ValueError("unsupported process worker phase")
        if not self.process_token or not self.process_token.strip():
            raise ValueError("process_token must be non-empty")
        if self.pid <= 0 or self.ppid <= 0:
            raise ValueError("worker process ids must be positive")
        _require_sha256("payload_digest", self.payload_digest)
        if sha256_digest(self.payload) != self.payload_digest:
            raise ValueError("worker payload digest mismatch")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ProcessSeparatedRecoveryReport:
    parent_pid: int
    prepare: ProcessWorkerResult
    resume: ProcessWorkerResult
    cold_report_digest: str
    context_digest: str
    outcome_digest: str
    result_digest: str | None
    schema_version: str = "ge.process-separated-recovery-report.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ge.process-separated-recovery-report.v1":
            raise ValueError("unsupported process-separated recovery report schema")
        if self.parent_pid <= 0:
            raise ValueError("parent_pid must be positive")
        if self.prepare.phase != "prepare" or self.resume.phase != "resume":
            raise ValueError("process-separated report requires prepare then resume workers")
        if self.prepare.process_token == self.resume.process_token:
            raise ValueError("prepare and resume must be distinct worker processes")
        if self.prepare.pid == self.parent_pid or self.resume.pid == self.parent_pid:
            raise ValueError("recovery workers must not be the harness process")
        if self.prepare.ppid != self.parent_pid or self.resume.ppid != self.parent_pid:
            raise ValueError("recovery workers must be direct children of the harness process")
        for name in ("cold_report_digest", "context_digest", "outcome_digest"):
            _require_sha256(name, getattr(self, name))
        if self.result_digest is not None:
            _require_sha256("result_digest", self.result_digest)
        resume_payload = self.resume.payload
        if resume_payload.get("report_digest") != self.cold_report_digest:
            raise ValueError("resume payload does not bind cold report digest")
        if resume_payload.get("context_digest") != self.context_digest:
            raise ValueError("resume payload does not bind reconstructed context digest")
        if resume_payload.get("outcome_digest") != self.outcome_digest:
            raise ValueError("resume payload does not bind outcome digest")
        if resume_payload.get("result_digest") != self.result_digest:
            raise ValueError("resume payload does not bind result digest")
        report = resume_payload.get("report")
        if not isinstance(report, dict) or report.get("context_mode") != "cold_reconstructed":
            raise ValueError("resume worker did not prove cold reconstructed context")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _source_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    root = _source_root()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = root if not existing else os.pathsep.join((root, existing))
    return env


def _run_worker(arguments: list[str], expected_phase: WorkerPhase) -> ProcessWorkerResult:
    command = [sys.executable, "-m", "general_execution.process_worker", *arguments]
    completed = subprocess.run(
        command,
        shell=False,
        capture_output=True,
        text=True,
        env=_worker_env(),
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise ProcessHarnessError(
            f"{expected_phase} worker failed with exit code {completed.returncode}: {completed.stderr.strip()}"
        )
    stdout = completed.stdout.strip()
    try:
        body = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ProcessHarnessError(f"{expected_phase} worker did not return one JSON object") from exc
    if not isinstance(body, dict) or body.get("schema_version") != "ge.process-recovery-worker.v1":
        raise ProcessHarnessError(f"{expected_phase} worker returned unsupported protocol")
    if body.get("phase") != expected_phase:
        raise ProcessHarnessError(f"{expected_phase} worker returned wrong phase")
    payload = body.get("payload")
    if not isinstance(payload, dict):
        raise ProcessHarnessError(f"{expected_phase} worker payload must be an object")
    return ProcessWorkerResult(
        phase=expected_phase,
        process_token=str(body["process_token"]),
        pid=int(body["pid"]),
        ppid=int(body["ppid"]),
        payload=payload,
        payload_digest=str(body["payload_digest"]),
    )


def run_process_separated_cold_recovery(
    root: str | Path,
    *,
    terminal_kind: Literal["timed_out", "completed"] = "timed_out",
    suffix: str = "1",
) -> ProcessSeparatedRecoveryReport:
    if terminal_kind not in {"timed_out", "completed"}:
        raise ProcessHarnessError("terminal_kind must be timed_out or completed")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    capacity = root / "capacity.db"
    context = root / "context.db"
    provider = root / "provider.db"

    prepare = _run_worker(
        [
            "prepare",
            "--capacity", str(capacity),
            "--context", str(context),
            "--provider", str(provider),
            "--suffix", suffix,
        ],
        "prepare",
    )

    # subprocess.run has already waited for and reaped the preparation interpreter.
    resume = _run_worker(
        [
            "resume",
            "--capacity", str(capacity),
            "--context", str(context),
            "--provider", str(provider),
            "--terminal-kind", terminal_kind,
        ],
        "resume",
    )

    payload = resume.payload
    return ProcessSeparatedRecoveryReport(
        parent_pid=os.getpid(),
        prepare=prepare,
        resume=resume,
        cold_report_digest=str(payload["report_digest"]),
        context_digest=str(payload["context_digest"]),
        outcome_digest=str(payload["outcome_digest"]),
        result_digest=(str(payload["result_digest"]) if payload["result_digest"] is not None else None),
    )
