#!/usr/bin/env python3
"""Credential-free metadata-only discovery for the original 2019 IBKR archive share.

OBSERVATION ONLY. Zero RLS admission authority. This worker searches public archive
indexes for the exact historical share id gRd3kH. It does not fetch archived page,
ZIP, or securities-data payload bodies.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION = "RLS-IBKR-ORIGINAL-GOFILE-ARCHIVE-DISCOVERY-v1"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
OUTPUT = Path("artifacts/rls_ibkr_original_gofile_archive_discovery_v1.json")
SHARE_ID = "gRd3kH"
EXACT_ORIGINAL = "https://gofile.io/?c=gRd3kH"
TARGET_PATTERNS = (
    "gofile.io/?c=gRd3kH",
    "www.gofile.io/?c=gRd3kH",
    "gofile.io/*gRd3kH*",
    "www.gofile.io/*gRd3kH*",
)
YEARS = {"2019", "2020", "2021"}
USER_AGENT = "RLS-Build-Colony-Gofile-Metadata/1.0 (credential-free public research)"
TIMEOUT = 12
MAX_BYTES = 8 * 1024 * 1024
MAX_WORKERS = 4


def stable_digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def get_bytes(url: str, timeout: int = TIMEOUT) -> tuple[bytes, int]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError("metadata response exceeds frozen 8 MiB ceiling")
    return data, status


def commoncrawl_collections() -> tuple[list[dict[str, object]], str | None]:
    try:
        raw, _ = get_bytes("https://index.commoncrawl.org/collinfo.json")
        payload = json.loads(raw)
        out = []
        for row in payload if isinstance(payload, list) else []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("id", ""))
            if cid.startswith("CC-MAIN-") and cid[8:12] in YEARS:
                out.append(row)
        out.sort(key=lambda x: str(x.get("id", "")))
        return out, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def query_cc(collection: dict[str, object], pattern: str) -> dict[str, object]:
    cid = str(collection.get("id", ""))
    api = str(collection.get("cdx-api") or f"https://index.commoncrawl.org/{cid}-index")
    params = {"url": pattern, "output": "json", "filter": "status:200"}
    url = api + ("&" if "?" in api else "?") + urllib.parse.urlencode(params)
    try:
        raw, status = get_bytes(url)
        rows = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            rows.append({k: obj.get(k) for k in ("url", "timestamp", "status", "mime", "digest", "length", "offset", "filename", "redirect")})
        return {"crawl_id": cid, "pattern": pattern, "status": "OK" if rows else "NO_MATCH", "http_status": status, "rows": rows, "error": None}
    except urllib.error.HTTPError as exc:
        return {"crawl_id": cid, "pattern": pattern, "status": "NO_MATCH" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "rows": [], "error": None if exc.code == 404 else str(exc)}
    except Exception as exc:
        return {"crawl_id": cid, "pattern": pattern, "status": "ERROR", "http_status": None, "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def query_wayback(pattern: str) -> dict[str, object]:
    params = {
        "url": pattern,
        "output": "json",
        "from": "2019",
        "to": "2021",
        "fl": "timestamp,original,statuscode,digest,length,mimetype,redirect",
        "filter": "statuscode:200",
        "collapse": "digest",
    }
    url = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(params)
    try:
        raw, status = get_bytes(url)
        payload = json.loads(raw)
        rows = []
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            header = payload[0]
            for row in payload[1:]:
                if isinstance(row, list):
                    rows.append(dict(zip(header, row)))
        return {"pattern": pattern, "status": "OK" if rows else "NO_MATCH", "http_status": status, "rows": rows, "error": None}
    except urllib.error.HTTPError as exc:
        return {"pattern": pattern, "status": "HTTP_ERROR", "http_status": exc.code, "rows": [], "error": str(exc)}
    except Exception as exc:
        return {"pattern": pattern, "status": "ERROR", "http_status": None, "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def query_arquivo(pattern: str) -> dict[str, object]:
    params = {"url": pattern, "from": "2019", "to": "2021", "output": "json"}
    url = "https://arquivo.pt/wayback/-cdx?" + urllib.parse.urlencode(params)
    try:
        raw, status = get_bytes(url)
        text = raw.decode("utf-8", "replace")
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return {"pattern": pattern, "status": "OK" if rows else "NO_MATCH", "http_status": status, "row_count": len(rows), "rows": rows[:100], "error": None}
    except urllib.error.HTTPError as exc:
        return {"pattern": pattern, "status": "HTTP_ERROR", "http_status": exc.code, "row_count": 0, "rows": [], "error": str(exc)}
    except Exception as exc:
        return {"pattern": pattern, "status": "ERROR", "http_status": None, "row_count": 0, "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    collections, coll_error = commoncrawl_collections()
    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for collection in collections:
            for pattern in TARGET_PATTERNS:
                tasks.append(pool.submit(query_cc, collection, pattern))
        cc_results = [future.result() for future in as_completed(tasks)]
    cc_results.sort(key=lambda x: (str(x.get("crawl_id")), str(x.get("pattern"))))

    # These are metadata-only index queries; no archived object body is opened.
    wayback = [query_wayback(pattern) for pattern in TARGET_PATTERNS]
    arquivo = [query_arquivo(pattern) for pattern in TARGET_PATTERNS]

    cc_rows = []
    for result in cc_results:
        cc_rows.extend(result.get("rows", []))
    wb_rows = []
    for result in wayback:
        wb_rows.extend(result.get("rows", []))
    aq_rows = []
    for result in arquivo:
        aq_rows.extend(result.get("rows", []))

    def unique_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        seen = set()
        out = []
        for row in rows:
            key = (str(row.get("timestamp", "")), str(row.get("url") or row.get("original") or ""), str(row.get("digest", "")))
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        out.sort(key=lambda x: (str(x.get("timestamp", "")), str(x.get("url") or x.get("original") or "")))
        return out

    unique_cc = unique_rows(cc_rows)
    unique_wb = unique_rows(wb_rows)
    unique_aq = unique_rows(aq_rows)
    all_meta = unique_rows(unique_cc + unique_wb + unique_aq)

    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "frozen_share_id": SHARE_ID,
        "exact_original_url": EXACT_ORIGINAL,
        "query_patterns": list(TARGET_PATTERNS),
        "credential_policy": {"user_specific_credentials_used": False, "api_key_used": False, "provider_login_used": False},
        "archive_body_bytes_opened": False,
        "securities_rows_opened": False,
        "economic_values_opened": False,
        "common_crawl": {"collection_count": len(collections), "collinfo_error": coll_error, "queries": cc_results, "unique_metadata_rows": unique_cc},
        "wayback": {"queries": wayback, "unique_metadata_rows": unique_wb},
        "arquivo_pt": {"queries": arquivo, "unique_metadata_rows": unique_aq},
        "summary": {
            "unique_metadata_capture_count": len(all_meta),
            "captures": all_meta,
            "success_condition_met": len(all_meta) > 0,
            "payload_selection_performed": False,
            "payload_bytes_opened": False,
            "admission_authority_granted": False
        }
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = stable_digest(stable)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("worker_version=", WORKER_VERSION)
    print("common_crawl_collection_count=", len(collections))
    print("common_crawl_unique_metadata_rows=", len(unique_cc))
    print("wayback_unique_metadata_rows=", len(unique_wb))
    print("arquivo_unique_metadata_rows=", len(unique_aq))
    print("unique_metadata_capture_count=", len(all_meta))
    print("success_condition_met=", len(all_meta) > 0)
    print("capture_summary=", [{k: row.get(k) for k in ("timestamp", "url", "original", "status", "statuscode", "mime", "mimetype", "digest", "length", "redirect")} for row in all_meta])
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
