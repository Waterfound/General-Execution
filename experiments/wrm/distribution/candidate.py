"""RMA-DIST-001 offline commercial adapter proof.

No HTTP handlers, providers, accounts, PII collection, payment rails or external I/O.
Only mock provider events and synthetic funnel identifiers are admitted.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import ceil
from pathlib import Path
import json
import re
import sqlite3

SCHEMA = "rma.distribution.candidate.v1"
KINDS = {"subscription.created", "invoice.paid", "invoice.failed", "subscription.canceled"}
FUNNEL = {"discovered", "interested", "onboarding_started", "activated", "value_delivered", "checkout_simulated_started", "checkout_simulated_completed", "retained", "churned"}
SYNTHETIC = re.compile(r"^sim-[a-z0-9-]{1,60}$")


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class MockEvent:
    event_id: str
    subscription_id: str
    revision: int
    kind: str
    plan_id: str

    def validate(self) -> None:
        for name in ("event_id", "subscription_id"):
            if not SYNTHETIC.fullmatch(getattr(self, name)):
                raise ContractError(f"{name} must be synthetic")
        if self.kind not in KINDS or not self.plan_id in {"candidate-basic", "candidate-team"}:
            raise ContractError("unknown event or candidate plan")
        if type(self.revision) is not int or not 1 <= self.revision <= 1_000_000:
            raise ContractError("revision must be a positive integer")
        if self.revision == 1 and self.kind != "subscription.created":
            raise ContractError("revision 1 must create subscription")
        if self.revision > 1 and self.kind == "subscription.created":
            raise ContractError("subscription.created must be revision 1")

    def digest(self) -> str:
        return sha256(json.dumps(asdict(self), sort_keys=True,
                                 separators=(",", ":")).encode()).hexdigest()



class OfflineLedger:
    """Persist mock events, enforce idempotency and ordered entitlements in SQLite."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS mock_events (
                    event_id TEXT PRIMARY KEY, subscription_id TEXT NOT NULL,
                    revision INTEGER NOT NULL, kind TEXT NOT NULL,
                    plan_id TEXT NOT NULL, digest TEXT NOT NULL, applied INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(subscription_id, revision)
                );
                CREATE TABLE IF NOT EXISTS mock_subscriptions (
                    subscription_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL,
                    revision INTEGER NOT NULL, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS synthetic_funnel (
                    event_id TEXT PRIMARY KEY, journey_id TEXT NOT NULL,
                    stage TEXT NOT NULL, UNIQUE(journey_id, stage)
                );
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _advance(state: str | None, kind: str) -> str:
        if state is None:
            if kind != "subscription.created":
                raise ContractError("first event must create subscription")
            return "pending"
        if kind == "subscription.created":
            raise ContractError("duplicate subscription creation")
        if state == "canceled":
            return "canceled"  # Terminal; delayed invoice cannot regrant entitlement.
        return {
            "invoice.paid": "active",
            "invoice.failed": "past_due",
            "subscription.canceled": "canceled",
        }[kind]

    def ingest_mock(self, event: MockEvent) -> dict:
        event.validate()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT digest FROM mock_events WHERE event_id=?", (event.event_id,)).fetchone()
            if old:
                if old["digest"] != event.digest():
                    raise ContractError("conflicting duplicate webhook event_id")
                return {"outcome": "duplicate", "state": self.state(event.subscription_id)}
            slot = db.execute("SELECT event_id FROM mock_events WHERE subscription_id=? AND revision=?", (event.subscription_id, event.revision)).fetchone()
            if slot:
                raise ContractError("conflicting event revision")
            existing = db.execute("SELECT DISTINCT plan_id FROM mock_events WHERE subscription_id=?", (event.subscription_id,)).fetchone()
            if existing and existing["plan_id"] != event.plan_id:
                raise ContractError("plan changed without approved plan-change contract")
            db.execute("INSERT INTO mock_events (event_id, subscription_id, revision, kind, plan_id, digest) VALUES (?,?,?,?,?,?)",
                       (event.event_id, event.subscription_id, event.revision, event.kind, event.plan_id, event.digest()))
            self._drain(db, event.subscription_id)
            state = db.execute("SELECT state, revision FROM mock_subscriptions WHERE subscription_id=?", (event.subscription_id,)).fetchone()
            return {"outcome": "applied" if state and state["revision"] >= event.revision else "deferred_gap",
                    "state": state["state"] if state else "unknown"}

    def _drain(self, db, sid: str) -> None:
        while True:
            current = db.execute("SELECT * FROM mock_subscriptions WHERE subscription_id=?", (sid,)).fetchone()
            next_rev = current["revision"] + 1 if current else 1
            next_event = db.execute("SELECT * FROM mock_events WHERE subscription_id=? AND revision=?", (sid, next_rev)).fetchone()
            if next_event is None:
                break
            state = self._advance(current["state"] if current else None, next_event["kind"])
            db.execute("INSERT INTO mock_subscriptions (subscription_id, plan_id, revision, state) VALUES (?,?,?,?) "
                       "ON CONFLICT(subscription_id) DO UPDATE SET revision=excluded.revision, state=excluded.state",
                       (sid, next_event["plan_id"], next_rev, state))
            db.execute("UPDATE mock_events SET applied=1 WHERE event_id=?", (next_event["event_id"],))

    def state(self, sid: str) -> str:
        if not SYNTHETIC.fullmatch(sid):
            raise ContractError("subscription_id must be synthetic")
        with self._db() as db:
            s = db.execute("SELECT state FROM mock_subscriptions WHERE subscription_id=?", (sid,)).fetchone()
            return s["state"] if s else "unknown"

    def reconcile(self, *, repair: bool = False) -> dict:
        """Reconstruct expected projections from immutable mock events.

        Entitlement is denied if projections diverge. Only an explicit local repair
        can rewrite a corrupted projection; no external provider is consulted.
        """
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            events = db.execute("SELECT * FROM mock_events ORDER BY subscription_id, revision").fetchall()
            expected = {}
            grouped = {}
            for e in events:
                grouped.setdefault(e["subscription_id"], []).append(e)
            invalid_digests = [e["event_id"] for e in events
                               if e["digest"] != MockEvent(
                                   e["event_id"], e["subscription_id"], e["revision"],
                                   e["kind"], e["plan_id"]
                               ).digest()]
            if invalid_digests:
                if repair:
                    raise ContractError("refuse to repair corrupted source event history")
                return {"healthy": False, "repaired": False,
                        "integrity_violations": sorted(invalid_digests),
                        "mismatched_subscriptions": sorted(grouped),
                        "subscriptions": 0, "pending_gap_events": 0}
            for sid, batch in grouped.items():
                rev, state, plan = 0, None, batch[0]["plan_id"]
                for e in batch:
                    if e["revision"] != rev + 1:
                        break  # Gaps do not grant any future entitlement.
                    state = self._advance(state, e["kind"])
                    rev += 1
                if state is not None:
                    expected[sid] = (plan, rev, state)
            actual = {r["subscription_id"]: (r["plan_id"], r["revision"], r["state"])
                      for r in db.execute("SELECT * FROM mock_subscriptions")}
            mismatches = sorted(sid for sid in set(expected) | set(actual) if expected.get(sid) != actual.get(sid))
            incorrect_applied = [e["subscription_id"] for e in events if bool(e["applied"]) !=
                                 (e["revision"] <= expected.get(e["subscription_id"], (None, 0, None))[1])]
            mismatches = sorted(set(mismatches) | set(incorrect_applied))
            if repair and mismatches:
                db.execute("DELETE FROM mock_subscriptions")
                db.executemany("INSERT INTO mock_subscriptions VALUES (?,?,?,?)",
                               [(sid, *details) for sid, details in expected.items()])
                db.execute("UPDATE mock_events SET applied=0")
                for sid, (_, revision, _) in expected.items():
                    db.execute("UPDATE mock_events SET applied=1 WHERE subscription_id=? AND revision<=?", (sid, revision))
            return {"healthy": not mismatches, "repaired": repair and bool(mismatches),
                    "mismatched_subscriptions": mismatches, "subscriptions": len(expected),
                    "pending_gap_events": sum(len(grouped[sid]) - expected.get(sid, (None, 0, None))[1] for sid in grouped)}

    def entitled(self, sid: str) -> bool:
        try:
            return self.reconcile()["healthy"] and self.state(sid) == "active"
        except sqlite3.Error:
            # Store outage or missing schema must never grant mock access.
            return False

    def track_synthetic(self, event_id: str, journey_id: str, stage: str) -> str:
        if not SYNTHETIC.fullmatch(event_id) or not SYNTHETIC.fullmatch(journey_id) or stage not in FUNNEL:
            raise ContractError("synthetic-only event id/journey id and allowlisted stage required")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            duplicate = db.execute("SELECT * FROM synthetic_funnel WHERE event_id=?", (event_id,)).fetchone()
            if duplicate:
                if (duplicate["journey_id"], duplicate["stage"]) != (journey_id, stage):
                    raise ContractError("conflicting duplicate funnel event")
                return "duplicate"
            already = db.execute("SELECT * FROM synthetic_funnel WHERE journey_id=? AND stage=?", (journey_id, stage)).fetchone()
            if already:
                return "duplicate_stage"
            db.execute("INSERT INTO synthetic_funnel VALUES (?,?,?)", (event_id, journey_id, stage))
        return "recorded"

    def funnel_counts(self) -> dict:
        with self._db() as db:
            rows = db.execute("SELECT stage, COUNT(*) AS n FROM synthetic_funnel GROUP BY stage").fetchall()
        return {key: next((r["n"] for r in rows if r["stage"] == key), 0) for key in sorted(FUNNEL)}


def simulated_economics(*, price_usd: str, customers: int, monthly_churn: str,
                        fee_pct: str, fee_fixed_usd: str, infra_usd: str,
                        variable_usd: str, support_usd: str, cac_usd: str) -> dict:
    """Steady-state scenario only, not observed payment, retention or WTP."""
    if type(customers) is not int or customers < 0:
        raise ContractError("customers must be nonnegative integer")
    try:
        p, churn, f, fixed, infra, var, sup, cac = map(Decimal, (price_usd, monthly_churn, fee_pct,
                                                                    fee_fixed_usd, infra_usd, variable_usd,
                                                                    support_usd, cac_usd))
    except Exception as exc:
        raise ContractError("invalid decimal") from exc
    if not all(x.is_finite() for x in (p, churn, f, fixed, infra, var, sup, cac)):
        raise ContractError("nonfinite economics")
    if p <= 0 or not (0 <= churn <= 1) or not (0 <= f < 1) or min(fixed, infra, var, sup, cac) < 0:
        raise ContractError("invalid economics assumptions")
    net_per = p * (1 - f) - fixed - var - sup - (cac * churn)
    monthly_contribution = customers * net_per - infra
    break_even = ceil(infra / net_per) if net_per > 0 else None
    money = lambda x: str(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return {"assumption_only": True, "scope": "monthly_steady_state_replace_churned_customers",
            "price_usd": money(p), "customers": customers,
            "gross_usd": money(customers * p),
            "payment_fees_usd": money(customers * (p * f + fixed)),
            "variable_support_usd": money(customers * (var + sup)),
            "replacement_acquisition_usd": money(customers * churn * cac),
            "fixed_infra_usd": money(infra),
            "contribution_usd": money(monthly_contribution),
            "break_even_customers": break_even}
