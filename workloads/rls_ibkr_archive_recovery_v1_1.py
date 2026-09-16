#!/usr/bin/env python3
"""Metadata-only successor to RLS IBKR archive recovery worker V1.

V1 discovered, from the already hash-bound public archive manifest, that members use
YYMMDD_shorting.tsv names. V1.1 changes only filename-date parsing and delegates all
other download, hashing, coverage, Wayback, safety, and output behavior to V1.
"""
from __future__ import annotations

from datetime import date
import re

import rls_ibkr_archive_recovery_v1 as v1


WORKER_VERSION = "RLS-IBKR-USA-ARCHIVE-RECOVERY-WORKER-v1.1"
YYMMDD_SHORTING = re.compile(r"^(\d{2})(\d{2})(\d{2})_shorting\.tsv$", re.I)


def filename_date_v1_1(name: str) -> str | None:
    legacy = v1.filename_date(name)
    if legacy is not None:
        return legacy
    base = name.rsplit("/", 1)[-1]
    match = YYMMDD_SHORTING.fullmatch(base)
    if match is None:
        return None
    try:
        return date(
            2000 + int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        ).isoformat()
    except ValueError:
        return None


def main() -> int:
    v1.WORKER_VERSION = WORKER_VERSION
    v1.filename_date = filename_date_v1_1
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
