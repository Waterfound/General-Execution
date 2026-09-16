#!/usr/bin/env python3
"""Common Crawl metadata-only discovery for historical versions of ib_shorting.zip.

Observation only. No archived WARC/ZIP bytes are opened in this stage and no RLS
admission authority is granted. The URL, crawl years, metadata fields and digest
selection rule were frozen privately before this worker was executed.
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

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-COMMONCRAWL-DISCOVERY-v1.2.2"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
USER_AGENT = "RLS-Build-Colony-CC-ZIP-Discovery/1.2.2 (public metadata only)"
OUTPUT = Path("artifacts/rls_ibkr_community_zip_commoncrawl_v1_2_2.json")
COLLINFO = "https://index.commoncrawl.org/collinfo.json"
TARGET = "potential-investments.com/ib_shorting.zip"
YEARS = {str(y) for y in range(2017, 2025)}
ALLOWED_FIELDS = ("url", "timestamp", "status", "mime", "digest", "length", "offset", "filename")
CURRENT_ARCHIVE_SHA256 = "e920f31b44254fc3633d610e621159a834bca90ed2b51b19d46046edb1d90724"
MAX_INDEX_RESPONSE = 8 * 1024 * 1024
SLEEP = 1.15


def get_bytes(url: str, timeout: int = 35) -> tuple[bytes, int]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(MAX_INDEX_RESPONSE + 1)
        if len(raw) > MAX_INDEX_RESPONSE:
            raise RuntimeError("index response exceeds frozen 8 MiB ceiling")
        return raw, getattr(response, "status", 200)


def get_json(url: str) -> object:
    raw, _ = get_bytes(url)
    return json.loads(raw)


def selected_collections() -> list[dict[str, object]]:
    payload = get_json(COLLINFO)
    rows = payload if isinstance(payload, list) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id", ""))
        if not cid.startswith("CC-MAIN-"):
            continue
        year = cid[len("CC-MAIN-"):len("CC-MAIN-") + 4]
        if year in YEARS:
            out.append(row)
    return sorted(out, key=lambda r: str(r.get("id", "")))


def query_index(row: dict[str, object]) -> dict[str, object]:
    cid = str(row.get("id", ""))
    api = str(row.get("cdx-api") or f"https://index.commoncrawl.org/{cid}-index")
    params = urllib.parse.urlencode({"url": TARGET, "output": "json", "matchType": "exact"})
    url = api + ("&" if "?" in api else "?") + params
    result: dict[str, object] = {"crawl_id": cid, "query_url": url, "status": "ERROR", "http_status": None, "rows": [], "error": None}
    try:
        raw, status = get_bytes(url)
        parsed = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            if str(item.get("status", "")) != "200":
                continue
            compact = {field: item.get(field) for field in ALLOWED_FIELDS}
            compact["crawl_id"] = cid
            parsed.append(compact)
        result.update({"status": "OK", "http_status": status, "rows": parsed})
    except urllib.error.HTTPError as exc:
        result.update({"status": "NO_MATCH" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "error": None if exc.code == 404 else f"HTTP {exc.code}"})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def stable_digest(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        collections = selected_collections()
        coll_error = None
    except Exception as exc:
        collections = []
        coll_error = f"{type(exc).__name__}: {exc}"

    queries = []
    all_rows: list[dict[str, object]] = []
    for collection in collections:
        q = query_index(collection)
        queries.append({
            "crawl_id": q["crawl_id"],
            "status": q["status"],
            "http_status": q["http_status"],
            "match_count": len(q["rows"]),
            "error": q["error"],
        })
        all_rows.extend(q["rows"])
        time.sleep(SLEEP)

    all_rows.sort(key=lambda x: (str(x.get("timestamp", "")), str(x.get("crawl_id", ""))))
    first_by_digest: dict[str, dict[str, object]] = {}
    no_digest: list[dict[str, object]] = []
    for row in all_rows:
        digest = str(row.get("digest") or "")
        if not digest:
            no_digest.append(row)
            continue
        first_by_digest.setdefault(digest, row)
    distinct = sorted(first_by_digest.values(), key=lambda x: str(x.get("timestamp", "")))

    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": generated,
        "frozen_query": {
            "target": TARGET,
            "years": sorted(YEARS),
            "http_status_required": "200",
            "selection_stage": "METADATA_ONLY",
            "collapse_key": "digest",
        },
        "current_archive_sha256": CURRENT_ARCHIVE_SHA256,
        "credential_policy": {"user_specific_credentials_used": False, "api_key_used": False, "aws_login_used": False},
        "collinfo_error": coll_error,
        "collection_count": len(collections),
        "queries": queries,
        "raw_match_count": len(all_rows),
        "distinct_digest_count": len(distinct),
        "distinct_digests_in_selection_order": distinct,
        "rows_without_digest": no_digest,
        "archived_warc_or_zip_bytes_opened": False,
        "admission_authority_granted": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = stable_digest(stable)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    print("collection_count=", len(collections))
    print("query_status_counts=", {s: sum(1 for q in queries if q["status"] == s) for s in sorted({q["status"] for q in queries})})
    print("raw_match_count=", len(all_rows))
    print("distinct_digest_count=", len(distinct))
    print("distinct_digests_in_selection_order=", distinct)
    print("archived_warc_or_zip_bytes_opened=", False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
