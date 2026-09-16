#!/usr/bin/env python3
"""Credential-free Common Crawl Columnar transport feasibility for RLS.

OBSERVATION ONLY. Zero RLS admission authority.

This worker implements only the frozen transport successor V1.2.2b. It queries one
predeclared Common Crawl Parquet partition over public HTTPS with DuckDB predicate
pushdown. It never opens WARC records, ZIP bodies, securities rows, economic values,
or return/performance data.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-COLUMNAR-TRANSPORT-v1.2.2b"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
CRAWL_ID = "CC-MAIN-2021-17"
BASE = "https://data.commoncrawl.org/cc-index/table/cc-main/warc"
PARQUET_GLOB = f"{BASE}/crawl={CRAWL_ID}/subset=warc/*.parquet"
TARGET_DOMAIN = "potential-investments.com"
TARGET_PATH = "/ib_shorting.zip"
MAX_ROWS = 100
OUTPUT = Path("artifacts/rls_ibkr_community_zip_columnar_transport_v1_2_2b.json")

QUERY = f"""
SELECT
    url,
    fetch_time,
    fetch_status,
    content_mime_type,
    content_digest,
    warc_filename,
    warc_record_offset,
    warc_record_length
FROM read_parquet('{PARQUET_GLOB}', hive_partitioning = true)
WHERE url_host_registered_domain = ?
  AND url_path = ?
  AND fetch_status = 200
ORDER BY fetch_time, url, content_digest
LIMIT {MAX_ROWS}
"""


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def sha256(obj: object) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def row_to_dict(columns: list[str], row: tuple[object, ...]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in zip(columns, row):
        if isinstance(value, datetime):
            value = value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.replace(tzinfo=timezone.utc).isoformat()
        out[key] = value
    return out


def main() -> int:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": generated,
        "phase": "A_TRANSPORT_FEASIBILITY_ONLY",
        "frozen_crawl_id": CRAWL_ID,
        "frozen_target": {
            "url_host_registered_domain": TARGET_DOMAIN,
            "url_path": TARGET_PATH,
            "fetch_status": 200,
            "max_rows": MAX_ROWS,
        },
        "transport": {
            "engine": "DuckDB",
            "duckdb_version": duckdb.__version__,
            "scheme": "HTTPS",
            "parquet_glob": PARQUET_GLOB,
            "aws_account_required": False,
            "aws_credentials_used": False,
            "api_key_used": False,
            "user_specific_credentials_used": False,
        },
        "boundaries": {
            "warc_bodies_opened": False,
            "zip_bodies_opened": False,
            "securities_rows_opened": False,
            "economic_values_opened": False,
            "return_or_performance_data_opened": False,
            "admission_authority_granted": False,
        },
        "query": {
            "status": "NOT_ATTEMPTED",
            "row_count": None,
            "rows": [],
            "rows_sha256": None,
            "error": None,
        },
    }

    try:
        con = duckdb.connect(database=":memory:")
        con.execute("SET threads=2")
        con.execute("SET memory_limit='2GB'")
        # DuckDB autoloads httpfs for https:// remote reads. Explicit LOAD is
        # attempted only to make the transport state observable.
        try:
            con.execute("LOAD httpfs")
            httpfs = "LOADED"
        except Exception:
            con.execute("INSTALL httpfs")
            con.execute("LOAD httpfs")
            httpfs = "INSTALLED_AND_LOADED"
        manifest["transport"]["httpfs"] = httpfs

        cursor = con.execute(QUERY, [TARGET_DOMAIN, TARGET_PATH])
        columns = [d[0] for d in cursor.description]
        rows = [row_to_dict(columns, row) for row in cursor.fetchall()]
        manifest["query"] = {
            "status": "EXECUTED",
            "row_count": len(rows),
            "rows": rows,
            "rows_sha256": sha256(rows),
            "error": None,
        }
        transport_success = True
    except Exception as exc:
        manifest["query"] = {
            "status": "ERROR",
            "row_count": None,
            "rows": [],
            "rows_sha256": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
        transport_success = False

    manifest["result"] = {
        "transport_success": transport_success,
        "match_presence_observed": (manifest["query"].get("row_count") or 0) > 0 if transport_success else None,
        "zero_rows_if_any_do_not_prove_absence": True,
        "phase_b_authorized_by_transport_gate": transport_success,
        "admission_authority_granted": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = sha256(stable)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    print("worker_version=", WORKER_VERSION)
    print("duckdb_version=", duckdb.__version__)
    print("crawl_id=", CRAWL_ID)
    print("transport_success=", transport_success)
    print("query_status=", manifest["query"]["status"])
    print("row_count=", manifest["query"]["row_count"])
    print("rows_sha256=", manifest["query"]["rows_sha256"])
    print("query_error=", manifest["query"]["error"])
    print("phase_b_authorized_by_transport_gate=", manifest["result"]["phase_b_authorized_by_transport_gate"])
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
