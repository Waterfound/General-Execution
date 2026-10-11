import base64
import json

import pytest

from general_execution.publication_boundary import (
    PublicEgressError, admit_public, classify_public, minimal_public_receipt,
)


def test_minimal_receipt_never_contains_operational_state():
    raw = minimal_public_receipt("sha256:" + "a" * 64, "sha256:" + "b" * 64, "PASS")
    obj = json.loads(raw)
    assert obj["status"] == "PASS"
    assert obj["authority_created"] is False
    assert obj["execution_triggered"] is False
    assert "objective" not in obj
    assert not classify_public("public-receipts/receipt.json", raw)


@pytest.mark.parametrize("path", [
    "runtime/state.sqlite.b64", "events/a.json", "authority/a.json",
    "human-decisions/a.json", "launch-orders/a.json",
    "provider-inbox/a.json", "private/a.json",
    "../sibling/receipt.json", "/absolute.json",
    "proof/ledger.sqlite", "proof/key.pem",
])
def test_private_storage_paths_rejected(path):
    assert classify_public(path, b"{}")


def test_raw_and_encoded_database_blocked():
    raw = b"SQLite format 3\x00" + b"\x00" * 250
    assert "SQLITE_STATE" in classify_public("public/x.txt", raw)
    assert "SQLITE_STATE" in classify_public("public/x.txt", base64.b64encode(raw))


@pytest.mark.parametrize("field", [
    "objective", "work_id", "authority_boundary", "next_action_ref",
    "portfolio", "fallback_graph", "canonical_refs", "credential",
])
def test_nested_operational_fields_rejected(field):
    data = json.dumps({"proof": [{"nested": {field: "dummy"}}]}).encode()
    assert "PRIVATE_SCHEMA" in classify_public("public/receipt.json", data)


def test_private_registry_identifier_rejected():
    marker = "wf." + "sys." + "dummy"
    assert "STABLE_PRIVATE_ID" in classify_public("public/sample.txt", marker.encode())


def test_private_repository_locator_rejected():
    marker = "Waterfound/" + "Systems" + "/something"
    assert "PRIVATE_REPO_REFERENCE" in classify_public("docs/sample.txt", marker.encode())


def test_no_raw_values_in_rejection():
    marker = "Waterfound/" + "Systems" + "/something"
    with pytest.raises(PublicEgressError) as e:
        admit_public("public/sample.txt", marker.encode())
    assert marker not in str(e.value)


def test_invalid_json_fails_closed():
    assert "INVALID_JSON" in classify_public("public/data.json", b"{bad")


def test_invalid_digest_rejected():
    with pytest.raises(PublicEgressError):
        minimal_public_receipt("sha256:wrong", "sha256:" + "b" * 64, "PASS")


def test_unknown_status_rejected():
    with pytest.raises(PublicEgressError):
        minimal_public_receipt("sha256:" + "a" * 64, "sha256:" + "b" * 64, "APPROVED")


def test_mechanism_source_can_remain_public():
    assert not classify_public("src/mechanism.py", b"def verify(): return True\n")
