#!/usr/bin/env python3
"""Credential-free public Build Colony worker for RLS IBKR gap recovery V1.2.

OBSERVATION ONLY. This worker has zero RLS admission authority.

Frozen task:
- preserve the exact 2016-09..2026-08 120-month target;
- search only the exact 39 months missing after verified V1.1 archive recovery;
- use no user-specific credentials;
- prefer IBKR publisher-public bytes;
- recover historical bytes only from public archives;
- count a month only when a full IBKR USA snapshot is mechanically validated;
- never read return/performance data.

The worker deliberately emits metadata + hashes only. It does not emit securities rows.
"""
from __future__ import annotations

import ftplib
import gzip
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION = "RLS-IBKR-PUBLIC-GAP-RECOVERY-WORKER-v1.2"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
USER_AGENT = "RLS-Build-Colony-Gap-Recovery/1.2 (credential-free public evidence)"
OUTPUT = Path("artifacts/rls_ibkr_public_gap_recovery_manifest_v1_2.json")

KNOWN_ARCHIVE_SHA256 = "e920f31b44254fc3633d610e621159a834bca90ed2b51b19d46046edb1d90724"
KNOWN_ARCHIVE_MANIFEST_SHA256 = "56543622b51d4d7684e79d4b972041088daf7992d8d9f39af98c36d881ed0c8b"
KNOWN_PRESENT_MONTHS = 81

MISSING_MONTHS = (
    "2016-09", "2016-10", "2016-11", "2016-12",
    "2017-01", "2017-02", "2017-03", "2017-04", "2017-05", "2017-06", "2017-07", "2017-08", "2017-09",
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
)
MISSING_SET = set(MISSING_MONTHS)
TARGET_YEARS = {m[:4] for m in MISSING_MONTHS}

FTP_HOSTS = ("ftp2.interactivebrokers.com", "ftp3.interactivebrokers.com")
FTP_USER = "shortstock"
FTP_FILE = "usa.txt"

CC_COLLINFO = "https://index.commoncrawl.org/collinfo.json"
CC_DATA = "https://data.commoncrawl.org/"
CC_TARGETS = (
    "ftp2.interactivebrokers.com/usa.txt",
    "ftp3.interactivebrokers.com/usa.txt",
)
CC_QUERY_SLEEP_SECONDS = 1.25
CC_MAX_WARC_RECORD_BYTES = 25 * 1024 * 1024
CC_MAX_RECOVERIES_PER_MONTH = 2

ARQUIVO_CDX = "https://arquivo.pt/wayback/-cdx"
ARQUIVO_VARIANTS = tuple(
    f"{scheme}://{host}/usa.txt"
    for host in FTP_HOSTS
    for scheme in ("ftp", "http", "https")
)

