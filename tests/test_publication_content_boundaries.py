import base64
import pytest

from general_execution.publication_boundary import classify_public


@pytest.mark.parametrize("path", ["proof/receipt.JSON", "proof/receipt.txt", "proof/receipt"])
def test_private_json_cannot_bypass_by_renaming(path):
    assert "PRIVATE_SCHEMA" in classify_public(path, b'{"nested": {"objective": "synthetic"}}')


def test_uppercase_json_invalid_is_rejected():
    assert "INVALID_JSON" in classify_public("proof/receipt.JSON", b"{bad")


@pytest.mark.parametrize("prefix", [b"\n", b" \t\n", b"\r\n"])
def test_whitespace_wrapped_encoded_sqlite_is_rejected(prefix):
    raw = b"SQLite format 3\x00" + b"\x00" * 256
    assert "SQLITE_STATE" in classify_public("proof/receipt.txt", prefix + base64.b64encode(raw))


def test_json_with_utf8_bom_private_fields_is_rejected():
    assert "PRIVATE_SCHEMA" in classify_public("proof/receipt.txt", b'\xef\xbb\xbf{"token":"synthetic"}')


def test_deep_json_fails_with_safe_category():
    assert "INVALID_JSON" in classify_public("proof/receipt.json", b"[" * 2000 + b"0" + b"]" * 2000)
