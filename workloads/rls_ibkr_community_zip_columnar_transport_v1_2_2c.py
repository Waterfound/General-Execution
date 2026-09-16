#!/usr/bin/env python3
"""Anonymous Common Crawl shard discovery + HTTPS Parquet transport for RLS.

OBSERVATION ONLY. Zero RLS admission authority.

V1.2.2c corrects only the physical transport mistake from V1.2.2b: HTTP does not
expand a wildcard. This worker anonymously lists public Common Crawl object metadata,
constructs explicit HTTPS Parquet URLs, and runs the same frozen metadata-only query.
It never reads WARC response bodies, ZIP bodies, securities rows, economic values, or
return/performance data.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import duckdb

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-COLUMNAR-TRANSPORT-v1.2.2c"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
CRAWL_ID = "CC-MAIN-2021-17"
TARGET_DOMAIN = "potential-investments.com"
TARGET_PATH = "/ib_shorting.zip"
FETCH_STATUS = 200
MAX_ROWS = 100
BUCKET_LIST_BASE = "https://commoncrawl.s3.amazonaws.com/"
HTTPS_DATA_BASE = "https://data.commoncrawl.org/"
PREFIX = f"cc-index/table/cc-main/warc/crawl={CRAWL_ID}/subset=warc/"
MAX_LIST_PAGES = 4
MAX_OBJECTS = 1000
MAX_SHARDS = 500
OUTPUT = Path("artifacts/rls_ibkr_community_zip_columnar_transport_v1_2_2c.json")
USER_AGENT = "RLS-Build-Colony-CC-Columnar/1.2.2c (anonymous metadata-only)"


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def fetch_xml(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise RuntimeError("anonymous listing response exceeds frozen 8 MiB ceiling")
        return data


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def list_public_shards() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    objects: list[dict[str, object]] = []
    pages: list[dict[str, object]] = []
    token: str | None = None
    for page_no in range(1, MAX_LIST_PAGES + 1):
        params = {"list-type": "2", "prefix": PREFIX, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        url = BUCKET_LIST_BASE + "?" + urllib.parse.urlencode(params)
        raw = fetch_xml(url)
        root = ET.fromstring(raw)
        page_objects = []
        next_token = None
        truncated = False
        for child in root:
            name = strip_ns(child.tag)
            if name == "Contents":
                item: dict[str, object] = {}
                for field in child:
                    key = strip_ns(field.tag)
                    text = field.text or ""
                    if key == "Key": item["key"] = text
                    elif key == "Size": item["size"] = int(text or "0")
                    elif key == "ETag": item["etag"] = text.strip('"')
                    elif key == "LastModified": item["last_modified"] = text
                page_objects.append(item)
            elif name == "IsTruncated":
                truncated = (child.text or "").lower() == "true"
            elif name == "NextContinuationToken":
                next_token = child.text
        objects.extend(page_objects)
        pages.append({
            "page": page_no,
            "request_url_sha256": hashlib.sha256(url.encode()).hexdigest(),
            "object_count": len(page_objects),
            "is_truncated": truncated,
            "next_token_present": bool(next_token),
        })
        if len(objects) > MAX_OBJECTS:
            raise RuntimeError("anonymous shard listing exceeded frozen 1000-object ceiling")
        if not truncated:
            break
        if not next_token:
            raise RuntimeError("listing is truncated without continuation token")
        token = next_token
    else:
        raise RuntimeError("anonymous shard listing exceeded frozen page ceiling")

    shards = []
    for obj in objects:
        key = str(obj.get("key", ""))
        if not key.startswith(PREFIX):
            raise RuntimeError("listing returned object outside frozen prefix")
        if key.endswith(".parquet"):
            shards.append(obj)
    shards.sort(key=lambda x: str(x.get("key", "")))
    if not shards:
        raise RuntimeError("no parquet shards found under frozen prefix")
    if len(shards) > MAX_SHARDS:
        raise RuntimeError(f"parquet shard count {len(shards)} exceeds frozen {MAX_SHARDS} ceiling")
    return shards, pages


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def row_dicts(cursor) -> list[dict[str, object]]:
    cols = [d[0] for d in cursor.description]
    rows = []
    for raw in cursor.fetchall():
        item: dict[str, object] = {}
        for key, value in zip(cols, raw):
            if isinstance(value, datetime):
                value = value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.replace(tzinfo=timezone.utc).isoformat()
            item[key] = value
        rows.append(item)
    return rows


def main() -> int:
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "phase": "A_TRANSPORT_FEASIBILITY_ONLY",
        "frozen_crawl_id": CRAWL_ID,
        "frozen_target": {
            "url_host_registered_domain": TARGET_DOMAIN,
            "url_path": TARGET_PATH,
            "fetch_status": FETCH_STATUS,
            "max_rows": MAX_ROWS,
        },
        "credential_policy": {
            "aws_account_login_used": False,
            "aws_access_key_used": False,
            "aws_secret_key_used": False,
            "request_signing_used": False,
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
        "listing": {"status": "NOT_ATTEMPTED"},
        "query": {"status": "NOT_ATTEMPTED", "rows": []},
    }

    try:
        shards, pages = list_public_shards()
        shard_meta = [
            {"key": x["key"], "size": x.get("size"), "etag": x.get("etag"), "last_modified": x.get("last_modified")}
            for x in shards
        ]
        manifest["listing"] = {
            "status": "SUCCEEDED",
            "prefix": PREFIX,
            "page_count": len(pages),
            "pages": pages,
            "parquet_shard_count": len(shards),
            "shards_sha256": digest(shard_meta),
            "first_shard_key": shard_meta[0]["key"],
            "last_shard_key": shard_meta[-1]["key"],
        }

        urls = [HTTPS_DATA_BASE + str(x["key"]) for x in shards]
        files_sql = "[" + ",".join(quote_sql(u) for u in urls) + "]"
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
          AND fetch_status = {FETCH_STATUS}
        ORDER BY fetch_time, url, content_digest
        LIMIT {MAX_ROWS}
        """
        con = duckdb.connect(database=":memory:")
        con.execute("SET threads=4")
        con.execute("SET memory_limit='3GB'")
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
        if manifest["listing"].get("status") == "NOT_ATTEMPTED":
            manifest["listing"] = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
        else:
            manifest["query"] = {"status": "ERROR", "rows": [], "error": f"{type(exc).__name__}: {exc}"}

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
    print("listing_status=", manifest["listing"].get("status"))
    print("parquet_shard_count=", manifest["listing"].get("parquet_shard_count"))
    print("shards_sha256=", manifest["listing"].get("shards_sha256"))
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
