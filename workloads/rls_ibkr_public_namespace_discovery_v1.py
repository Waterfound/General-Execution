#!/usr/bin/env python3
"""Credential-free metadata-only IBKR namespace discovery for RLS.

OBSERVATION ONLY. Zero RLS admission authority.

This worker deliberately never issues RETR or opens file bodies. It enumerates only
publisher-exposed namespace metadata on ftp2.interactivebrokers.com using the public
shortstock login, bounded to root plus one directory level.
"""
from __future__ import annotations

import ftplib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath, Path

WORKER_VERSION = "RLS-IBKR-PUBLIC-NAMESPACE-DISCOVERY-v1.0.1"
AUTHORITY = "OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY"
HOST = "ftp2.interactivebrokers.com"
USER = "shortstock"
PASSWORD = ""
TIMEOUT = 30
MAX_ENTRIES_PER_DIRECTORY = 500
MAX_CHILD_DIRECTORIES = 100
OUTPUT = Path("artifacts/rls_ibkr_public_namespace_discovery_v1.json")
TERMS = (
    "archive", "backup", "history", "historical", "hist", "old",
    "short", "usa", ".zip", ".gz", ".bz2", ".csv", ".tsv",
)
HISTORICAL_TERMS = (
    "archive", "backup", "history", "historical", "hist", "old",
    ".zip", ".gz", ".bz2", ".csv", ".tsv",
)
CURRENT_ONLY_PATHS = {"/usa.txt", "/usa.txt.md5"}
DATEISH = re.compile(r"(?:^|[^0-9])(?:20\d{2}(?:[-_.]?\d{2}){0,2}|\d{6,8})(?:[^0-9]|$)")


