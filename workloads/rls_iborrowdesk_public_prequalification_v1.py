#!/usr/bin/env python3
"""Keyless structural/coverage prequalification for the public IBorrowDesk API.

This worker intentionally does NOT emit fee or availability values. It records only
response hashes, schema keys, record counts, dates/month coverage, and whether fee and
availability coexist. It has no RLS admission authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION = "RLS-IBORROWDESK-PUBLIC-MIRROR-PREQUALIFICATION-v1"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
USER_AGENT = "RLS-Build-Colony-IBD-Prequalification/1.0 (public keyless structural research)"
BASE = "https://iborrowdesk.com/api/ticker"
PROBES = ("AAPL", "MSFT", "SPY", "IBM", "GE", "TSLA", "GME", "AMC", "TWTR", "ATVI", "XLNX", "BBBY", "FB", "META")
TARGET_FIRST = "2016-09"
TARGET_LAST = "2026-08"
OUTPUT = Path("artifacts/rls_iborrowdesk_public_prequalification_v1.json")
MAX_BYTES = 64 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def month_index(month: str) -> int:
    y, m = map(int, month.split("-"))
    return y * 12 + m - 1


def month_from_index(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def target_months() -> list[str]:
    return [month_from_index(i) for i in range(month_index(TARGET_FIRST), month_index(TARGET_LAST) + 1)]


def get_bytes(url: str) -> tuple[bytes, int, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise RuntimeError("response exceeds frozen 64 MiB ceiling")
        return raw, getattr(r, "status", 200), {k.lower(): v for k, v in r.headers.items()}


def normalize_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    # ISO date or datetime prefix.
    m = re.match(r"^(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        except ValueError:
            return None
    # Epoch-like strings are not interpreted at prequalification: no post-hoc unit guessing.
    return None


def list_schema(rows: object) -> dict[str, object]:
    if not isinstance(rows, list):
        return {"type": type(rows).__name__, "count": None, "record_keys": [], "fee_and_availability_coexist": False, "dates": []}
    keys = set()
    coexist = False
    dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys.update(str(k) for k in row.keys())
        lower = {str(k).lower() for k in row.keys()}
        if ("fee" in lower or "fee_rate" in lower or "feerate" in lower) and ("available" in lower or "availability" in lower):
            coexist = True
        for candidate in ("date", "reported", "timestamp", "time", "datetime", "updated_at"):
            if candidate in row:
                d = normalize_date(row.get(candidate))
                if d:
                    dates.append(d)
                    break
    return {
        "type": "list",
        "count": len(rows),
        "record_keys": sorted(keys),
        "fee_and_availability_coexist": coexist,
        "dates": dates,
    }


def summarize_payload(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        top_keys = sorted(str(k) for k in payload.keys())
        nested = {}
        all_dates = []
        coexist = False
        for key, value in payload.items():
            if isinstance(value, list):
                s = list_schema(value)
                nested[str(key)] = {k: v for k, v in s.items() if k != "dates"}
                all_dates.extend(s["dates"])
                coexist = coexist or bool(s["fee_and_availability_coexist"])
            elif isinstance(value, dict):
                nested[str(key)] = {"type": "dict", "keys": sorted(str(k) for k in value.keys())}
        dates = sorted(set(all_dates))
        months = sorted({d[:7] for d in dates})
        target = target_months()
        return {
            "json_type": "dict",
            "top_level_keys": top_keys,
            "nested_shapes": nested,
            "fee_and_availability_coexist_in_list_record": coexist,
            "earliest_parseable_date": dates[0] if dates else None,
            "latest_parseable_date": dates[-1] if dates else None,
            "distinct_parseable_dates": len(dates),
            "observed_months": months,
            "target_months_present": [m for m in target if m in set(months)],
            "target_month_count_present": sum(m in set(months) for m in target),
            "target_months_missing": [m for m in target if m not in set(months)],
        }
    if isinstance(payload, list):
        s = list_schema(payload)
        dates = sorted(set(s.pop("dates")))
        months = sorted({d[:7] for d in dates})
        return {
            "json_type": "list",
            "top_level_keys": [],
            "list_shape": s,
            "fee_and_availability_coexist_in_list_record": bool(s["fee_and_availability_coexist"]),
            "earliest_parseable_date": dates[0] if dates else None,
            "latest_parseable_date": dates[-1] if dates else None,
            "distinct_parseable_dates": len(dates),
            "observed_months": months,
        }
    return {"json_type": type(payload).__name__, "top_level_keys": [], "fee_and_availability_coexist_in_list_record": False}


def probe(url: str, label: str) -> dict[str, object]:
    out: dict[str, object] = {"label": label, "url": url, "status": "ERROR"}
    try:
        raw, status, headers = get_bytes(url)
        out.update({
            "status": "RETRIEVED",
            "http_status": status,
            "response_size": len(raw),
            "response_sha256": sha256(raw),
            "content_type": headers.get("content-type"),
        })
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            out.update({"json_valid": False, "json_error": str(exc)})
            return out
        out["json_valid"] = True
        out["shape"] = summarize_payload(payload)
    except urllib.error.HTTPError as exc:
        out.update({"status": "HTTP_ERROR", "http_status": exc.code, "error": f"HTTP {exc.code}"})
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    probes = []
    # Frozen current-universe endpoint first; metadata only.
    probes.append(probe(BASE, "CURRENT_UNIVERSE_ENDPOINT"))
    time.sleep(1.0)
    for symbol in PROBES:
        probes.append(probe(f"{BASE}/{symbol}", symbol))
        time.sleep(0.8)

    long_lived = {"AAPL", "MSFT", "SPY", "IBM", "GE", "TSLA"}
    reaches_start = []
    coexist = []
    for p in probes:
        shape = p.get("shape") if isinstance(p, dict) else None
        if not isinstance(shape, dict):
            continue
        if shape.get("fee_and_availability_coexist_in_list_record"):
            coexist.append(p["label"])
        earliest = shape.get("earliest_parseable_date")
        if p.get("label") in long_lived and isinstance(earliest, str) and earliest[:7] <= TARGET_FIRST:
            reaches_start.append(p["label"])

    inactive = {"TWTR", "ATVI", "XLNX", "BBBY"}
    inactive_results = {
        p["label"]: {
            "status": p.get("status"),
            "http_status": p.get("http_status"),
            "json_valid": p.get("json_valid"),
            "earliest": (p.get("shape") or {}).get("earliest_parseable_date") if isinstance(p.get("shape"), dict) else None,
            "latest": (p.get("shape") or {}).get("latest_parseable_date") if isinstance(p.get("shape"), dict) else None,
        }
        for p in probes if p.get("label") in inactive
    }

    prequal_pass = bool(reaches_start and coexist)
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "credential_policy": {"user_specific_credentials_used": False, "api_key_used": False, "account_login_used": False},
        "target_window": {"first_month": TARGET_FIRST, "last_month": TARGET_LAST, "required_months": len(target_months())},
        "frozen_probe_symbols": list(PROBES),
        "probes": probes,
        "prequalification_result": {
            "long_lived_probes_reaching_2016_09_or_earlier": reaches_start,
            "probes_with_fee_and_availability_coexisting": coexist,
            "inactive_or_acquired_probe_queryability": inactive_results,
            "prequalification_pass": prequal_pass,
            "admission_authority_granted": False,
            "economic_values_emitted": False,
            "next_gate_if_pass": "freeze provenance/time-normalization/PIT-identity authentication before comparing any economic values",
        },
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    print("probe_statuses=", [(p["label"], p["status"], p.get("http_status"), p.get("json_valid")) for p in probes])
    print("long_lived_probes_reaching_2016_09_or_earlier=", reaches_start)
    print("probes_with_fee_and_availability_coexisting=", coexist)
    print("inactive_or_acquired_probe_queryability=", inactive_results)
    print("prequalification_pass=", prequal_pass)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
