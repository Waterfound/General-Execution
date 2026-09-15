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


class CanonicalProcessHarnessError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalProcessWorkerResult:
    phase: WorkerPhase
    process_token: str
    pid: int
    ppid: int
    payload: dict
    payload_digest: str
    schema_version: str = "ge.canonical-process-worker-result.v1"

    def __post_init__(self) -> None:
        if self.phase not in {"prepare", "resume"}:
            raise ValueError("unsupported worker phase")
        if not self.process_token:
            raise ValueError("process token must be non-empty")
        if self.pid <= 0 or self.ppid <= 0:
            raise ValueError("worker process ids must be positive")
        if sha256_digest(self.payload) != self.payload_digest:
            raise ValueError("worker payload digest mismatch")


@dataclass(frozen=True, slots=True)
class CanonicalProcessSeparatedEvidence:
    parent_pid: int
    prepare: CanonicalProcessWorkerResult
    resume: CanonicalProcessWorkerResult
    preparation_digest: str
    recovery_digest: str
    context_id: str
    invocation_id: str
    recovery_action: str
    schema_version: str = "ge.canonical-process-separated-evidence.v1"

    def __post_init__(self) -> None:
        if self.parent_pid <= 0:
            raise ValueError("parent pid must be positive")
        if self.prepare.phase != "prepare" or self.resume.phase != "resume":
            raise ValueError("evidence requires prepare then resume")
        if self.prepare.pid == self.resume.pid:
            raise ValueError("prepare and resume must use different processes")
        if self.prepare.process_token == self.resume.process_token:
            raise ValueError("prepare and resume must use different process tokens")
        if self.prepare.pid == self.parent_pid or self.resume.pid == self.parent_pid:
            raise ValueError("workers must be distinct from the harness process")
        if self.prepare.ppid != self.parent_pid or self.resume.ppid != self.parent_pid:
            raise ValueError("workers must be direct children of the harness process")
        if self.recovery_action != "reconcile_provider":
            raise ValueError("process-separated recovery must preserve provider reconciliation")

    @property
    def semantic_digest(self) -> str:
        return sha256_digest(
            {
                "preparation_digest": self.preparation_digest,
                "recovery_digest": self.recovery_digest,
                "context_id": self.context_id,
                "invocation_id": self.invocation_id,
                "recovery_action": self.recovery_action,
            }
        )

    @property
    def evidence_digest(self) -> str:
        return sha256_digest(self)


def _source_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def _worker_environment() -> dict[str, str]:
    env = os.environ.copy()
    root = _source_root()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = root if not current else os.pathsep.join((root, current))
    return env


def _run_worker(arguments: list[str], expected_phase: WorkerPhase) -> CanonicalProcessWorkerResult:
    completed = subprocess.run(
        [sys.executable, "-m", "general_execution.canonical_process_worker", *arguments],
        shell=False,
        capture_output=True,
        text=True,
        env=_worker_environment(),
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise CanonicalProcessHarnessError(
            f"{expected_phase} worker failed with exit code {completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        body = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise CanonicalProcessHarnessError(f"{expected_phase} worker did not emit valid JSON") from exc
    if not isinstance(body, dict) or body.get("schema_version") != "ge.canonical-process-worker.v1":
        raise CanonicalProcessHarnessError(f"{expected_phase} worker returned unsupported schema")
    if body.get("phase") != expected_phase:
        raise CanonicalProcessHarnessError(f"{expected_phase} worker returned the wrong phase")
    payload = body.get("payload")
    if not isinstance(payload, dict):
        raise CanonicalProcessHarnessError(f"{expected_phase} worker payload must be an object")
    return CanonicalProcessWorkerResult(
        phase=expected_phase,
        process_token=str(body["process_token"]),
        pid=int(body["pid"]),
        ppid=int(body["ppid"]),
        payload=payload,
        payload_digest=str(body["payload_digest"]),
    )


def run_process_separated_canonical_cold_recovery(
    root: str | Path,
    *,
    suffix: str = "1",
) -> CanonicalProcessSeparatedEvidence:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    capacity = root / "capacity.db"
    context = root / "context.db"
    dispatch = root / "dispatch.db"

    prepare = _run_worker(
        [
            "prepare",
            "--capacity", str(capacity),
            "--context", str(context),
            "--dispatch", str(dispatch),
            "--suffix", suffix,
        ],
        "prepare",
    )

    # The preparation interpreter has exited before this worker starts.
    resume = _run_worker(
        [
            "resume",
            "--capacity", str(capacity),
            "--context", str(context),
            "--dispatch", str(dispatch),
        ],
        "resume",
    )

    receipt = prepare.payload.get("receipt")
    report = resume.payload.get("report")
    if not isinstance(receipt, dict) or not isinstance(report, dict):
        raise CanonicalProcessHarnessError("worker protocol is missing receipt/report objects")
    if receipt.get("context_id") != report.get("context_id"):
        raise CanonicalProcessHarnessError("resume did not reconstruct the prepared context")
    if receipt.get("invocation_id") != report.get("invocation_id"):
        raise CanonicalProcessHarnessError("resume did not reconstruct the prepared invocation")
    if report.get("context_mode") != "cold_reconstructed":
        raise CanonicalProcessHarnessError("resume did not prove cold reconstructed context")
    if report.get("blind_resubmissions_authorized") != 0 or report.get("provider_outcomes_inferred") != 0:
        raise CanonicalProcessHarnessError("resume widened cold-recovery authority")

    return CanonicalProcessSeparatedEvidence(
        parent_pid=os.getpid(),
        prepare=prepare,
        resume=resume,
        preparation_digest=str(prepare.payload["receipt_digest"]),
        recovery_digest=str(resume.payload["report_digest"]),
        context_id=str(report["context_id"]),
        invocation_id=str(report["invocation_id"]),
        recovery_action=str(report["recovery_action"]),
    )
