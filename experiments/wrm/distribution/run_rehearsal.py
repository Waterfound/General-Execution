"""Print auditable, deterministic (synthetic) contract and economics rehearsal JSON."""
import json
import tempfile
from pathlib import Path

from candidate import MockEvent, OfflineLedger, SCHEMA, simulated_economics


def execute():
    with tempfile.TemporaryDirectory() as directory:
        db = Path(directory) / "candidate.sqlite3"
        ledger = OfflineLedger(db)
        journey = "sim-inbound-1"
        for i, stage in enumerate(("discovered", "interested", "onboarding_started", "activated", "value_delivered", "checkout_simulated_started", "checkout_simulated_completed"), 1):
            ledger.track_synthetic(f"sim-funnel-{i}", journey, stage)
        sid = "sim-subscription-1"
        e = lambda i, kind: MockEvent(f"sim-billing-{i}", sid, i, kind, "candidate-basic")
        out_of_order = ledger.ingest_mock(e(2, "invoice.paid"))
        created = ledger.ingest_mock(e(1, "subscription.created"))
        granted = ledger.entitled(sid)
        restarted = OfflineLedger(db)
        cold_restart = restarted.entitled(sid)
        duplicate = restarted.ingest_mock(e(2, "invoice.paid"))
        cancelled = restarted.ingest_mock(e(3, "subscription.canceled"))
        after_cancel = restarted.entitled(sid)
        scenarios = {
            "conservative": dict(price_usd="29", customers=3, monthly_churn="0.10", fee_pct="0.05", fee_fixed_usd="0.50", infra_usd="30", variable_usd="5", support_usd="6", cac_usd="30"),
            "central": dict(price_usd="49", customers=10, monthly_churn="0.05", fee_pct="0.05", fee_fixed_usd="0.50", infra_usd="20", variable_usd="3", support_usd="2", cac_usd="20"),
            "optimistic": dict(price_usd="99", customers=25, monthly_churn="0.02", fee_pct="0.05", fee_fixed_usd="0.50", infra_usd="20", variable_usd="2", support_usd="1", cac_usd="10"),
        }
        return {
            "schema": SCHEMA,
            "evidence_class": "SYNTHETIC_MOCK_ONLY",
            "external_payments": 0, "actual_customers": 0, "real_revenue_usd": "0.00",
            "distribution": {"funnel_counts": ledger.funnel_counts()},
            "billing": {"gap_deferred": out_of_order["outcome"] == "deferred_gap",
                        "gap_recovered": created["state"] == "active",
                        "entitlement_granted_after_replay": granted,
                        "entitlement_survives_cold_restart": cold_restart,
                        "duplicate_idempotent": duplicate["outcome"] == "duplicate",
                        "canceled_state": cancelled["state"],
                        "entitlement_revoked_after_cancel": not after_cancel,
                        "reconciliation": restarted.reconcile()},
            "economics": {label: simulated_economics(**parameters) for label, parameters in scenarios.items()},
        }


if __name__ == "__main__":
    print(json.dumps(execute(), sort_keys=True, indent=2))
