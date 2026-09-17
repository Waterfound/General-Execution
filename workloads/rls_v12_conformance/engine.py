from hashlib import sha256
import json


class ValidationError(ValueError):
    """Raised when an RLS decision package violates a fail-closed invariant."""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_json_sha256(value: object) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()
