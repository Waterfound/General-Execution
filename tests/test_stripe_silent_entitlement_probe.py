import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "revenue_mission"))

from stripe_silent_entitlement_probe import analyze


FIXTURE_DIR = Path(__file__).with_name("fixtures")
FIXTURE = FIXTURE_DIR / "stripe_silent_entitlement_public_fixture.json"
FIXTURE_2 = FIXTURE_DIR / "stripe_silent_entitlement_public_fixture_2.json"


class ProbeTests(unittest.TestCase):
    def test_flags_two_silent_paid_access_paths(self):
        payload = json.loads(FIXTURE.read_text())
        result = analyze(payload)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["finding_count"], 2)
        self.assertEqual(result["severity_counts"], {"BLOCKER": 2})

    def test_durable_retry_removes_finding(self):
        payload = json.loads(FIXTURE.read_text())
        safe = copy.deepcopy(payload)
        for path in safe["event_paths"]:
            path["durable_retry_queue"] = True
        self.assertEqual(analyze(safe)["finding_count"], 0)

    def test_flags_three_paths_in_independent_public_fixture(self):
        payload = json.loads(FIXTURE_2.read_text())
        result = analyze(payload)
        self.assertEqual(result["finding_count"], 3)
        self.assertEqual(result["severity_counts"], {"BLOCKER": 3})


if __name__ == "__main__":
    unittest.main()
