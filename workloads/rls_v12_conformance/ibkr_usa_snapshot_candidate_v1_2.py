from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re

from .engine import ValidationError, canonical_json_sha256


PROTOCOL_VERSION = "RLS-IBKR-USA-SNAPSHOT-CANDIDATE-v1.2"
HEADER = "#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|"
_BOF = re.compile(r"^#BOF\|(20\d{2})\.(\d{2})\.(\d{2})\|(\d{2}):(\d{2}):(\d{2})$")
_EOF = re.compile(r"^#EOF\|(\d+)\|?$")
_SIGNED_NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_INTEGER = re.compile(r"^\d+$")
_LOWER_BOUND = re.compile(r"^>(\d+)$")
_RATE_MISSING = {"", "NA"}


@dataclass(frozen=True)
class IBKRUSASnapshotRowV12:
    symbol: str
    currency: str
    name: str
    con: int
    isin: str | None
    figi: str | None
    rebate_rate_percent: str | None
    fee_rate_percent: str | None
    fee_rate_bps: str | None
    availability_state: str
    available_raw: str | None


@dataclass(frozen=True)
class IBKRUSASnapshotResultV12:
    protocol_version: str
    structurally_valid: bool
    source_sha256: str
    snapshot_date: str
    snapshot_time: str
    row_count: int
    distinct_contracts: int
    observed_available_rows: int
    observed_unavailable_rows: int
    missing_availability_rows: int
    missing_fee_rows: int
    missing_rebate_rows: int
    paired_fee_availability_rows: int
    availability_with_missing_fee_rows: int
    normalized_rows_sha256: str
    rows: tuple[IBKRUSASnapshotRowV12, ...]


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _parse_rate(value: str, label: str) -> tuple[str | None, str | None]:
    text = value.strip()
    if text in _RATE_MISSING:
        return None, None
    if _SIGNED_NUMBER.fullmatch(text) is None:
        raise ValidationError(f"{label} contains undocumented non-numeric literal")
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{label} is not numeric") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{label} must be finite")
    pct = _canonical_decimal(parsed)
    bps = _canonical_decimal(parsed * Decimal(100))
    return pct, bps


def _parse_availability(value: str) -> tuple[str, str | None]:
    text = value.strip()
    if text == "":
        return "MISSING", None
    lower = _LOWER_BOUND.fullmatch(text)
    if lower:
        amount = int(lower.group(1))
        if amount <= 0:
            raise ValidationError("AVAILABLE lower-bound must be positive")
        return "OBSERVED_AVAILABLE_LOWER_BOUND", text
    if _INTEGER.fullmatch(text):
        amount = int(text)
        if amount == 0:
            return "OBSERVED_UNAVAILABLE", text
        return "OBSERVED_AVAILABLE", text
    raise ValidationError("AVAILABLE contains undocumented literal")


def _parse_bof(line: str) -> tuple[date, time]:
    match = _BOF.fullmatch(line)
    if match is None:
        raise ValidationError("first nonblank line must match frozen #BOF shape")
    try:
        d = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        t = time(int(match.group(4)), int(match.group(5)), int(match.group(6)))
    except ValueError as exc:
        raise ValidationError("#BOF contains invalid date/time") from exc
    return d, t


def _normalize_row(line: str, index: int) -> IBKRUSASnapshotRowV12:
    parts = line.split("|")
    if len(parts) != 10 or parts[-1] != "":
        raise ValidationError(f"row {index} does not match nine-field trailing-delimiter schema")
    sym, cur, name, con_text, isin_text, rebate_text, fee_text, available_text, figi_text, _ = parts
    if not sym.strip():
        raise ValidationError(f"row {index} SYM must be non-empty")
    if not cur.strip():
        raise ValidationError(f"row {index} CUR must be non-empty")
    if _INTEGER.fullmatch(con_text.strip()) is None or int(con_text.strip()) <= 0:
        raise ValidationError(f"row {index} CON must be a positive integer")

    rebate_pct, _ = _parse_rate(rebate_text, f"row {index} REBATERATE")
    fee_pct, fee_bps = _parse_rate(fee_text, f"row {index} FEERATE")
    availability_state, available_raw = _parse_availability(available_text)

    return IBKRUSASnapshotRowV12(
        symbol=sym.strip(),
        currency=cur.strip(),
        name=name,
        con=int(con_text.strip()),
        isin=isin_text.strip() or None,
        figi=figi_text.strip() or None,
        rebate_rate_percent=rebate_pct,
        fee_rate_percent=fee_pct,
        fee_rate_bps=fee_bps,
        availability_state=availability_state,
        available_raw=available_raw,
    )


