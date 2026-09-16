#!/usr/bin/env python3
"""Unsigned Common Crawl shard listing + HTTPS Parquet query for RLS.

OBSERVATION ONLY. Zero RLS admission authority.

Uses the Common Crawl documented AWS CLI --no-sign-request mode only to enumerate
public Parquet object names. The subprocess environment removes credential variables.
If listing succeeds, named objects are read over HTTPS by DuckDB using the unchanged
metadata-only target query. No WARC, ZIP, securities, economic, or return data bodies
are opened.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb

WORKER_VERSION = "RLS-IBKR-COMMUNITY-ZIP-COLUMNAR-TRANSPORT-v1.2.2d"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
CRAWL_ID = "CC-MAIN-2021-17"
PREFIX = f"cc-index/table/cc-main/warc/crawl={CRAWL_ID}/subset=warc/"
TARGET_DOMAIN = "potential-investments.com"
TARGET_PATH = "/ib_shorting.zip"
MAX_ROWS = 100
MAX_SHARDS = 500
HTTPS_BASE = "https://data.commoncrawl.org/"
OUTPUT = Path("artifacts/rls_ibkr_community_zip_columnar_transport_v1_2_2d.json")

CREDENTIAL_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
)


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def sha256(obj: object) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def sanitized_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in CREDENTIAL_ENV_KEYS:
        env.pop(key, None)
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    env["AWS_DEFAULT_REGION"] = "us-east-1"
    return env


def unsigned_list() -> tuple[list[dict[str, object]], dict[str, object]]:
    command = [
        "aws", "s3api", "list-objects-v2",
        "--bucket", "commoncrawl",
        "--prefix", PREFIX,
        "--max-items", "1000",
        "--output", "json",
        "--no-sign-request",
        "--region", "us-east-1",
    ]
    proc = subprocess.run(
        command,
        env=sanitized_env(),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    meta = {
        "command_shape": "aws s3api list-objects-v2 --bucket commoncrawl --prefix <FROZEN_PREFIX> --max-items 1000 --output json --no-sign-request --region us-east-1",
        "exit_code": proc.returncode,
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
        "stderr_tail": proc.stderr[-2000:],
        "credential_environment_removed": list(CREDENTIAL_ENV_KEYS),
        "request_signing_disabled": True,
    }
    if proc.returncode != 0:
        raise RuntimeError(f"unsigned listing exited {proc.returncode}: {proc.stderr[-1200:]}")
    payload = json.loads(proc.stdout)
    contents = payload.get("Contents") or []
    if not isinstance(contents, list):
        raise RuntimeError("unsigned listing returned non-list Contents")
    shards = []
    for item in contents:
        if not isinstance(item, dict):
            continue
        key = str(item.get("Key", ""))
        if not key.startswith(PREFIX):
            raise RuntimeError("unsigned listing returned object outside frozen prefix")
        if key.endswith(".parquet"):
            shards.append({
                "key": key,
                "size": item.get("Size"),
                "etag": str(item.get("ETag", "")).strip('"') or None,
                "last_modified": str(item.get("LastModified", "")) or None,
            })
    shards.sort(key=lambda x: x["key"])
    if not shards:
        raise RuntimeError("unsigned listing returned no Parquet shards")
    if len(shards) > MAX_SHARDS:
        raise RuntimeError(f"Parquet shard count {len(shards)} exceeds frozen ceiling {MAX_SHARDS}")
    meta["returned_content_count"] = len(contents)
    meta["next_token_present"] = bool(payload.get("NextToken"))
    return shards, meta


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def rows_to_dicts(cursor) -> list[dict[str, object]]:
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
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "phase": "A_TRANSPORT_FEASIBILITY_ONLY",
        "frozen_crawl_id": CRAWL_ID,
        "frozen_target": {
            "url_host_registered_domain": TARGET_DOMAIN,
            "url_path": TARGET_PATH,
            "fetch_status": 200,
            "max_rows": MAX_ROWS,
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
        shards, list_meta = unsigned_list()
        manifest["listing"] = {
            "status": "SUCCEEDED",
            **list_meta,
            "parquet_shard_count": len(shards),
            "shards_sha256": sha256(shards),
            "first_shard_key": shards[0]["key"],
            "last_shard_key": shards[-1]["key"],
        }

        urls = [HTTPS_BASE + str(x["key"]) for x in shards]
        files_sql = "[" + ",".join(sql_quote(url) for url in urls) + "]"
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
        rows = rows_to_dicts(cursor)
        manifest["query"] = {
            "status": "EXECUTED",
            "duckdb_version": duckdb.__version__,
            "httpfs": httpfs,
            "row_count": len(rows),
            "rows": rows,
            "rows_sha256": sha256(rows),
            "error": None,
        }
        success = True
    except Exception as exc:
        success = False
        error = f"{type(exc).__name__}: {exc}"
        if manifest["listing"].get("status") == "NOT_ATTEMPTED":
            manifest["listing"] = {"status": "ERROR", "error": error}
        else:
            manifest["query"] = {"status": "ERROR", "rows": [], "error": error}

    manifest["result"] = {
        "transport_success": success,
        "phase_b_authorized_by_transport_gate": success,
        "match_presence_observed": ((manifest["query"].get("row_count") or 0) > 0) if success else None,
        "zero_rows_if_any_do_not_prove_absence": True,
        "admission_authority_granted": False,
    }
    stable = dict(manifest)
    stable.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = sha256(stable)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    print("worker_version=", WORKER_VERSION)
    print("listing_status=", manifest["listing"].get("status"))
    print("listing_error=", manifest["listing"].get("error"))
    print("listing_exit_code=", manifest["listing"].get("exit_code"))
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
