#!/usr/bin/env python3
import hashlib
import json
import re
import struct
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

WORKER_VERSION = "RLS-IBKR-WAYBACK-ZIP-STRUCTURE-WORKER-v1"
PROTOCOL = "RLS-IBKR-WAYBACK-ZIP-STRUCTURE-v1"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
TARGET = "https://web.archive.org/web/20260221140226id_/http://potential-investments.com/ib_shorting.zip"
UA = "RLS-Build-Colony-Wayback-ZIP-Structure/1.0 (metadata-only, bounded-range)"
TAIL_BYTES = 65557
DATE_RE = re.compile(r"(?P<date>\d{6})_shorting\.tsv$", re.IGNORECASE)


def canonical_digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def range_request(start: int, end: int) -> Tuple[str, Dict[str, str], bytes]:
    req = urllib.request.Request(
        TARGET,
        headers={
            "User-Agent": UA,
            "Accept-Encoding": "identity",
            "Range": f"bytes={start}-{end}",
        },
        method="GET",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        status = getattr(resp, "status", resp.getcode())
        headers = {k.lower(): v for k, v in resp.headers.items()}
        if status != 206:
            resp.close()
            return "RANGE_UNSUPPORTED", headers, b""
        data = resp.read((end - start + 1) + 1)
        resp.close()
        if len(data) != end - start + 1:
            return "RANGE_LENGTH_MISMATCH", headers, b""
        return "OK", headers, data
    except urllib.error.HTTPError as exc:
        return f"HTTP_{exc.code}", {k.lower(): v for k, v in exc.headers.items()}, b""
    except Exception as exc:
        return f"ERROR_{type(exc).__name__}", {"error": str(exc)}, b""


def discover_length() -> Tuple[str, Optional[int], Dict[str, str]]:
    status, headers, _ = range_request(0, 0)
    if status != "OK":
        return status, None, headers
    content_range = headers.get("content-range", "")
    m = re.match(r"bytes\s+0-0/(\d+)$", content_range)
    if not m:
        return "CONTENT_RANGE_UNPARSABLE", None, headers
    return "OK", int(m.group(1)), headers


def parse_eocd(tail: bytes, absolute_tail_start: int) -> Dict:
    sig = b"PK\x05\x06"
    idx = tail.rfind(sig)
    if idx < 0:
        raise ValueError("EOCD_NOT_FOUND")
    if len(tail) - idx < 22:
        raise ValueError("EOCD_TRUNCATED")
    fields = struct.unpack_from("<4s4H2IH", tail, idx)
    _, disk_no, cd_disk, disk_entries, total_entries, cd_size, cd_offset, comment_len = fields
    if idx + 22 + comment_len > len(tail):
        raise ValueError("EOCD_COMMENT_TRUNCATED")
    if cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF or total_entries == 0xFFFF:
        raise ValueError("ZIP64_REQUIRED")
    return {
        "absolute_offset": absolute_tail_start + idx,
        "disk_no": disk_no,
        "central_directory_disk": cd_disk,
        "disk_entries": disk_entries,
        "total_entries": total_entries,
        "central_directory_size": cd_size,
        "central_directory_offset": cd_offset,
        "comment_length": comment_len,
    }


def decode_name(raw: bytes, flags: int) -> str:
    encoding = "utf-8" if flags & 0x800 else "cp437"
    return raw.decode(encoding, errors="strict")


def parse_central_directory(data: bytes, expected_entries: int) -> List[Dict]:
    entries: List[Dict] = []
    pos = 0
    fmt = "<4s6H3I5H2I"
    fixed = struct.calcsize(fmt)
    while pos < len(data):
        if len(data) - pos < fixed:
            raise ValueError("CENTRAL_DIRECTORY_TRUNCATED")
        values = struct.unpack_from(fmt, data, pos)
        (
            sig, ver_made, ver_needed, flags, method, mod_time, mod_date,
            crc32, compressed_size, uncompressed_size,
            name_len, extra_len, comment_len, disk_start, internal_attr,
            external_attr, local_header_offset,
        ) = values
        if sig != b"PK\x01\x02":
            raise ValueError(f"CENTRAL_DIRECTORY_BAD_SIGNATURE_AT_{pos}")
        total_len = fixed + name_len + extra_len + comment_len
        if pos + total_len > len(data):
            raise ValueError("CENTRAL_DIRECTORY_ENTRY_TRUNCATED")
        raw_name = data[pos + fixed:pos + fixed + name_len]
        name = decode_name(raw_name, flags)
        entries.append({
            "name": name,
            "crc32": f"{crc32:08x}",
            "compressed_size": compressed_size,
            "uncompressed_size": uncompressed_size,
            "compression_method": method,
            "flags": flags,
            "local_header_offset": local_header_offset,
        })
        pos += total_len
    if len(entries) != expected_entries:
        raise ValueError(f"ENTRY_COUNT_MISMATCH_{len(entries)}_{expected_entries}")
    return entries


def month_range(first: str, last: str) -> List[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def main() -> None:
    result: Dict = {
        "worker_version": WORKER_VERSION,
        "protocol": PROTOCOL,
        "authority": AUTHORITY,
        "target": TARGET,
        "credential_policy": {
            "user_specific_credentials_used": False,
            "api_key_used": False,
            "account_login_used": False,
        },
        "member_payload_bytes_opened": False,
        "economic_values_opened": False,
        "admission_authority_granted": False,
    }

    status, length, initial_headers = discover_length()
    result["range_probe_status"] = status
    result["container_content_length"] = length
    result["initial_headers"] = {
        k: initial_headers.get(k) for k in ["content-range", "content-length", "etag", "last-modified", "accept-ranges", "content-type"] if initial_headers.get(k) is not None
    }
    if status != "OK" or length is None or length <= 0:
        result["status"] = "STOP_RANGE_OR_LENGTH_UNAVAILABLE"
    else:
        tail_start = max(0, length - TAIL_BYTES)
        tail_status, tail_headers, tail = range_request(tail_start, length - 1)
        result["tail_range_status"] = tail_status
        if tail_status != "OK":
            result["status"] = "STOP_TAIL_RANGE_FAILED"
        else:
            try:
                eocd = parse_eocd(tail, tail_start)
                result["eocd"] = eocd
                cd_start = eocd["central_directory_offset"]
                cd_size = eocd["central_directory_size"]
                cd_end = cd_start + cd_size - 1
                if cd_start < 0 or cd_size <= 0 or cd_end >= length:
                    raise ValueError("CENTRAL_DIRECTORY_BOUNDS_INVALID")
                cd_status, cd_headers, cd_bytes = range_request(cd_start, cd_end)
                result["central_directory_range_status"] = cd_status
                if cd_status != "OK":
                    result["status"] = "STOP_CENTRAL_DIRECTORY_RANGE_FAILED"
                else:
                    entries = parse_central_directory(cd_bytes, eocd["total_entries"])
                    result["central_directory_sha256"] = hashlib.sha256(cd_bytes).hexdigest()
                    result["member_count"] = len(entries)
                    result["members"] = entries
                    dates: List[str] = []
                    for entry in entries:
                        base = PurePosixPath(entry["name"]).name
                        m = DATE_RE.search(base)
                        if not m:
                            continue
                        try:
                            dt = datetime.strptime(m.group("date"), "%y%m%d")
                            dates.append(dt.strftime("%Y-%m-%d"))
                        except ValueError:
                            pass
                    dates = sorted(set(dates))
                    months = sorted(set(d[:7] for d in dates))
                    target_months = month_range("2016-09", "2026-08")
                    result["filename_date_summary"] = {
                        "matched_daily_snapshot_count": len(dates),
                        "first_date": dates[0] if dates else None,
                        "last_date": dates[-1] if dates else None,
                        "observed_months": months,
                        "observed_target_month_count": len([m for m in target_months if m in set(months)]),
                        "missing_target_months": [m for m in target_months if m not in set(months)],
                    }
                    result["status"] = "STRUCTURE_OBSERVED_NO_MEMBER_PAYLOAD_OPENED"
            except Exception as exc:
                result["status"] = "STOP_ZIP_STRUCTURE_ERROR"
                result["error"] = f"{type(exc).__name__}: {exc}"

    digest_basis = dict(result)
    result["evidence_digest_sha256"] = canonical_digest(digest_basis)
    out = "workloads/artifacts/rls_ibkr_wayback_zip_structure_v1.json"
    import os
    os.makedirs("workloads/artifacts", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print("worker_version=", WORKER_VERSION)
    print("status=", result.get("status"))
    print("range_probe_status=", result.get("range_probe_status"))
    print("container_content_length=", result.get("container_content_length"))
    print("member_count=", result.get("member_count"))
    print("filename_date_summary=", result.get("filename_date_summary"))
    print("evidence_digest_sha256=", result["evidence_digest_sha256"])


if __name__ == "__main__":
    main()