def validate_ibkr_usa_snapshot_v12(raw_bytes: bytes) -> IBKRUSASnapshotResultV12:
    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise ValidationError("usa.txt source bytes must be non-empty bytes")
    source_hash = sha256(raw_bytes).hexdigest()
    try:
        text = raw_bytes.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError("usa.txt must be strict UTF-8-compatible text") from exc

    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if len(lines) < 3:
        raise ValidationError("usa.txt snapshot is too short")

    snapshot_date, snapshot_time = _parse_bof(lines[0])
    if lines[1] != HEADER:
        raise ValidationError("usa.txt header differs from frozen v1.2 schema")
    eof_match = _EOF.fullmatch(lines[-1])
    if eof_match is None:
        raise ValidationError("last nonblank line must match frozen #EOF shape")
    expected_rows = int(eof_match.group(1))

    body = lines[2:-1]
    if any(not line.strip() for line in body):
        raise ValidationError("blank lines inside usa.txt body are forbidden")
    if expected_rows != len(body):
        raise ValidationError("#EOF row count does not equal body row count")

    rows: list[IBKRUSASnapshotRowV12] = []
    seen_cons: set[int] = set()
    for index, line in enumerate(body, start=1):
        row = _normalize_row(line, index)
        if row.con in seen_cons:
            raise ValidationError(f"duplicate CON in snapshot: {row.con}")
        seen_cons.add(row.con)
        rows.append(row)

    normalized_payload = [
        {
            "symbol": row.symbol,
            "currency": row.currency,
            "name": row.name,
            "con": row.con,
            "isin": row.isin,
            "figi": row.figi,
            "rebate_rate_percent": row.rebate_rate_percent,
            "fee_rate_percent": row.fee_rate_percent,
            "fee_rate_bps": row.fee_rate_bps,
            "availability_state": row.availability_state,
            "available_raw": row.available_raw,
        }
        for row in rows
    ]

    observed_available = sum(
        row.availability_state in {"OBSERVED_AVAILABLE", "OBSERVED_AVAILABLE_LOWER_BOUND"}
        for row in rows
    )
    observed_unavailable = sum(row.availability_state == "OBSERVED_UNAVAILABLE" for row in rows)
    missing_availability = sum(row.availability_state == "MISSING" for row in rows)
    missing_fee = sum(row.fee_rate_percent is None for row in rows)
    missing_rebate = sum(row.rebate_rate_percent is None for row in rows)
    paired = sum(
        row.fee_rate_percent is not None and row.availability_state != "MISSING"
        for row in rows
    )
    availability_with_missing_fee = sum(
        row.fee_rate_percent is None
        and row.availability_state in {"OBSERVED_AVAILABLE", "OBSERVED_AVAILABLE_LOWER_BOUND", "OBSERVED_UNAVAILABLE"}
        for row in rows
    )

    return IBKRUSASnapshotResultV12(
        protocol_version=PROTOCOL_VERSION,
        structurally_valid=True,
        source_sha256=source_hash,
        snapshot_date=snapshot_date.isoformat(),
        snapshot_time=snapshot_time.isoformat(),
        row_count=len(rows),
        distinct_contracts=len(seen_cons),
        observed_available_rows=observed_available,
        observed_unavailable_rows=observed_unavailable,
        missing_availability_rows=missing_availability,
        missing_fee_rows=missing_fee,
        missing_rebate_rows=missing_rebate,
        paired_fee_availability_rows=paired,
        availability_with_missing_fee_rows=availability_with_missing_fee,
        normalized_rows_sha256=canonical_json_sha256(normalized_payload),
        rows=tuple(rows),
    )
