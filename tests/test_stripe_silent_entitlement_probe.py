import copy
import json
import unittest
from pathlib import Path

from stripe_silent_entitlement_probe import analyze


FIXTURE = Path(__file__).with_name("stripe_silent_entitlement_public_fixture.json")


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


if __name__ == "__main__":
    unittest.main()
