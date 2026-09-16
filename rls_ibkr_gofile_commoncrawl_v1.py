#!/usr/bin/env python3
import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION = "RLS-IBKR-GOFILE-COMMONCRAWL-WORKER-v1"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
TARGET = "https://gofile.io/?c=gRd3kH"
CRAWLS = [
    "CC-MAIN-2019-04","CC-MAIN-2019-09","CC-MAIN-2019-13","CC-MAIN-2019-18",
    "CC-MAIN-2019-22","CC-MAIN-2019-26","CC-MAIN-2019-30","CC-MAIN-2019-35",
    "CC-MAIN-2019-39","CC-MAIN-2019-43","CC-MAIN-2019-47","CC-MAIN-2019-51",
    "CC-MAIN-2020-05","CC-MAIN-2020-10","CC-MAIN-2020-16","CC-MAIN-2020-24",
    "CC-MAIN-2020-29","CC-MAIN-2020-34","CC-MAIN-2020-40","CC-MAIN-2020-45",
    "CC-MAIN-2020-50","CC-MAIN-2021-04","CC-MAIN-2021-10","CC-MAIN-2021-17",
    "CC-MAIN-2021-21","CC-MAIN-2021-25","CC-MAIN-2021-31","CC-MAIN-2021-39",
    "CC-MAIN-2021-43","CC-MAIN-2021-49"
]
UA = "RLS-Build-Colony-GoFile-Recovery/1.0"
OUT = Path("workloads/artifacts/rls_ibkr_gofile_commoncrawl_v1.json")


def query(crawl):
    q = urllib.parse.urlencode({"url": TARGET, "output": "json", "matchType": "exact"})
    url = f"https://index.commoncrawl.org/{crawl}-index?{q}"
    last_error = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode("utf-8", errors="strict")
                rows = []
                for line in raw.splitlines():
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    rows.append({k: obj.get(k) for k in ["url","timestamp","status","digest","length","mime","filename","offset"]})
                return {"crawl_id": crawl, "status": "MATCH" if rows else "NO_MATCH", "http_status": r.status, "attempts": attempt, "rows": rows, "error": None}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"crawl_id": crawl, "status": "NO_MATCH", "http_status": 404, "attempts": attempt, "rows": [], "error": None}
            last_error = f"HTTP {e.code}"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
        time.sleep(0.4 * attempt)
    return {"crawl_id": crawl, "status": "ERROR", "http_status": None, "attempts": 3, "rows": [], "error": last_error}


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(query, CRAWLS))
    results.sort(key=lambda x: CRAWLS.index(x["crawl_id"]))
    captures = [row for result in results for row in result["rows"]]
    payload = {
        "worker_version": WORKER_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": AUTHORITY,
        "parent_protocol": "RLS-IBKR-GOFILE-2019-RECOVERY-CANDIDATE-v1",
        "credential_policy": {"user_specific_credentials_used": False, "api_key_used": False, "account_login_used": False},
        "target": TARGET,
        "crawl_count": len(CRAWLS),
        "queries": results,
        "capture_row_count": len(captures),
        "capture_rows": captures,
        "archived_landing_or_file_bytes_opened": False,
        "economic_values_opened": False,
        "admission_authority_granted": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_digest_sha256"] = hashlib.sha256(canonical).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("worker_version=", WORKER_VERSION)
    print("evidence_digest_sha256=", payload["evidence_digest_sha256"])
    print("status_counts=", {s: sum(1 for r in results if r["status"] == s) for s in sorted({r["status"] for r in results})})
    print("capture_row_count=", len(captures))
    print("capture_timestamps=", [x.get("timestamp") for x in captures])


if __name__ == "__main__":
    main()
