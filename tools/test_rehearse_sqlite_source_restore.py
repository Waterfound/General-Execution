"""Generic negative fixtures. Never use production or private state as a test."""
import base64
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "sqlite_rehearsal", Path(__file__).with_name("rehearse_sqlite_source_restore.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


@pytest.fixture
def source_fixture(tmp_path):
    db = tmp_path / "synthetic.sqlite"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE synthetic (id INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO synthetic VALUES (1)")
    c.commit()
    c.close()
    raw = db.read_bytes()
    return base64.b64encode(raw), {
        "database_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "authority_created": False,
    }


def test_recover_and_reopen_in_independent_process(source_fixture):
    encoded, manifest = source_fixture
    receipt = _mod.verify_snapshot(encoded, manifest)
    assert receipt["independent_process_cold_open"] == "PASS"
    assert receipt["sqlite_integrity_check"] == "PASS"
    assert receipt["private_host_restoration_proven"] is False
    assert "synthetic" not in json.dumps(receipt)


def test_digest_mismatch_fails_closed(source_fixture):
    encoded, manifest = source_fixture
    manifest["database_sha256"] = "sha256:" + "a" * 64
    with pytest.raises(ValueError, match="SOURCE_DIGEST_MISMATCH"):
        _mod.verify_snapshot(encoded, manifest)


def test_invalid_base64_fails_closed(source_fixture):
    _, manifest = source_fixture
    with pytest.raises(ValueError, match="INVALID_ENCODING"):
        _mod.verify_snapshot(b"not_base64!", manifest)


def test_privilege_claim_rejected(source_fixture):
    encoded, manifest = source_fixture
    manifest["authority_created"] = True
    with pytest.raises(ValueError, match="UNAUTHORIZED_SNAPSHOT"):
        _mod.verify_snapshot(encoded, manifest)


def test_truncated_sqlite_fails_integrity_or_identity(source_fixture):
    encoded, manifest = source_fixture
    raw = base64.b64decode(encoded)
    short = raw[:100]
    manifest["database_sha256"] = "sha256:" + hashlib.sha256(short).hexdigest()
    with pytest.raises(ValueError):
        _mod.verify_snapshot(base64.b64encode(short), manifest)


def test_invalid_sha_syntax_rejected(source_fixture):
    encoded, manifest = source_fixture
    manifest["database_sha256"] = "sha256:" + "Z" * 64
    with pytest.raises(ValueError, match="INVALID_MANIFEST_DIGEST"):
        _mod.verify_snapshot(encoded, manifest)
