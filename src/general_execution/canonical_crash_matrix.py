from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .canonical import sha256_digest
from .canonical_crash_worker import CRASH_EXIT_CODE, CUT_POINTS

CutPoint = Literal[
    "context_only",
    "prepared",
    "capacity_committed",
    "submission_unknown",
]

EXPECTED_DISPOSITION = {
    "context_only": "inert_orphan",
    "prepared": "inert_orphan",
    "capacity_committed": "begin_submission",
    "submission_unknown": "reconcile_provider",
}


class CanonicalCrashMatrixError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CrashWorkerEnvelope:
    phase: str
    process_token: str
    pid: int
    ppid: int
    payload: dict
    payload_digest: str
    returncode: int
    schema_version: str = "ge.crash-worker-envelope.v1"

    def __post_init__(self) -> None:
        if self.pid <= 0 or self.ppid <= 0:
            raise ValueError("worker process ids must be positive")
        if not self.process_token:
            raise ValueError("process token must be non-empty")
        if sha256_digest(self.payload) != self.payload_digest:
            raise ValueError("crash worker payload digest mismatch")


@dataclass(frozen=True, slots=True)
class CanonicalCrashCutPointEvidence:
    cut_point: CutPoint
    expected_disposition: str
    cut: CrashWorkerEnvelope
    recover: CrashWorkerEnvelope
    semantic_digest: str
    schema_version: str = "ge.canonical-crash-cut-point-evidence.v1"

    def __post_init__(self) -> None:
        if self.cut_point not in CUT_POINTS:
            raise ValueError("unsupported cut point")
        if self.expected_disposition != EXPECTED_DISPOSITION[self.cut_point]:
            raise ValueError("cut point expected disposition mismatch")
        if self.cut.returncode != CRASH_EXIT_CODE:
            raise ValueError("cut worker did not terminate via the crash exit code")
        if self.recover.returncode != 0:
            raise ValueError("recovery worker did not exit cleanly")
        if self.cut.pid == self.recover.pid or self.cut.process_token == self.recover.process_token:
            raise ValueError("cut and recovery must execute in distinct processes")
        if self.recover.payload.get("disposition") != self.expected_disposition:
            raise ValueError("recovery disposition does not match cut point")
        expected_semantic = sha256_digest(
            {
                "cut_point": self.cut_point,
                "context_id": self.cut.payload.get("context_id"),
                "invocation_id": self.cut.payload.get("invocation_id"),
                "disposition": self.recover.payload.get("disposition"),
                "recovery_action": self.recover.payload.get("recovery_action"),
                "active_binding_count": self.recover.payload.get("active_binding_count"),
            }
        )
        if self.semantic_digest != expected_semantic:
            raise ValueError("crash cut-point semantic digest mismatch")

    @property
    def evidence_digest(self) -> str:
        return sha256_digest(self)


def _source_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    root = _source_root()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = root if not current else os.pathsep.join((root, current))
    return env


def _parse_worker(completed: subprocess.CompletedProcess[str], phase: str) -> CrashWorkerEnvelope:
    try:
        body = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise CanonicalCrashMatrixError(f"{phase} worker did not emit valid JSON") from exc
    if not isinstance(body, dict) or body.get("schema_version") != "ge.canonical-crash-worker.v1":
        raise CanonicalCrashMatrixError(f"{phase} worker emitted unsupported schema")
    if body.get("phase") != phase:
        raise CanonicalCrashMatrixError(f"{phase} worker emitted the wrong phase")
    payload = body.get("payload")
    if not isinstance(payload, dict):
        raise CanonicalCrashMatrixError(f"{phase} worker payload must be an object")
    return CrashWorkerEnvelope(
        phase=phase,
        process_token=str(body["process_token"]),
        pid=int(body["pid"]),
        ppid=int(body["ppid"]),
        payload=payload,
        payload_digest=str(body["payload_digest"]),
        returncode=completed.returncode,
    )


def _invoke(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "general_execution.canonical_crash_worker", *arguments],
        shell=False,
        capture_output=True,
        text=True,
        env=_environment(),
        timeout=30,
        check=False,
    )


def run_process_crash_cut_point(
    root: str | Path,
    cut_point: CutPoint,
    *,
    suffix: str = "1",
) -> CanonicalCrashCutPointEvidence:
    if cut_point not in CUT_POINTS:
        raise CanonicalCrashMatrixError("unsupported cut point")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    capacity = root / "capacity.db"
    context = root / "context.db"
    dispatch = root / "dispatch.db"

    cut_completed = _invoke(
        [
            "cut",
            "--capacity", str(capacity),
            "--context", str(context),
            "--dispatch", str(dispatch),
            "--cut-point", cut_point,
            "--suffix", suffix,
        ]
    )
    if cut_completed.returncode != CRASH_EXIT_CODE:
        raise CanonicalCrashMatrixError(
            f"cut worker returned {cut_completed.returncode}, expected {CRASH_EXIT_CODE}: {cut_completed.stderr.strip()}"
        )
    cut = _parse_worker(cut_completed, "cut")

    recover_completed = _invoke(
        [
            "recover",
            "--capacity", str(capacity),
            "--context", str(context),
            "--dispatch", str(dispatch),
        ]
    )
    if recover_completed.returncode != 0:
        raise CanonicalCrashMatrixError(
            f"recovery worker failed with {recover_completed.returncode}: {recover_completed.stderr.strip()}"
        )
    recover = _parse_worker(recover_completed, "recover")

    if cut.pid == os.getpid() or recover.pid == os.getpid():
        raise CanonicalCrashMatrixError("crash matrix workers must not be the harness process")
    if cut.ppid != os.getpid() or recover.ppid != os.getpid():
        raise CanonicalCrashMatrixError("crash matrix workers must be direct harness children")

    semantic_digest = sha256_digest(
        {
            "cut_point": cut_point,
            "context_id": cut.payload.get("context_id"),
            "invocation_id": cut.payload.get("invocation_id"),
            "disposition": recover.payload.get("disposition"),
            "recovery_action": recover.payload.get("recovery_action"),
            "active_binding_count": recover.payload.get("active_binding_count"),
        }
    )
    return CanonicalCrashCutPointEvidence(
        cut_point=cut_point,
        expected_disposition=EXPECTED_DISPOSITION[cut_point],
        cut=cut,
        recover=recover,
        semantic_digest=semantic_digest,
    )


def run_process_crash_matrix(root: str | Path) -> tuple[CanonicalCrashCutPointEvidence, ...]:
    root = Path(root)
    return tuple(
        run_process_crash_cut_point(
            root / cut_point,
            cut_point,
            suffix=f"matrix-{cut_point}",
        )
        for cut_point in CUT_POINTS
    )
