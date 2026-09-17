from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace


def execution_frontier(manifest, ledger):
    return SimpleNamespace(ready=ledger.ready)


def append_event(manifest, ledger, *, package_id, role, event_type, payload=None):
    by_package = {package.package_id: package.domain_id for package in manifest.packages}
    domain_id = by_package[package_id]
    if domain_id not in ledger.ready:
        raise ValueError(f"package {domain_id} is not ready")
    event = {
        "package_id": package_id,
        "domain_id": domain_id,
        "role": role,
        "event_type": event_type,
        "payload": dict(payload or {}),
    }
    return replace(
        ledger,
        ready=tuple(item for item in ledger.ready if item != domain_id),
        events=ledger.events + (event,),
    )
