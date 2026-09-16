#!/usr/bin/env python3
"""Deterministic public-catalog Common Crawl transport for RLS.

OBSERVATION ONLY. Zero RLS admission authority.

No object listing and no AWS credentials are used. Physical Parquet shard names for
CC-MAIN-2021-17 are frozen before execution from public indexed catalog evidence:
300 partitions, indexes 00000..00299, UUID 74237c22-0523-49c6-9e5a-6b4aa471a042.
The worker constructs all HTTPS URLs deterministically and executes only the frozen
metadata query. It never opens WARC/ZIP bodies, securities rows, economic values, or
return/performance data.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import duckdb

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-CATALOG-TRANSPORT-v1.2.2e"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
CRAWL_ID = "CC-MAIN-2021-17"
PARTITION_COUNT = 300
SHARD_UUID = "74237c22-0523-49c6-9e5a-6b4aa471a042"
PREFIX = f"cc-index/table/cc-main/warc/crawl={CRAWL_ID}/subset=warc/"
HTTPS_BASE = "https://data.commoncrawl.org/"
TARGET_DOMAIN = "potential-investments.com"
TARGET_PATH = "/ib_shorting.zip"
MAX_ROWS = 100
OUTPUT = Path("artifacts/rls_ibkr_community_zip_catalog_transport_v1_2_2e.json")
USER_AGENT = "RLS-Build-Colony-CC-Catalog/1.2.2e (metadata-only public research)"


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def shard_key(index: int) -> str:
    return PREFIX + f"part-{index:05d}-{SHARD_UUID}.c000.gz.parquet"


def head_metadata(url: str) -> dict[str, object]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return {
                "status": getattr(response, "status", 200),
                "content_length": response.headers.get("Content-Length"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "error": None,
            }
    except Exception as exc:
        return {
            "status": None,
            "content_length": None,
            "etag": None,
            "last_modified": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def row_dicts(cursor) -> list[dict[str, object]]:
    names = [d[0] for d in cursor.description]
    out = []
    for row in cursor.fetchall():
        record: dict[str, object] = {}
        for name, value in zip(names, row):
            if isinstance(value, datetime):
                value = value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.replace(tzinfo=timezone.utc).isoformat()
            record[name] = value
        out.append(record)
    return out


def main() -> int:
    keys = [shard_key(i) for i in range(PARTITION_COUNT)]
    urls = [HTTPS_BASE + key for key in keys]
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "phase": "A_TRANSPORT_FEASIBILITY_ONLY",
        "frozen_crawl_id": CRAWL_ID,
        "catalog": {
            "partition_count": PARTITION_COUNT,
            "first_partition_index": 0,
            "last_partition_index": PARTITION_COUNT - 1,
            "shard_uuid": SHARD_UUID,
            "keys_sha256": digest(keys),
            "first_key": keys[0],
            "last_key": keys[-1],
            "object_listing_used": False,
        },
        "credential_policy": {
            "aws_account_login_used": False,
            "aws_access_key_used": False,
            "aws_secret_key_used": False,
            "aws_session_token_used": False,
            "request_signing_used": False,
            "api_key_used": False,
            "user_specific_credentials_used": False,
        },
        "frozen_target": {
            "url_host_registered_domain": TARGET_DOMAIN,
            "url_path": TARGET_PATH,
            "fetch_status": 200,
            "max_rows": MAX_ROWS,
        },
        "boundaries": {
            "warc_bodies_opened": False,
            "zip_bodies_opened": False,
            "securities_rows_opened": False,
            "economic_values_opened": False,
            "return_or_performance_data_opened": False,
            "admission_authority_granted": False,
        },
        "catalog_endpoint_probes": {},
        "query": {"status": "NOT_ATTEMPTED", "rows": []},
    }

    manifest["catalog_endpoint_probes"] = {
        "first": head_metadata(urls[0]),
        "middle": head_metadata(urls[PARTITION_COUNT // 2]),
        "last": head_metadata(urls[-1]),
    }

    try:
        failed_probes = [k for k, v in manifest["catalog_endpoint_probes"].items() if v.get("status") != 200]
        if failed_probes:
            raise RuntimeError(f"frozen shard catalog endpoint probe failed: {failed_probes}")

        files_sql = "[" + ",".join(quote_sql(url) for url in urls) + "]"
        query = f"""
        SELECT
          url,
          fetch_time,
          fetch_status,
          content_mime_type,
          content_digest,
          warc_filename,
          warc_record_offset,
          warc_record_length
        FROM read_parquet({files_sql}, hive_partitioning=true)
        WHERE url_host_registered_domain = ?
          AND url_path = ?
          AND fetch_status = 200
        ORDER BY fetch_time, url, content_digest
        LIMIT {MAX_ROWS}
        """
        con = duckdb.connect(database=":memory:")
        con.execute("SET threads=6")
        con.execute("SET memory_limit='4GB'")
        try:
            con.execute("LOAD httpfs")
            httpfs = "LOADED"
        except Exception:
            con.execute("INSTALL httpfs")
            con.execute("LOAD httpfs")
            httpfs = "INSTALLED_AND_LOADED"
        cursor = con.execute(query, [TARGET_DOMAIN, TARGET_PATH])
        rows = row_dicts(cursor)
        manifest["query"] = {
            "status": "EXECUTED",
            "duckdb_version": duckdb.__version__,
            "httpfs": httpfs,
            "row_count": len(rows),
            "rows": rows,
            "rows_sha256": digest(rows),
            "error": None,
        }
        success = True
    except Exception as exc:
        success = False
        manifest["query"] = {
            "status": "ERROR",
            "rows": [],
            "row_count": None,
            "rows_sha256": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    manifest["result"] = {
        "transport_success": success,
        "phase_b_authorized_by_transport_gate": success,
        "match_presence_observed": ((manifest["query"].get("row_count") or 0) > 0) if success else None,
        "zero_rows_if_any_do_not_prove_absence": True,
        "admission_authority_granted": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = digest(stable)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    print("worker_version=", WORKER_VERSION)
    print("partition_count=", PARTITION_COUNT)
    print("keys_sha256=", manifest["catalog"]["keys_sha256"])
    print("catalog_endpoint_probes=", manifest["catalog_endpoint_probes"])
    print("query_status=", manifest["query"].get("status"))
    print("row_count=", manifest["query"].get("row_count"))
    print("rows_sha256=", manifest["query"].get("rows_sha256"))
    print("query_error=", manifest["query"].get("error"))
    print("transport_success=", success)
    print("phase_b_authorized_by_transport_gate=", manifest["result"]["phase_b_authorized_by_transport_gate"])
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
