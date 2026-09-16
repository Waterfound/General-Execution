#!/usr/bin/env python3
"""Discover historical public versions of the frozen IBKR community ZIP.

Observation only. No RLS admission authority. This stage queries archive metadata only;
it does not download archived ZIP bytes. Its sole purpose is to determine whether a
subsequent, already-frozen raw-version retrieval has something deterministic to fetch.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-VERSION-DISCOVERY-v1.2.1"
USER_AGENT = "RLS-Build-Colony-ZIP-Version-Discovery/1.2.1 (public evidence)"
OUTPUT = Path("artifacts/rls_ibkr_community_zip_versions_v1_2_1.json")
URL_VARIANTS = (
    "http://potential-investments.com/ib_shorting.zip",
    "https://potential-investments.com/ib_shorting.zip",
    "http://www.potential-investments.com/ib_shorting.zip",
    "https://www.potential-investments.com/ib_shorting.zip",
)
CDX = "https://web.archive.org/cdx/search/cdx"
FROM = "20170401"
TO = "20240630"
CURRENT_ARCHIVE_SHA256 = "e920f31b44254fc3633d610e621159a834bca90ed2b51b19d46046edb1d90724"


def sha256_json(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise RuntimeError("CDX response exceeds frozen 8 MiB ceiling")
        return json.loads(raw)


def rows_from_payload(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, list) or not payload:
        return []
    if isinstance(payload[0], list):
        header = payload[0]
        if not all(isinstance(x, str) for x in header):
            return []
        return [dict(zip(header, row)) for row in payload[1:] if isinstance(row, list)]
    return [x for x in payload if isinstance(x, dict)]


def query_variant(original: str) -> dict[str, object]:
    params = {
        "url": original,
        "output": "json",
        "from": FROM,
        "to": TO,
        "filter": "statuscode:200",
        "fl": "timestamp,original,statuscode,digest,length,mimetype",
        "collapse": "digest",
    }
    url = CDX + "?" + urllib.parse.urlencode(params)
    try:
        payload = fetch_json(url)
        rows = rows_from_payload(payload)
        rows.sort(key=lambda x: x.get("timestamp", ""))
        return {"original": original, "query_url": url, "status": "OK", "rows": rows, "error": None}
    except urllib.error.HTTPError as exc:
        return {"original": original, "query_url": url, "status": "HTTP_ERROR", "rows": [], "error": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"original": original, "query_url": url, "status": "ERROR", "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    variants = []
    for original in URL_VARIANTS:
        variants.append(query_variant(original))
        time.sleep(1.5)

    unique: dict[tuple[str, str], dict[str, str]] = {}
    for v in variants:
        for row in v["rows"]:
            key = (str(row.get("timestamp", "")), str(row.get("digest", "")))
            unique[key] = row
    captures = [unique[k] for k in sorted(unique)]

    distinct_digests = []
    seen = set()
    for row in captures:
        digest = row.get("digest")
        if digest and digest not in seen:
            seen.add(digest)
            distinct_digests.append({
                "timestamp": row.get("timestamp"),
                "original": row.get("original"),
                "digest": digest,
                "length": row.get("length"),
                "mimetype": row.get("mimetype"),
            })

    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "query_window": {"from": FROM, "to": TO},
        "current_archive_sha256": CURRENT_ARCHIVE_SHA256,
        "variants": variants,
        "unique_capture_count": len(captures),
        "distinct_digest_count": len(distinct_digests),
        "distinct_digests_in_selection_order": distinct_digests,
        "raw_archived_zip_bytes_opened": False,
        "user_specific_credentials_used": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = sha256_json(stable)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    print("variant_statuses=", [(v["original"], v["status"], len(v["rows"]), v["error"]) for v in variants])
    print("unique_capture_count=", len(captures))
    print("distinct_digest_count=", len(distinct_digests))
    print("distinct_digests_in_selection_order=", distinct_digests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
