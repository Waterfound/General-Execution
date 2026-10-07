from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Mapping, Any


INPUT_SCHEMA = "ge.operator-plane-input.v1"
PROJECTION_SCHEMA = "ge.operator-plane-projection.v1"
REVISION = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")


def _nonempty(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _revision(label: str, value: object) -> str:
    text = _nonempty(label, value)
    if not REVISION.fullmatch(text):
        raise ValueError(f"{label} must be an exact lowercase 40-hex revision")
    return text


def _digest(label: str, value: object) -> str:
    text = _nonempty(label, value)
    if not DIGEST.fullmatch(text):
        raise ValueError(f"{label} must be sha256:<64-hex>")
    return text


def _strings(label: str, value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    return list(value)


def _exact(data: object, allowed: set[str], required: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be an object")
    unknown = set(data) - allowed
    missing = required - set(data)
    if unknown or missing:
        raise ValueError(f"{label} fields mismatch: missing={sorted(missing)} unknown={sorted(unknown)}")
    return data


def _source(raw: object) -> dict[str, object]:
    fields = {"source_id", "system", "repository", "revision", "artifact_ref", "artifact_digest"}
    data = _exact(raw, fields, fields, "source")
    return {
        "source_id": _nonempty("source.source_id", data["source_id"]),
        "system": _nonempty("source.system", data["system"]),
        "repository": _nonempty("source.repository", data["repository"]),
        "revision": _revision("source.revision", data["revision"]),
        "artifact_ref": _nonempty("source.artifact_ref", data["artifact_ref"]),
        "artifact_digest": _digest("source.artifact_digest", data["artifact_digest"]),
    }


def _gate(raw: object | None) -> dict[str, str] | None:
    if raw is None:
        return None
    fields = {"kind", "ref", "reason"}
    data = _exact(raw, fields, fields, "blocking_gate")
    return {key: _nonempty(f"blocking_gate.{key}", data[key]) for key in sorted(fields)}


def _lane(raw: object, source_by_id: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    required = {
        "lane_id", "workstream_id", "owner_system", "repository", "source_revision",
        "state", "observed_at", "source_refs", "evidence_refs",
    }
    allowed = required | {"current_frontier", "executor", "dispatch_identity", "blocking_gate"}
    data = _exact(raw, allowed, required, "lane")
    lane = {
        "lane_id": _nonempty("lane.lane_id", data["lane_id"]),
        "workstream_id": _nonempty("lane.workstream_id", data["workstream_id"]),
        "owner_system": _nonempty("lane.owner_system", data["owner_system"]),
        "repository": _nonempty("lane.repository", data["repository"]),
        "source_revision": _revision("lane.source_revision", data["source_revision"]),
        "state": _nonempty("lane.state", data["state"]),
        "observed_at": _nonempty("lane.observed_at", data["observed_at"]),
        "source_refs": _strings("lane.source_refs", data["source_refs"]),
        "evidence_refs": _strings("lane.evidence_refs", data["evidence_refs"]),
        "current_frontier": (
            _nonempty("lane.current_frontier", data["current_frontier"])
            if data.get("current_frontier") is not None else None
        ),
        "executor": (
            _nonempty("lane.executor", data["executor"])
            if data.get("executor") is not None else None
        ),
        "dispatch_identity": (
            _nonempty("lane.dispatch_identity", data["dispatch_identity"])
            if data.get("dispatch_identity") is not None else None
        ),
        "blocking_gate": _gate(data.get("blocking_gate")),
    }
    if not lane["source_refs"]:
        raise ValueError("lane.source_refs must bind at least one exact source")
    for source_id in lane["source_refs"]:
        source = source_by_id.get(source_id)
        if source is None:
            raise ValueError(f"lane references unknown source: {source_id}")
        if source["repository"] == lane["repository"] and source["revision"] != lane["source_revision"]:
            raise ValueError("lane source revision conflicts with bound repository source")
    if not any(
        source_by_id[source_id]["repository"] == lane["repository"]
        and source_by_id[source_id]["revision"] == lane["source_revision"]
        for source_id in lane["source_refs"]
    ):
        raise ValueError("lane lacks exact source binding for its repository revision")
    return lane


def build_operator_projection(raw: Mapping[str, Any]) -> dict[str, object]:
    required = {"schema_version", "portfolio_id", "observed_at", "sources", "lanes"}
    data = _exact(raw, required, required, "operator-plane input")
    if data["schema_version"] != INPUT_SCHEMA:
        raise ValueError("unsupported operator-plane input schema")
    portfolio_id = _nonempty("portfolio_id", data["portfolio_id"])
    observed_at = _nonempty("observed_at", data["observed_at"])
    if not isinstance(data["sources"], list) or not data["sources"]:
        raise ValueError("sources must be a non-empty list")
    if not isinstance(data["lanes"], list):
        raise ValueError("lanes must be a list")

    sources = [_source(item) for item in data["sources"]]
    source_ids = [str(item["source_id"]) for item in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source_id values must be unique")
    artifact_refs = [str(item["artifact_ref"]) for item in sources]
    if len(artifact_refs) != len(set(artifact_refs)):
        raise ValueError("source artifact_ref values must be unique")
    source_by_id = {str(item["source_id"]): item for item in sources}

    lanes = [_lane(item, source_by_id) for item in data["lanes"]]
    lane_ids = [str(item["lane_id"]) for item in lanes]
    if len(lane_ids) != len(set(lane_ids)):
        raise ValueError("lane_id values must be unique")

    ordered_sources = sorted(sources, key=lambda item: str(item["source_id"]))
    ordered_lanes = sorted(lanes, key=lambda item: str(item["lane_id"]))
    status_counts = dict(sorted(Counter(str(item["state"]) for item in ordered_lanes).items()))
    timeline = [
        {
            "observed_at": lane["observed_at"],
            "lane_id": lane["lane_id"],
            "state": lane["state"],
            "current_frontier": lane["current_frontier"],
        }
        for lane in sorted(ordered_lanes, key=lambda item: (str(item["observed_at"]), str(item["lane_id"])))
    ]

    return {
        "schema_version": PROJECTION_SCHEMA,
        "portfolio_id": portfolio_id,
        "observed_at": observed_at,
        "source_bindings": deepcopy(ordered_sources),
        "lanes": deepcopy(ordered_lanes),
        "timeline": timeline,
        "summary": {
            "lane_count": len(ordered_lanes),
            "state_counts": status_counts,
            "blocking_gate_count": sum(1 for item in ordered_lanes if item["blocking_gate"] is not None),
        },
        "authority_created": False,
        "execution_triggered": False,
        "mutable_state_owned": False,
    }


def render_operator_projection(projection: Mapping[str, object]) -> str:
    if projection.get("schema_version") != PROJECTION_SCHEMA:
        raise ValueError("not a governed operator-plane projection")
    lines = [
        "Governed Operator Plane",
        "",
        f"Portfolio: {projection['portfolio_id']}",
        f"Observed: {projection['observed_at']}",
    ]
    lanes = projection.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("projection lanes must be a list")
    for lane in lanes:
        if not isinstance(lane, Mapping):
            raise ValueError("projection lane must be an object")
        gate = lane.get("blocking_gate")
        gate_text = "none"
        if isinstance(gate, Mapping):
            gate_text = f"{gate.get('kind')}:{gate.get('ref')}"
        executor = lane.get("executor") or "none"
        revision = str(lane.get("source_revision") or "")
        lines.append(
            f"- {lane.get('lane_id')} | {lane.get('state')} | "
            f"frontier={lane.get('current_frontier') or 'none'} | "
            f"executor={executor} | gate={gate_text} | rev={revision[:12]}"
        )
    lines.extend([
        "",
        "Read-only: authority_created=false; execution_triggered=false; mutable_state_owned=false",
    ])
    return "\n".join(lines)
