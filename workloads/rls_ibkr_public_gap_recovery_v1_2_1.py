#!/usr/bin/env python3
"""Parser-hygiene successor to credential-free RLS IBKR gap recovery V1.2.

V1.2.1 changes no source, target month, threshold, archive selection, credential,
or admission rule. It only accepts the IBKR #EOF line under either LF or CRLF
framing, preventing a platform line-ending false negative.
"""
from __future__ import annotations

import re

import rls_ibkr_public_gap_recovery_v1_2 as v12

WORKER_VERSION = "RLS-IBKR-PUBLIC-GAP-RECOVERY-WORKER-v1.2.1"
EOF_CRLF_SAFE = re.compile(rb"(?m)^#EOF(?:\|[^\r\n]*)?\r?$")


def main() -> int:
    v12.WORKER_VERSION = WORKER_VERSION
    v12.EOF_RE = EOF_CRLF_SAFE
    return v12.main()


if __name__ == "__main__":
    raise SystemExit(main())
