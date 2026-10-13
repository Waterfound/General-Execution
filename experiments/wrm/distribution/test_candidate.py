"""Offline/isolated RMA-DIST-001 adversarial tests, stdlib only."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from candidate import ContractError, MockEvent, OfflineLedger, simulated_economics


def event(rev, kind, eid=None, sid="sim-org-a", plan="candidate-basic"):
    return MockEvent(eid or f"sim-event-{rev}", sid, rev, kind, plan)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "candidate.sqlite3"
        self.ledger = OfflineLedger(self.path)

    def test_no_entitlement_before_payment(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.assertEqual(self.ledger.state("sim-org-a"), "pending")
        self.assertFalse(self.ledger.entitled("sim-org-a"))

    def test_successful_simulation_entitles(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.assertEqual(self.ledger.ingest_mock(event(2, "invoice.paid"))["state"], "active")
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_duplicate_webhook_idempotent(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        self.assertEqual(self.ledger.ingest_mock(event(2, "invoice.paid"))["outcome"], "duplicate")
        self.assertTrue(self.ledger.reconcile()["healthy"])

    def test_duplicate_payload_conflict_rejected(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        with self.assertRaises(ContractError):
            self.ledger.ingest_mock(event(1, "subscription.created", plan="candidate-team"))

    def test_duplicate_revision_conflict_rejected(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        with self.assertRaises(ContractError):
            self.ledger.ingest_mock(event(1, "subscription.created", eid="sim-other"))

    def test_out_of_order_does_not_grant_early(self):
        self.assertEqual(self.ledger.ingest_mock(event(2, "invoice.paid"))["outcome"], "deferred_gap")
        self.assertFalse(self.ledger.entitled("sim-org-a"))
        self.assertEqual(self.ledger.reconcile()["pending_gap_events"], 1)
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.assertTrue(self.ledger.entitled("sim-org-a"))
        self.assertEqual(self.ledger.reconcile()["pending_gap_events"], 0)

    def test_payment_failure_revokes(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        self.ledger.ingest_mock(event(3, "invoice.failed"))
        self.assertEqual(self.ledger.state("sim-org-a"), "past_due")
        self.assertFalse(self.ledger.entitled("sim-org-a"))

    def test_recovery_from_past_due(self):
        for n, kind in enumerate(["subscription.created", "invoice.paid", "invoice.failed", "invoice.paid"], 1):
            self.ledger.ingest_mock(event(n, kind))
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_cancellation_irreversible_under_stale_invoice(self):
        for n, kind in enumerate(["subscription.created", "invoice.paid", "subscription.canceled", "invoice.paid"], 1):
            self.ledger.ingest_mock(event(n, kind))
        self.assertEqual(self.ledger.state("sim-org-a"), "canceled")
        self.assertFalse(self.ledger.entitled("sim-org-a"))

    def test_persisted_cold_restart(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        restarted = OfflineLedger(self.path)
        self.assertTrue(restarted.entitled("sim-org-a"))
        self.assertEqual(restarted.ingest_mock(event(2, "invoice.paid"))["outcome"], "duplicate")

    def test_reconcile_detects_and_repairs_corrupt_projection(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute("UPDATE mock_subscriptions SET state='past_due'")
        self.assertFalse(self.ledger.entitled("sim-org-a"))
        self.assertFalse(self.ledger.reconcile()["healthy"])
        self.assertTrue(self.ledger.reconcile(repair=True)["repaired"])
        self.assertTrue(self.ledger.reconcile()["healthy"])
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_only_synthetic_identifiers(self):
        with self.assertRaises(ContractError):
            self.ledger.ingest_mock(MockEvent("actual@customer.com", "sim-org-a", 1, "subscription.created", "candidate-basic"))
        with self.assertRaises(ContractError):
            self.ledger.track_synthetic("sim-e1", "email@example.com", "interested")

    def test_unknown_event_denied(self):
        with self.assertRaises(ContractError):
            self.ledger.ingest_mock(event(1, "refund.approved"))

    def test_unknown_plan_denied(self):
        with self.assertRaises(ContractError):
            self.ledger.ingest_mock(event(1, "subscription.created", plan="secret-enterprise"))

    def test_revision_jump_no_privilege(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(3, "invoice.paid"))
        self.assertFalse(self.ledger.entitled("sim-org-a"))
        self.ledger.ingest_mock(event(2, "invoice.failed"))
        self.assertTrue(self.ledger.entitled("sim-org-a"))  # rev3 is newer evidence

    def test_synthetic_funnel_deduplicated(self):
        self.assertEqual(self.ledger.track_synthetic("sim-a", "sim-journey-a", "discovered"), "recorded")
        self.assertEqual(self.ledger.track_synthetic("sim-a", "sim-journey-a", "discovered"), "duplicate")
        self.assertEqual(self.ledger.track_synthetic("sim-b", "sim-journey-a", "discovered"), "duplicate_stage")
        self.assertEqual(self.ledger.funnel_counts()["discovered"], 1)

    def test_funnel_event_collision_denied(self):
        self.ledger.track_synthetic("sim-a", "sim-journey-a", "discovered")
        with self.assertRaises(ContractError):
            self.ledger.track_synthetic("sim-a", "sim-journey-a", "activated")

    def test_simulated_checkout_never_called_payment(self):
        self.ledger.track_synthetic("sim-a", "sim-journey-a", "checkout_simulated_started")
        self.ledger.track_synthetic("sim-b", "sim-journey-a", "checkout_simulated_completed")
        self.assertEqual(self.ledger.funnel_counts()["checkout_simulated_completed"], 1)
        self.assertEqual(self.ledger.state("sim-org-a"), "unknown")
        self.assertFalse(self.ledger.entitled("sim-org-a"))

    def test_economics_break_even(self):
        data = simulated_economics(price_usd="49", customers=10, monthly_churn="0.05", fee_pct="0.05",
                                   fee_fixed_usd="0.50", infra_usd="20", variable_usd="3", support_usd="2", cac_usd="20")
        self.assertEqual(data["gross_usd"], "490.00")
        self.assertEqual(data["payment_fees_usd"], "29.50")
        self.assertEqual(data["contribution_usd"], "380.50")
        self.assertEqual(data["break_even_customers"], 1)
        self.assertTrue(data["assumption_only"])

    def test_unprofitable_scenario_no_break_even(self):
        data = simulated_economics(price_usd="1", customers=100, monthly_churn="0.20", fee_pct="0.05",
                                   fee_fixed_usd="0.50", infra_usd="20", variable_usd="2", support_usd="2", cac_usd="20")
        self.assertIsNone(data["break_even_customers"])

    def test_negative_or_nonfinite_assumptions_rejected(self):
        params = dict(price_usd="49", customers=10, monthly_churn="0.03", fee_pct="0.05",
                      fee_fixed_usd="0.50", infra_usd="20", variable_usd="3", support_usd="2", cac_usd="20")
        for changes in ({"price_usd": "NaN"}, {"monthly_churn": "2"}, {"customers": -1}, {"infra_usd": "-2"}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                simulated_economics(**(params | changes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
