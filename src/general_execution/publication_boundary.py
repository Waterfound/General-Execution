"""Candidate public publication boundary. No private registry or live-host activation."""
from __future__ import annotations

import base64
import json
import re
from pathlib import PurePosixPath

RECEIPT_SCHEMA = "ge.public-proof-receipt.v1"
BLOCKED_ROOTS = frozenset({
    "runtime", "events", "authority", "human-decisions",
    "provider-inbox", "launch-orders", "private",
})
PRIVATE_FIELDS = frozenset({
    "portfolio", "portfolio_id", "work_id", "objective", "active_gate",
    "next_action_ref", "authority_boundary", "authority_grant",
    "approved_action_ref", "requested_action_ref", "dependency_graph",
    "fallback_graph", "canonical_refs", "private_key", "credential",
    "password", "seed_phrase",
})
DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")
SQLITE = b"SQLite format 3\x00"


class PublicEgressError(ValueError):
    def __init__(self, categories):
        self.categories = tuple(sorted(set(categories)))
        super().__init__("Public publication blocked: " + ",".join(self.categories))


def _private_fields(value):
    if isinstance(value, dict):
        return any(
            not isinstance(k, str)
            or k.lower() in PRIVATE_FIELDS
            or _private_fields(v)
            for k, v in value.items()
        )
    if isinstance(value, list):
        return any(_private_fields(item) for item in value)
    return False


def classify_public(path: str, data: bytes) -> tuple[str, ...]:
    """Return non-sensitive finding codes. Never report payloads or matched values."""
    codes = []
    if not isinstance(path, str) or not path or "\\" in path:
        return ("UNSAFE_PATH",)
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        codes.append("UNSAFE_PATH")
    if not p.parts or p.parts[0].lower() in BLOCKED_ROOTS:
        codes.append("PRIVATE_PATH")
    if path.lower().endswith((".sqlite.b64", ".db.b64", ".sqlite",
                              ".sqlite3", ".db", ".pem", ".key")):
        codes.append("PRIVATE_FILE_TYPE")
    if not isinstance(data, bytes):
        codes.append("INVALID_BODY")
        return tuple(sorted(set(codes)))
    if data.startswith(SQLITE):
        codes.append("SQLITE_STATE")
    if len(data) > 24:
        try:
            if base64.b64decode(data[:32]).startswith(SQLITE):
                codes.append("SQLITE_STATE")
        except Exception:
            pass
    if re.search(rb"\bwf[.](?:sys|cap)[.][A-Za-z0-9_.-]+", data):
        codes.append("STABLE_PRIVATE_ID")
    if re.search(rb"Waterfound/" + rb"Systems(?:/|\b)", data):
        codes.append("PRIVATE_REPO_REFERENCE")
    if path.endswith(".json"):
        try:
            obj = json.loads(data)
        except (UnicodeError, ValueError):
            codes.append("INVALID_JSON")
        else:
            if _private_fields(obj):
                codes.append("PRIVATE_SCHEMA")
    return tuple(sorted(set(codes)))


def admit_public(path: str, data: bytes) -> None:
    categories = classify_public(path, data)
    if categories:
        raise PublicEgressError(categories)


def minimal_public_receipt(evidence_digest: str, revision_digest: str,
                           status: str) -> bytes:
    """Construct a deterministic safe receipt; never serialize source payloads."""
    if not isinstance(evidence_digest, str) or not DIGEST.fullmatch(evidence_digest):
        raise PublicEgressError(("RECEIPT_INVALID",))
    if not isinstance(revision_digest, str) or not DIGEST.fullmatch(revision_digest):
        raise PublicEgressError(("RECEIPT_INVALID",))
    if status not in {"PASS", "FAIL", "WARN", "CONDITION_WAIT"}:
        raise PublicEgressError(("RECEIPT_INVALID",))
    result = {
        "schema_version": RECEIPT_SCHEMA,
        "evidence_digest": evidence_digest,
        "source_revision_digest": revision_digest,
        "status": status,
        "authority_created": False,
        "execution_triggered": False,
    }
    encoded = (json.dumps(result, sort_keys=True) + "\n").encode("utf-8")
    admit_public("public-receipts/receipt.json", encoded)
    return encoded