BOF_RE = re.compile(rb"(?m)^#BOF\|(?P<date>20\d{2}(?:[.\-/]?\d{2}){2})\|(?P<time>[^\r\n|]*)")
HEADER_OLD = b"#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|"
HEADER_FIGI = b"#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|"
EOF_RE = re.compile(rb"(?m)^#EOF(?:\|[^\r\n]*)?$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def http_bytes(url: str, timeout: int = 30, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> tuple[bytes, dict[str, str], int]:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        out = bytearray()
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.extend(chunk)
            if max_bytes is not None and len(out) > max_bytes:
                raise RuntimeError(f"response exceeds frozen ceiling {max_bytes} bytes")
        return bytes(out), {k.lower(): v for k, v in response.headers.items()}, status


def http_json(url: str, timeout: int = 30, max_bytes: int = 10 * 1024 * 1024) -> object:
    raw, _, _ = http_bytes(url, timeout=timeout, max_bytes=max_bytes)
    return json.loads(raw)


def parse_bof_date(raw: bytes) -> str | None:
    m = BOF_RE.search(raw[:65536])
    if not m:
        return None
    token = m.group("date").decode("ascii", "strict")
    digits = re.sub(r"\D", "", token)
    if len(digits) != 8:
        return None
    try:
        return datetime.strptime(digits, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def validate_ibkr_snapshot(raw: bytes) -> dict[str, object]:
    capture_date = parse_bof_date(raw)
    prefix = raw[:65536]
    header = HEADER_FIGI if HEADER_FIGI in prefix else (HEADER_OLD if HEADER_OLD in prefix else None)
    eof = bool(EOF_RE.search(raw[-65536:]))
    has_fee = b"FEERATE" in prefix
    has_avail = b"AVAILABLE" in prefix
    row_count = 0
    if header is not None:
        # Structural row count only; row contents are never emitted.
        for line in raw.splitlines():
            if line and not line.startswith(b"#") and b"|" in line:
                row_count += 1
    valid = bool(capture_date and header and eof and has_fee and has_avail and row_count > 0)
    return {
        "valid_full_ibkr_snapshot": valid,
        "capture_date": capture_date,
        "capture_month": capture_date[:7] if capture_date else None,
        "schema": "FIGI" if header == HEADER_FIGI else ("LEGACY" if header == HEADER_OLD else None),
        "has_feerate": has_fee,
        "has_available": has_avail,
        "has_eof": eof,
        "structural_row_count": row_count,
        "size": len(raw),
        "sha256": sha256_bytes(raw),
    }


def probe_live_ftp(host: str) -> dict[str, object]:
    result: dict[str, object] = {"host": host, "username": FTP_USER, "file": FTP_FILE, "status": "ERROR"}
    try:
        bio = io.BytesIO()
        with ftplib.FTP(timeout=40) as ftp:
            ftp.connect(host, 21)
            ftp.login(FTP_USER, "")
            ftp.retrbinary(f"RETR {FTP_FILE}", bio.write)
        raw = bio.getvalue()
        result.update({"status": "RETRIEVED", **validate_ibkr_snapshot(raw)})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def cc_collections() -> tuple[list[dict[str, object]], str | None]:
    try:
        payload = http_json(CC_COLLINFO, timeout=30)
        rows = payload if isinstance(payload, list) else []
        chosen = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("id", ""))
            if not cid.startswith("CC-MAIN-") or len(cid) < 12:
                continue
            year = cid[len("CC-MAIN-"):len("CC-MAIN-") + 4]
            if year in TARGET_YEARS:
                chosen.append(row)
        chosen.sort(key=lambda x: str(x.get("id", "")))
        return chosen, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def cc_query(index_api: str, target: str) -> dict[str, object]:
    url = index_api + ("&" if "?" in index_api else "?") + urllib.parse.urlencode({"url": target, "output": "json"})
    try:
        raw, _, status = http_bytes(url, timeout=30, max_bytes=5 * 1024 * 1024)
        records = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return {"query_url": url, "http_status": status, "records": records, "error": None}
    except urllib.error.HTTPError as exc:
        # 404 means no indexed capture for this exact URL in this crawl.
        return {"query_url": url, "http_status": exc.code, "records": [], "error": None if exc.code == 404 else f"HTTPError: {exc}"}
    except Exception as exc:
        return {"query_url": url, "http_status": None, "records": [], "error": f"{type(exc).__name__}: {exc}"}


def extract_http_payload_from_warc_record(compressed: bytes) -> bytes:
    warc = gzip.decompress(compressed)
    # WARC header, then application/http response. We only need the HTTP entity body.
    first = warc.find(b"\r\n\r\n")
    sep_len = 4
    if first < 0:
        first = warc.find(b"\n\n")
        sep_len = 2
    if first < 0:
        raise ValueError("WARC header terminator not found")
    http = warc[first + sep_len:]
    if not http.startswith(b"HTTP/"):
        raise ValueError("WARC record is not an HTTP response")
    second = http.find(b"\r\n\r\n")
    http_sep = 4
    if second < 0:
        second = http.find(b"\n\n")
        http_sep = 2
    if second < 0:
        raise ValueError("HTTP header terminator not found")
    header_blob = http[:second].lower()
    body = http[second + http_sep:]
    if b"content-encoding: gzip" in header_blob:
        body = gzip.decompress(body)
    return body


def recover_cc_record(record: dict[str, object]) -> dict[str, object]:
    filename = str(record.get("filename", ""))
    try:
        offset = int(str(record.get("offset", "")))
        length = int(str(record.get("length", "")))
    except ValueError:
        return {"status": "REJECTED_METADATA", "reason": "invalid offset/length", "record": compact_cc_record(record)}
    if not filename or offset < 0 or length <= 0 or length > CC_MAX_WARC_RECORD_BYTES:
        return {"status": "REJECTED_METADATA", "reason": "missing filename or frozen length ceiling exceeded", "record": compact_cc_record(record)}
    try:
        url = CC_DATA + filename
        raw_record, _, status = http_bytes(
            url,
            timeout=60,
            headers={"Range": f"bytes={offset}-{offset + length - 1}"},
            max_bytes=CC_MAX_WARC_RECORD_BYTES,
        )
        if status not in (200, 206):
            raise RuntimeError(f"unexpected range status {status}")
        payload = extract_http_payload_from_warc_record(raw_record)
        validation = validate_ibkr_snapshot(payload)
        return {
            "status": "RECOVERED",
            "record": compact_cc_record(record),
            "warc_record_sha256": sha256_bytes(raw_record),
            "payload": validation,
        }
    except Exception as exc:
        return {"status": "ERROR", "record": compact_cc_record(record), "error": f"{type(exc).__name__}: {exc}"}


def compact_cc_record(record: dict[str, object]) -> dict[str, object]:
    keys = ("url", "timestamp", "status", "mime", "digest", "length", "offset", "filename")
    return {k: record.get(k) for k in keys}


def probe_common_crawl() -> dict[str, object]:
    collections, error = cc_collections()
    result: dict[str, object] = {
        "status": "ERROR" if error else "QUERIED",
        "collinfo_error": error,
        "collection_count": len(collections),
        "queries": [],
        "recovered": [],
    }
    if error:
        return result

    candidates_by_month: dict[str, list[dict[str, object]]] = defaultdict(list)
    query_summaries = []
    for coll in collections:
        cid = str(coll.get("id"))
        api = str(coll.get("cdx-api") or f"https://index.commoncrawl.org/{cid}-index")
        for target in CC_TARGETS:
            q = cc_query(api, target)
            accepted_records = []
            for rec in q["records"]:
                ts = str(rec.get("timestamp", ""))
                if len(ts) >= 6 and ts[:4].isdigit() and ts[4:6].isdigit():
                    month = ts[:4] + "-" + ts[4:6]
                    if month in MISSING_SET and str(rec.get("status", "")) == "200":
                        accepted_records.append(compact_cc_record(rec))
                        candidates_by_month[month].append(rec)
            query_summaries.append({
                "collection": cid,
                "target": target,
                "http_status": q["http_status"],
                "error": q["error"],
                "matching_gap_records": accepted_records,
            })
            time.sleep(CC_QUERY_SLEEP_SECONDS)

    recovered = []
    for month in MISSING_MONTHS:
        seen = set()
        count = 0
        for rec in sorted(candidates_by_month.get(month, []), key=lambda r: str(r.get("timestamp", ""))):
            key = (rec.get("digest"), rec.get("filename"), rec.get("offset"))
            if key in seen:
                continue
            seen.add(key)
            recovered_item = recover_cc_record(rec)
            recovered_item["target_gap_month"] = month
            recovered.append(recovered_item)
            count += 1
            if count >= CC_MAX_RECOVERIES_PER_MONTH:
                break

    result["queries"] = query_summaries
    result["recovered"] = recovered
    return result


def flatten_arquivo_rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], list):
            header = payload[0]
            if all(isinstance(x, str) for x in header):
                return [dict(zip(header, row)) for row in payload[1:] if isinstance(row, list)]
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("results", "response", "items", "captures"):
            value = payload.get(key)
            if isinstance(value, list):
                return flatten_arquivo_rows(value)
    return []


