import json
import unittest
from pathlib import Path

from accounting_data_path_audit import audit


ROOT = Path(__file__).parent


class AccountingDataPathAuditTest(unittest.TestCase):
    def test_truth_labeled_fixture(self):
        receipts = json.loads((ROOT / "accounting_data_path_fixture.json").read_text())
        truth = {
            tuple(item)
            for item in json.loads(
                (ROOT / "accounting_data_path_ground_truth.json").read_text()
            )
        }
        findings = audit(receipts)
        observed = {(item["record_key"], item["code"]) for item in findings}

        self.assertEqual(truth, observed)
        self.assertTrue(all(item["evidence"] for item in findings))
        evidence_ids = {e for item in findings for e in item["evidence"]}
        self.assertEqual(
            {
                "qbo-1",
                "karbon-1a",
                "karbon-1b",
                "xero-2",
                "karbon-2",
                "qbo-3",
                "karbon-3",
                "xero-4",
                "karbon-4",
                "karbon-4-edit",
                "karbon-orphan",
            },
            evidence_ids,
        )


if __name__ == "__main__":
    unittest.main()
