"""Bounded red/green regressions for mock tenant isolation and crash safety."""
import random
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from candidate import ContractError, MockEvent, OfflineLedger


def event(rev, kind, *, sid="sim-org-a"):
    return MockEvent(f"sim-{sid}-{rev}", sid, rev, kind, "candidate-basic")


class RecoveryHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "mock.sqlite3"
        self.ledger = OfflineLedger(self.path)

    def test_corruption_isolated_to_subscription(self):
        for sid in ("sim-org-a", "sim-org-b"):
            self.ledger.ingest_mock(event(1, "subscription.created", sid=sid))
            self.ledger.ingest_mock(event(2, "invoice.paid", sid=sid))
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute("UPDATE mock_events SET kind='invoice.failed' WHERE subscription_id='sim-org-b' AND revision=2")
        self.assertFalse(self.ledger.reconcile()["healthy"])
        self.assertFalse(self.ledger.entitled("sim-org-b"))
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_repair_receipt_reports_post_repair_health(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute("UPDATE mock_subscriptions SET state='past_due'")
        receipt = self.ledger.reconcile(repair=True)
        self.assertTrue(receipt["repaired"])
        self.assertTrue(receipt["healthy"])
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_atomic_rollback_on_projection_failure(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute("CREATE TRIGGER fail_projection BEFORE UPDATE ON mock_subscriptions "
                           "BEGIN SELECT RAISE(ABORT, 'synthetic outage'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.ledger.ingest_mock(event(2, "invoice.paid"))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM mock_events").fetchone()[0], 1)
            with db:
                db.execute("DROP TRIGGER fail_projection")
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        self.assertTrue(self.ledger.entitled("sim-org-a"))

    def test_128_permutations_duplicate_delivery_and_cold_reopen(self):
        events = [event(i, k) for i, k in enumerate((
            "subscription.created", "invoice.paid", "invoice.failed",
            "invoice.paid", "subscription.canceled", "invoice.paid"), 1)]
        for seed in range(128):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as dirname:
                ledger = OfflineLedger(Path(dirname) / "replay.sqlite3")
                order = events[:]
                random.Random(seed).shuffle(order)
                for item in order:
                    ledger.ingest_mock(item)
                    ledger.ingest_mock(item)
                recovered = OfflineLedger(ledger.path)
                self.assertEqual(recovered.state("sim-org-a"), "canceled")
                self.assertFalse(recovered.entitled("sim-org-a"))
                self.assertTrue(recovered.reconcile()["healthy"])
                self.assertEqual(recovered.reconcile()["pending_gap_events"], 0)

    def test_scoped_repair_and_invalid_identity_fail_closed(self):
        self.ledger.ingest_mock(event(1, "subscription.created"))
        self.ledger.ingest_mock(event(2, "invoice.paid"))
        with self.assertRaises(ContractError):
            self.ledger.reconcile(subscription_id="buyer@example.com")
        with self.assertRaises(ContractError):
            self.ledger.reconcile(subscription_id="sim-org-a", repair=True)
        self.assertFalse(self.ledger.entitled("sim-unknown"))
        self.assertTrue(self.ledger.entitled("sim-org-a"))


if __name__ == "__main__":
    unittest.main()
