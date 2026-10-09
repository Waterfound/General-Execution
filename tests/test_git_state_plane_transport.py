from __future__ import annotations

import base64
import subprocess

import pytest

from general_execution.git_state_plane_transport import (
    GitStatePlaneTransport,
    GitStatePlaneTransportError,
)


def sh(*args, cwd=None):
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_remote(tmp_path):
    seed = tmp_path / "seed"
    remote = tmp_path / "remote.git"
    seed.mkdir()
    sh("git", "init", "-q", cwd=seed)
    sh("git", "config", "user.name", "fixture", cwd=seed)
    sh("git", "config", "user.email", "fixture@example.invalid", cwd=seed)
    target = seed / "opaque" / "state"
    target.mkdir(parents=True)
    (target / "state.sqlite.b64").write_text(
        base64.b64encode(b"initial-state").decode("ascii") + "\n"
    )
    sh("git", "add", ".", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    sh("git", "branch", "-M", "state", cwd=seed)
    sh("git", "init", "--bare", "-q", str(remote))
    sh("git", "remote", "add", "origin", str(remote), cwd=seed)
    sh("git", "push", "-q", "origin", "state", cwd=seed)
    return remote


def make_transport(remote, workdir):
    return GitStatePlaneTransport(
        remote=str(remote),
        branch="state",
        root="opaque",
        state_ref="s_1234567890abcdef",
        workdir=workdir,
    )


def test_roundtrip_and_cas(tmp_path):
    remote = make_remote(tmp_path)
    first = make_transport(remote, tmp_path / "first")
    receipt, payload = first.load()
    assert payload == b"initial-state"
    updated = first.commit(b"next-state", expected_receipt_digest=receipt.digest)

    second = make_transport(remote, tmp_path / "second")
    observed, payload = second.load()
    assert payload == b"next-state"
    assert observed == updated


def test_stale_remote_fails_closed(tmp_path):
    remote = make_remote(tmp_path)
    left = make_transport(remote, tmp_path / "left")
    right = make_transport(remote, tmp_path / "right")
    left_receipt, _ = left.load()
    right_receipt, _ = right.load()

    left.commit(b"winner", expected_receipt_digest=left_receipt.digest)

    with pytest.raises(GitStatePlaneTransportError, match="remote advanced"):
        right.commit(b"loser", expected_receipt_digest=right_receipt.digest)


def test_wrong_receipt_fails_before_write(tmp_path):
    remote = make_remote(tmp_path)
    item = make_transport(remote, tmp_path / "item")
    item.load()
    with pytest.raises(GitStatePlaneTransportError, match="stale state-plane receipt"):
        item.commit(
            b"wrong",
            expected_receipt_digest="sha256:" + "0" * 64,
        )
