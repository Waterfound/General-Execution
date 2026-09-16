#!/usr/bin/env python3
"""Public-safe Build Colony worker for RLS IBKR archival recovery.

This workload has no RLS admission authority. It only:
1. downloads the predeclared public community archive;
2. hashes the archive and every member;
3. measures capture-date/month coverage from filenames and embedded IBKR BOF headers;
4. queries predeclared Internet Archive aliases for 2016-09..2017-04;
5. hashes any successfully recovered archived snapshots; and
6. emits a deterministic JSON evidence manifest.

It never reads return/performance data and never fills missing months.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

WORKER_VERSION = "RLS-IBKR-USA-ARCHIVE-RECOVERY-WORKER-v1"
COMMUNITY_URL = "https://potential-investments.com/ib_shorting.zip"
TARGET_FIRST_MONTH = "2016-09"
TARGET_LAST_MONTH = "2026-08"
WAYBACK_FIRST = "20160901"
WAYBACK_LAST = "20170417"
WAYBACK_VARIANTS = (
    "ftp://ftp3.interactivebrokers.com/usa.txt",
    "http://ftp3.interactivebrokers.com/usa.txt",
    "https://ftp3.interactivebrokers.com/usa.txt",
)
USER_AGENT = "RLS-Build-Colony-Archive-Recovery/1.0 (+public-research)"
BOF_RE = re.compile(rb"#BOF\|(?P<y>20\d{2})[.\-/](?P<m>\d{2})[.\-/](?P<d>\d{2})(?:\|(?P<t>\d{2}:\d{2}:\d{2}))?", re.I)
FILENAME_DATE_RES = (
    re.compile(r"(?<!\d)(20\d{2})[-_.](\d{2})[-_.](\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def month_index(month: str) -> int:
    y, m = map(int, month.split("-"))
    return y * 12 + m - 1


def month_from_index(value: int) -> str:
    return f"{value // 12:04d}-{value % 12 + 1:02d}"


def target_months() -> list[str]:
    start = month_index(TARGET_FIRST_MONTH)
    end = month_index(TARGET_LAST_MONTH)
    return [month_from_index(i) for i in range(start, end + 1)]


def http_open(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    return urllib.request.urlopen(req, timeout=timeout)


def download_to_temp(url: str) -> tuple[Path, str, int, dict[str, str]]:
    fd, raw_path = tempfile.mkstemp(prefix="rls_ibkr_", suffix=".zip")
    os.close(fd)
    path = Path(raw_path)
    h = hashlib.sha256()
    size = 0
    headers: dict[str, str] = {}
    try:
        with http_open(url, timeout=120) as response, path.open("wb") as out:
            headers = {k.lower(): v for k, v in response.headers.items()}
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                size += len(chunk)
        return path, h.hexdigest(), size, headers
    except Exception:
        path.unlink(missing_ok=True)
        raise


def filename_date(name: str) -> str | None:
    for rx in FILENAME_DATE_RES:
        match = rx.search(name)
        if not match:
            continue
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            continue
    return None


def embedded_bof_date(prefix: bytes) -> str | None:
    match = BOF_RE.search(prefix)
    if not match:
        return None
    try:
        return date(int(match.group("y")), int(match.group("m")), int(match.group("d"))).isoformat()
    except ValueError:
        return None


def inspect_zip(path: Path) -> dict[str, object]:
    members: list[dict[str, object]] = []
    dates: dict[str, list[str]] = {}
    schema_prefix_hashes: dict[str, int] = {}
    with zipfile.ZipFile(path, "r") as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        for info in infos:
            h = hashlib.sha256()
            prefix = bytearray()
            size = 0
            with zf.open(info, "r") as src:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    if len(prefix) < 65536:
                        prefix.extend(chunk[: 65536 - len(prefix)])
                    h.update(chunk)
                    size += len(chunk)
            prefix_bytes = bytes(prefix)
            bof = embedded_bof_date(prefix_bytes)
            by_name = filename_date(info.filename)
            capture_date = bof or by_name
            source = "BOF_HEADER" if bof else ("FILENAME" if by_name else None)
            header_lines = prefix_bytes.splitlines()[:3]
            schema_material = b"\n".join(header_lines)
            schema_hash = sha256_bytes(schema_material) if schema_material else None
            if schema_hash:
                schema_prefix_hashes[schema_hash] = schema_prefix_hashes.get(schema_hash, 0) + 1
            member = {
                "name": info.filename,
                "compressed_size": info.compress_size,
                "uncompressed_size": size,
                "sha256": h.hexdigest(),
                "capture_date": capture_date,
                "capture_date_source": source,
                "filename_date": by_name,
                "embedded_bof_date": bof,
                "filename_bof_date_agree": (by_name == bof) if by_name and bof else None,
                "schema_prefix_sha256": schema_hash,
            }
            members.append(member)
            if capture_date:
                dates.setdefault(capture_date, []).append(info.filename)

    duplicate_dates = {k: v for k, v in dates.items() if len(v) > 1}
    observed_months = sorted({d[:7] for d in dates})
    targets = target_months()
    target_present = [m for m in targets if m in observed_months]
    target_missing = [m for m in targets if m not in observed_months]

    longest = 0
    current = 0
    previous = None
    for m in map(month_index, target_present):
        if previous is not None and m == previous + 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = m

    return {
        "member_count": len(members),
        "members": members,
        "earliest_capture_date": min(dates) if dates else None,
        "latest_capture_date": max(dates) if dates else None,
        "distinct_capture_dates": len(dates),
        "duplicate_capture_dates": duplicate_dates,
        "observed_months": observed_months,
        "target_months_present": target_present,
        "target_months_missing": target_missing,
        "target_month_count_present": len(target_present),
        "target_month_count_missing": len(target_missing),
        "longest_consecutive_target_month_run": longest,
        "schema_prefix_hash_counts": dict(sorted(schema_prefix_hashes.items())),
    }


def cdx_query(original: str) -> dict[str, object]:
    params = {
        "url": original,
        "output": "json",
        "filter": "statuscode:200",
        "from": WAYBACK_FIRST[:4],
        "to": WAYBACK_LAST[:4],
        "fl": "timestamp,original,statuscode,digest,length,mimetype",
        "collapse": "digest",
    }
    url = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(params)
    try:
        with http_open(url, timeout=60) as response:
            raw = response.read()
        decoded = json.loads(raw)
        if not isinstance(decoded, list) or not decoded:
            rows: list[dict[str, str]] = []
        else:
            header = decoded[0]
            rows = [dict(zip(header, row)) for row in decoded[1:] if isinstance(row, list)]
        rows = [r for r in rows if WAYBACK_FIRST <= r.get("timestamp", "")[:8] <= WAYBACK_LAST]
        rows.sort(key=lambda r: r.get("timestamp", ""))
        return {"query_url": url, "ok": True, "rows": rows, "error": None}
    except Exception as exc:
        return {"query_url": url, "ok": False, "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def availability_query(original: str, anchor: str) -> dict[str, object]:
    params = {"url": original, "timestamp": anchor}
    url = "https://archive.org/wayback/available?" + urllib.parse.urlencode(params)
    try:
        with http_open(url, timeout=45) as response:
            raw = response.read()
        payload = json.loads(raw)
        closest = ((payload.get("archived_snapshots") or {}).get("closest") or {})
        return {
            "query_url": url,
            "ok": True,
            "available": bool(closest.get("available")),
            "timestamp": closest.get("timestamp"),
            "snapshot_url": closest.get("url"),
            "status": closest.get("status"),
            "error": None,
        }
    except Exception as exc:
        return {
            "query_url": url,
            "ok": False,
            "available": False,
            "timestamp": None,
            "snapshot_url": None,
            "status": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def monthly_anchors() -> list[str]:
    anchors = []
    for month in ["2016-09", "2016-10", "2016-11", "2016-12", "2017-01", "2017-02", "2017-03", "2017-04"]:
        day = "17" if month == "2017-04" else "18"
        anchors.append(month.replace("-", "") + day)
    return anchors


def raw_snapshot_hash(snapshot_url: str | None) -> dict[str, object] | None:
    if not snapshot_url:
        return None
    url = snapshot_url.replace("http://", "https://", 1)
    # Request identity/raw representation where supported.
    match = re.search(r"/web/(\d+)/(.*)$", url)
    if match and "id_/" not in url:
        url = f"https://web.archive.org/web/{match.group(1)}id_/{match.group(2)}"
    try:
        h = hashlib.sha256()
        size = 0
        prefix = bytearray()
        with http_open(url, timeout=60) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                if len(prefix) < 65536:
                    prefix.extend(chunk[: 65536 - len(prefix)])
                h.update(chunk)
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    raise RuntimeError("snapshot exceeds frozen 50 MiB safety ceiling")
        return {
            "raw_url": url,
            "sha256": h.hexdigest(),
            "size": size,
            "embedded_bof_date": embedded_bof_date(bytes(prefix)),
            "error": None,
        }
    except Exception as exc:
        return {
            "raw_url": url,
            "sha256": None,
            "size": None,
            "embedded_bof_date": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def inspect_wayback() -> dict[str, object]:
    variants = []
    anchors = monthly_anchors()
    for original in WAYBACK_VARIANTS:
        cdx = cdx_query(original)
        availability = [availability_query(original, anchor) for anchor in anchors]
        # Only raw-fetch a unique closest snapshot that lands inside the frozen window.
        snapshots = []
        seen = set()
        for item in availability:
            ts = item.get("timestamp")
            url = item.get("snapshot_url")
            if not item.get("available") or not isinstance(ts, str) or not (WAYBACK_FIRST <= ts[:8] <= WAYBACK_LAST):
                continue
            key = (ts, url)
            if key in seen:
                continue
            seen.add(key)
            snapshots.append({"timestamp": ts, "snapshot_url": url, "raw": raw_snapshot_hash(url if isinstance(url, str) else None)})
        variants.append({"original": original, "cdx": cdx, "availability_by_anchor": availability, "recovered_snapshots": snapshots})
    return {"variants": variants, "anchors": anchors}


def main() -> int:
    output = Path("artifacts/rls_ibkr_archive_recovery_manifest_v1.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "generated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "authority": "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY",
        "target_first_month": TARGET_FIRST_MONTH,
        "target_last_month": TARGET_LAST_MONTH,
        "target_month_count": len(target_months()),
        "community_archive": {"url": COMMUNITY_URL, "status": "NOT_ATTEMPTED"},
        "internet_archive": {"status": "NOT_ATTEMPTED"},
    }

    archive_path = None
    try:
        archive_path, archive_sha, archive_size, headers = download_to_temp(COMMUNITY_URL)
        archive = inspect_zip(archive_path)
        manifest["community_archive"] = {
            "url": COMMUNITY_URL,
            "status": "RETRIEVED",
            "sha256": archive_sha,
            "size": archive_size,
            "http_headers_subset": {k: headers[k] for k in sorted(headers) if k in {"content-type", "content-length", "etag", "last-modified"}},
            **archive,
        }
    except Exception as exc:
        manifest["community_archive"] = {
            "url": COMMUNITY_URL,
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        if archive_path:
            archive_path.unlink(missing_ok=True)

    manifest["internet_archive"] = {"status": "QUERIED", **inspect_wayback()}

    manifest["manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
