from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from enum import Enum


class RunManifest:
    pass


def _normal(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _normal(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _normal(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normal(item) for item in value]
    return value


def sha256_digest(value):
    payload = json.dumps(_normal(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
