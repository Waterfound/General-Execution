#!/usr/bin/env python3
"""Transport-only successor for frozen Common Crawl metadata discovery V1.2.2.

No semantic query, selection, source, date, threshold, or admission rule changes.
The parent run timed out before producing a manifest. V1.2.2a uses bounded
parallelism, shorter request timeouts, and bounded retries, then restores a
fully deterministic crawl-id ordering before evidence hashing.
"""
from __future__ import annotations

import json
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import rls_ibkr_community_zip_commoncrawl_v1_2_2 as v122

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-COMMONCRAWL-DISCOVERY-v1.2.2a"
OUTPUT = Path("artifacts/rls_ibkr_community_zip_commoncrawl_v1_2_2a.json")
MAX_WORKERS = 4
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = (1.0, 2.0)
RETRYABLE_HTTP = {429, 500, 502, 503, 504}

# Transport-only monkey patch: every index request gets an 8 second ceiling.
_original_get_bytes = v122.get_bytes

def get_bytes_fast(url: str, timeout: int = 8):
    return _original_get_bytes(url, timeout=8)

v122.get_bytes = get_bytes_fast


def query_with_retry(collection: dict[str, object]) -> dict[str, object]:
    last = None
    for attempt in range(RETRY_ATTEMPTS):
        result = v122.query_index(collection)
        last = result
        if result.get("status") in ("OK", "NO_MATCH"):
            result["attempts"] = attempt + 1
            return result
        http_status = result.get("http_status")
        retryable = result.get("status") == "ERROR" or http_status in RETRYABLE_HTTP
        if not retryable or attempt == RETRY_ATTEMPTS - 1:
            result["attempts"] = attempt + 1
            return result
        time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
    assert last is not None
    last["attempts"] = RETRY_ATTEMPTS
    return last


def main() -> int:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        collections = v122.selected_collections()
        coll_error = None
    except Exception as exc:
        collections = []
        coll_error = f"{type(exc).__name__}: {exc}"

    results_by_id: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(query_with_retry, row): str(row.get("id", "")) for row in collections}
        for future in as_completed(futures):
            cid = futures[future]
            try:
                results_by_id[cid] = future.result()
            except Exception as exc:
                results_by_id[cid] = {
                    "crawl_id": cid,
                    "status": "ERROR",
                    "http_status": None,
                    "rows": [],
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempts": RETRY_ATTEMPTS,
                }

    queries = []
    all_rows: list[dict[str, object]] = []
    for cid in sorted(results_by_id):
        q = results_by_id[cid]
        queries.append({
            "crawl_id": q["crawl_id"],
            "status": q["status"],
            "http_status": q["http_status"],
            "match_count": len(q.get("rows", [])),
            "attempts": q.get("attempts"),
            "error": q.get("error"),
        })
        all_rows.extend(q.get("rows", []))

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
        "authority": v122.AUTHORITY,
        "generated_at_utc": generated,
        "parent_protocol": "RLS-IBKR-COMMUNITY-ARCHIVE-COMMONCRAWL-CANDIDATE-v1.2.2",
        "transport_addendum": "RLS-IBKR-COMMUNITY-ARCHIVE-COMMONCRAWL-TRANSPORT-v1.2.2a",
        "parent_run": {"run_id": 35089044235, "outcome": "OPERATIONAL_TIMEOUT_NO_MANIFEST"},
        "frozen_query": {
            "target": v122.TARGET,
            "years": sorted(v122.YEARS),
            "http_status_required": "200",
            "selection_stage": "METADATA_ONLY",
            "collapse_key": "digest",
        },
        "transport": {
            "per_request_timeout_seconds": 8,
            "bounded_parallelism": MAX_WORKERS,
            "retry_attempts": RETRY_ATTEMPTS,
            "retry_backoff_seconds": list(RETRY_BACKOFF),
            "no_early_stop_on_match": True,
        },
        "current_archive_sha256": v122.CURRENT_ARCHIVE_SHA256,
        "credential_policy": {"user_specific_credentials_used": False, "api_key_used": False, "aws_login_used": False},
        "collinfo_error": coll_error,
        "collection_count": len(collections),
        "queries": queries,
        "raw_match_count": len(all_rows),
        "distinct_digest_count": len(distinct),
        "distinct_digests_in_selection_order": distinct,
        "rows_without_digest": no_digest,
        "archived_warc_or_zip_bytes_opened": False,
        "economic_values_opened": False,
        "admission_authority_granted": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = v122.stable_digest(stable)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    status_counts = {s: sum(1 for q in queries if q["status"] == s) for s in sorted({q["status"] for q in queries})}
    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    print("collection_count=", len(collections))
    print("query_status_counts=", status_counts)
    print("raw_match_count=", len(all_rows))
    print("distinct_digest_count=", len(distinct))
    print("distinct_digests_in_selection_order=", distinct)
    print("archived_warc_or_zip_bytes_opened=", False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
