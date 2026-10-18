import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "revenue_mission"))

from prebuild_decision_gap_probe import analyze


FIXTURE = Path(__file__).with_name("fixtures") / "prebuild_decision_gap_fixture.json"


class ProbeTest(unittest.TestCase):
    def test_synthetic_fixture_finds_expected_gaps(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = analyze(fixture)

        self.assertTrue(result["read_only"])
        self.assertEqual(result["finding_count"], 4)
        self.assertEqual(result["severity_counts"]["BLOCKER"], 3)
        self.assertEqual(result["severity_counts"]["HIGH"], 1)
        self.assertEqual(
            {item["kind"] for item in result["findings"]},
            {
                "cross_artifact_contradiction",
                "workflow_permission_gap",
                "product_decision_required",
            },
        )


if __name__ == "__main__":
    unittest.main()