def probe_arquivo() -> dict[str, object]:
    summaries = []
    for original in ARQUIVO_VARIANTS:
        params = {
            "output": "json",
            "url": original,
            "from": "20160901000000",
            "to": "20260831235959",
        }
        url = ARQUIVO_CDX + "?" + urllib.parse.urlencode(params)
        try:
            payload = http_json(url, timeout=45, max_bytes=10 * 1024 * 1024)
            rows = flatten_arquivo_rows(payload)
            gap_rows = []
            for row in rows:
                ts = str(row.get("timestamp") or row.get("tstamp") or row.get("date") or "")
                digits = re.sub(r"\D", "", ts)
                if len(digits) >= 6:
                    month = digits[:4] + "-" + digits[4:6]
                    if month in MISSING_SET:
                        gap_rows.append({k: row.get(k) for k in ("timestamp", "url", "original", "status", "statuscode", "digest") if k in row})
            summaries.append({"original": original, "status": "QUERIED", "row_count": len(rows), "gap_rows": gap_rows, "error": None})
        except urllib.error.HTTPError as exc:
            summaries.append({"original": original, "status": "HTTP_ERROR", "row_count": 0, "gap_rows": [], "error": f"HTTP {exc.code}"})
        except Exception as exc:
            summaries.append({"original": original, "status": "ERROR", "row_count": 0, "gap_rows": [], "error": f"{type(exc).__name__}: {exc}"})
        time.sleep(0.75)
    # V1.2 intentionally records Arquivo.pt metadata only until its returned capture schema is mechanically observed.
    # This prevents post-hoc invention of a retrieval rule after seeing outcomes.
    return {"status": "QUERIED_METADATA_ONLY", "variants": summaries, "counts_for_gap_coverage": False}


