from __future__ import annotations

import base64
import hashlib
import subprocess
from pathlib import Path

from .state_boundary import StateTransportReceipt
from .state_plane_host import StatePlaneHostError


class GitStatePlaneTransportError(StatePlaneHostError):
    pass


def _run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitStatePlaneTransportError(
            f"git state-plane operation failed with rc={result.returncode}"
        )
    return result.stdout.strip()


def _blob_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class GitStatePlaneTransport:
    """Provider-neutral Git transport for one opaque durable state blob.

    Remote locator and branch/root binding are supplied by the runtime
    environment. The transport never exposes them through the public receipt.
    """

    def __init__(
        self,
        *,
        remote: str,
        branch: str,
        root: str,
        state_ref: str,
        workdir: str | Path,
    ):
        if not remote or not branch or not root:
            raise GitStatePlaneTransportError("remote, branch and root are required")
        root_path = Path(root)
        if root_path.is_absolute() or ".." in root_path.parts:
            raise GitStatePlaneTransportError("root must be safe and relative")

        self.remote = remote
        self.branch = branch
        self.root = root_path
        self.state_ref = state_ref
        self.workdir = Path(workdir)
        self.checkout = self.workdir / "state-plane"
        self._head: str | None = None
        self._receipt: StateTransportReceipt | None = None

    @property
    def state_path(self) -> Path:
        return self.checkout / self.root / "state" / "state.sqlite.b64"

    def _checkout(self) -> None:
        if self.checkout.exists():
            raise GitStatePlaneTransportError("state-plane checkout already exists")
        _run("git", "clone", "--quiet", "--no-checkout", self.remote, str(self.checkout))
        _run("git", "fetch", "--quiet", "origin", self.branch, cwd=self.checkout)
        _run(
            "git",
            "checkout",
            "--quiet",
            "-B",
            "state-plane",
            f"origin/{self.branch}",
            cwd=self.checkout,
        )
        self._head = _run("git", "rev-parse", "HEAD", cwd=self.checkout)

    def load(self) -> tuple[StateTransportReceipt, bytes]:
        self._checkout()
        if not self.state_path.is_file():
            raise GitStatePlaneTransportError("state blob is missing")
        try:
            payload = base64.b64decode(self.state_path.read_text().strip(), validate=True)
        except Exception as exc:
            raise GitStatePlaneTransportError("state blob is not valid base64") from exc
        receipt = StateTransportReceipt(
            state_ref=self.state_ref,
            blob_digest=_blob_digest(payload),
            byte_count=len(payload),
            storage_visibility="private",
        )
        self._receipt = receipt
        return receipt, payload

    def commit(
        self,
        payload: bytes,
        *,
        expected_receipt_digest: str,
    ) -> StateTransportReceipt:
        if self._head is None or self._receipt is None:
            raise GitStatePlaneTransportError("load must precede commit")
        if expected_receipt_digest != self._receipt.digest:
            raise GitStatePlaneTransportError("stale state-plane receipt")

        remote_head = _run(
            "git",
            "ls-remote",
            self.remote,
            f"refs/heads/{self.branch}",
        ).split()[0]
        if remote_head != self._head:
            raise GitStatePlaneTransportError("state-plane remote advanced")

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(payload).decode("ascii") + "\n"
        self.state_path.write_text(encoded)

        _run("git", "config", "user.name", "durable-state-runtime", cwd=self.checkout)
        _run(
            "git",
            "config",
            "user.email",
            "durable-state-runtime@users.noreply.github.com",
            cwd=self.checkout,
        )
        _run("git", "add", "--", str(self.root), cwd=self.checkout)

        status = _run("git", "status", "--porcelain", cwd=self.checkout)
        if status:
            _run(
                "git",
                "commit",
                "--quiet",
                "-m",
                "state: advance opaque durable state",
                cwd=self.checkout,
            )
            result = subprocess.run(
                [
                    "git",
                    "push",
                    "--quiet",
                    "origin",
                    f"HEAD:refs/heads/{self.branch}",
                    f"--force-with-lease=refs/heads/{self.branch}:{self._head}",
                ],
                cwd=str(self.checkout),
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise GitStatePlaneTransportError("state-plane compare-and-swap failed")
            self._head = _run("git", "rev-parse", "HEAD", cwd=self.checkout)

        receipt = StateTransportReceipt(
            state_ref=self.state_ref,
            blob_digest=_blob_digest(payload),
            byte_count=len(payload),
            storage_visibility="private",
        )
        self._receipt = receipt
        return receipt