def sha256_json(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def safe_cmd(ftp: ftplib.FTP, cmd: str) -> dict[str, object]:
    try:
        return {"ok": True, "response": ftp.sendcmd(cmd)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def candidate_reason(path: str) -> list[str]:
    lower = path.lower()
    reasons = [f"term:{term}" for term in TERMS if term in lower]
    if DATEISH.search(path):
        reasons.append("dateish_name")
    return reasons


def historical_candidate(entry: dict[str, object]) -> bool:
    path = str(entry.get("path", "")).lower()
    if path in CURRENT_ONLY_PATHS:
        return False
    if entry.get("type") == "dir":
        return True
    reasons = [str(x) for x in entry.get("candidate_reasons", [])]
    if "dateish_name" in reasons:
        return True
    return any(f"term:{term}" in reasons for term in HISTORICAL_TERMS)


def normalize_entry(parent: str, name: str, facts: dict[str, str] | None, source: str) -> dict[str, object]:
    facts = facts or {}
    path = str(PurePosixPath(parent) / name) if parent not in ("", "/") else f"/{name}"
    return {
        "path": path,
        "name": name,
        "type": facts.get("type"),
        "size": facts.get("size"),
        "modify": facts.get("modify"),
        "perm": facts.get("perm"),
        "unique": facts.get("unique"),
        "listing_source": source,
        "candidate_reasons": candidate_reason(path),
    }


def list_directory_mlsd(ftp: ftplib.FTP, path: str) -> tuple[list[dict[str, object]], str | None]:
    try:
        rows = []
        for index, (name, facts) in enumerate(ftp.mlsd(path)):
            if index >= MAX_ENTRIES_PER_DIRECTORY:
                break
            if name in (".", ".."):
                continue
            rows.append(normalize_entry(path, name, facts, "MLSD"))
        return rows, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def list_directory_nlst(ftp: ftplib.FTP, path: str) -> tuple[list[dict[str, object]], str | None]:
    try:
        raw_names = ftp.nlst(path)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    rows = []
    for raw in raw_names[:MAX_ENTRIES_PER_DIRECTORY]:
        name = PurePosixPath(raw.rstrip("/")).name
        if name in ("", ".", ".."):
            continue
        entry = normalize_entry(path, name, None, "NLST")
        full = str(entry["path"])
        try:
            entry["size"] = str(ftp.size(full))
            entry["type"] = "file"
        except Exception:
            pass
        try:
            reply = ftp.sendcmd(f"MDTM {full}")
            entry["modify"] = reply.split(maxsplit=1)[1] if " " in reply else reply
        except Exception:
            pass
        if entry.get("type") is None:
            original = ftp.pwd()
            try:
                ftp.cwd(full)
                entry["type"] = "dir"
            except Exception:
                entry["type"] = "unknown"
            finally:
                try:
                    ftp.cwd(original)
                except Exception:
                    pass
        rows.append(entry)
    return rows, None


def list_directory(ftp: ftplib.FTP, path: str) -> dict[str, object]:
    rows, mlsd_error = list_directory_mlsd(ftp, path)
    source = "MLSD"
    nlst_error = None
    if mlsd_error is not None:
        rows, nlst_error = list_directory_nlst(ftp, path)
        source = "NLST" if nlst_error is None else "NONE"
    rows.sort(key=lambda x: str(x["path"]))
    return {
        "path": path,
        "source": source,
        "mlsd_error": mlsd_error,
        "nlst_error": nlst_error,
        "entry_count": len(rows),
        "truncated_at": MAX_ENTRIES_PER_DIRECTORY,
        "entries": rows,
    }


def main() -> int:
    manifest: dict[str, object] = {
        "worker_version": WORKER_VERSION,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "credential_policy": {
            "user_specific_credentials_used": False,
            "public_fixed_username": USER,
            "blank_password": True,
        },
        "body_retrieval_performed": False,
        "host": HOST,
        "bounds": {
            "max_directory_depth": 1,
            "max_entries_per_directory": MAX_ENTRIES_PER_DIRECTORY,
            "max_child_directories": MAX_CHILD_DIRECTORIES,
        },
        "connection": {"status": "NOT_ATTEMPTED"},
        "root": None,
        "children": [],
    }
    try:
        with ftplib.FTP(timeout=TIMEOUT) as ftp:
            ftp.connect(HOST, 21)
            ftp.login(USER, PASSWORD)
            manifest["connection"] = {
                "status": "CONNECTED",
                "pwd": ftp.pwd(),
                "syst": safe_cmd(ftp, "SYST"),
                "feat": safe_cmd(ftp, "FEAT"),
            }
            root = list_directory(ftp, "/")
            manifest["root"] = root
            dirs = [
                e for e in root["entries"]
                if e.get("type") in {"dir", "cdir", "pdir"}
            ][:MAX_CHILD_DIRECTORIES]
            children = []
            for entry in dirs:
                path = str(entry["path"])
                children.append(list_directory(ftp, path))
            manifest["children"] = children
    except Exception as exc:
        manifest["connection"] = {
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }

    all_entries: list[dict[str, object]] = []
    root_obj = manifest.get("root")
    if isinstance(root_obj, dict):
        all_entries.extend(root_obj.get("entries", []))
    for child in manifest.get("children", []):
        if isinstance(child, dict):
            all_entries.extend(child.get("entries", []))

    candidates = [e for e in all_entries if e.get("candidate_reasons")]
    historical_candidates = [e for e in candidates if historical_candidate(e)]
    manifest["summary"] = {
        "total_entries_observed": len(all_entries),
        "child_directories_enumerated": len(manifest.get("children", [])),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "historical_candidate_count": len(historical_candidates),
        "historical_candidates": historical_candidates,
        "success_condition_met": bool(historical_candidates),
        "historical_candidate_bodies_opened": False,
        "admission_authority_granted": False,
    }
    manifest["evidence_digest_sha256"] = sha256_json(manifest)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    s = manifest["summary"]
    print("worker_version=", WORKER_VERSION)
    print("connection_status=", manifest["connection"].get("status"))
    print("total_entries_observed=", s["total_entries_observed"])
    print("child_directories_enumerated=", s["child_directories_enumerated"])
    print("candidate_count=", s["candidate_count"])
    print("candidate_paths=", [e["path"] for e in s["candidates"]])
    print("historical_candidate_count=", s["historical_candidate_count"])
    print("historical_candidate_paths=", [e["path"] for e in s["historical_candidates"]])
    print("success_condition_met=", s["success_condition_met"])
    print("evidence_digest_sha256=", manifest["evidence_digest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