def anonymous_bucket_probe() -> dict[str, object]:
    # The bucket name is published in the public open-source collector. This is an anonymous read/list probe only.
    bucket = "ibkr-borrow-collector-borrowdatabucket-u0yupnyt837q"
    url = f"https://{bucket}.s3.amazonaws.com/?list-type=2&prefix=ibkr/borrow/2026-01-17/"
    try:
        raw, _, status = http_bytes(url, timeout=20, max_bytes=2 * 1024 * 1024)
        return {"bucket": bucket, "status": "PUBLIC" if status == 200 else "UNEXPECTED", "http_status": status, "response_sha256": sha256_bytes(raw), "counts_for_gap_coverage": False}
    except urllib.error.HTTPError as exc:
        return {"bucket": bucket, "status": "NOT_ANONYMOUSLY_LISTABLE" if exc.code in (401, 403) else "HTTP_ERROR", "http_status": exc.code, "counts_for_gap_coverage": False}
    except Exception as exc:
        return {"bucket": bucket, "status": "ERROR", "http_status": None, "error": f"{type(exc).__name__}: {exc}", "counts_for_gap_coverage": False}


def recovered_gap_months(common_crawl: dict[str, object]) -> list[str]:
    months = set()
    for item in common_crawl.get("recovered", []):
        if not isinstance(item, dict) or item.get("status") != "RECOVERED":
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict) or not payload.get("valid_full_ibkr_snapshot"):
            continue
        month = payload.get("capture_month")
        if month in MISSING_SET and month == item.get("target_gap_month"):
            months.add(str(month))
    return sorted(months)


def main() -> int:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": generated,
        "frozen_target": {
            "first_month": "2016-09",
            "last_month": "2026-08",
            "required_full_calendar_months": 120,
            "known_present_months_before_run": KNOWN_PRESENT_MONTHS,
            "missing_months_before_run": list(MISSING_MONTHS),
            "known_archive_sha256": KNOWN_ARCHIVE_SHA256,
            "known_archive_manifest_sha256": KNOWN_ARCHIVE_MANIFEST_SHA256,
        },
        "credential_policy": {
            "user_specific_credentials_used": False,
            "aws_login_used": False,
            "provider_signup_used": False,
            "ibkr_public_generic_ftp_identity_only": True,
        },
    }

    manifest["live_ibkr_publisher"] = [probe_live_ftp(host) for host in FTP_HOSTS]
    manifest["common_crawl"] = probe_common_crawl()
    manifest["arquivo_pt"] = probe_arquivo()
    manifest["public_collector_bucket"] = anonymous_bucket_probe()

    recovered = recovered_gap_months(manifest["common_crawl"])
    residual = [m for m in MISSING_MONTHS if m not in set(recovered)]
    manifest["coverage_result"] = {
        "new_full_snapshot_gap_months_recovered": recovered,
        "new_gap_month_count": len(recovered),
        "residual_missing_months": residual,
        "residual_missing_month_count": len(residual),
        "combined_month_count_if_all_new_recoveries_authenticate": KNOWN_PRESENT_MONTHS + len(recovered),
        "threshold_120_met_by_this_public_recovery": KNOWN_PRESENT_MONTHS + len(recovered) >= 120,
        "note": "Only mechanically validated full IBKR snapshots recovered from Common Crawl count. Arquivo.pt metadata and third-party collector metadata do not count in V1.2.",
    }

    # Stable digest excludes runtime timestamp and the digest field itself.
    digest_material = dict(manifest)
    digest_material.pop("generated_at_utc", None)
    manifest["evidence_digest_sha256"] = sha256_bytes(canonical_json_bytes(digest_material))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    c = manifest["coverage_result"]
    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    print("live_ibkr_statuses=", [(x.get("host"), x.get("status"), x.get("capture_date"), x.get("schema")) for x in manifest["live_ibkr_publisher"]])
    print("common_crawl_collections=", manifest["common_crawl"].get("collection_count"))
    print("new_full_snapshot_gap_months_recovered=", c["new_full_snapshot_gap_months_recovered"])
    print("residual_missing_month_count=", c["residual_missing_month_count"])
    print("residual_missing_months=", c["residual_missing_months"])
    print("threshold_120_met_by_this_public_recovery=", c["threshold_120_met_by_this_public_recovery"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
