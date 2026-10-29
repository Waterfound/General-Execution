import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "revenue_mission" / "pr_reviewability_packet.py"
SPEC = importlib.util.spec_from_file_location("pr_reviewability_packet", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load_fixture(name: str):
    path = ROOT / "tools" / "revenue_mission" / "fixtures" / name
    return json.loads(path.read_text(encoding="utf-8"))


class ReviewabilityPacketTests(unittest.TestCase):
    def test_reviewable_fixture_is_reviewable(self):
        packet = MODULE.build_packet(load_fixture("reviewable.json"))
        self.assertEqual(packet["disposition"], "REVIEWABLE")
        self.assertEqual(len(packet["verified_claims"]), 1)
        self.assertEqual(packet["blockers"], [])
        self.assertEqual(packet["next_action"], "begin human code review")

    def test_unsupported_completion_is_blocked_with_bounded_next_action(self):
        packet = MODULE.build_packet(load_fixture("unsupported_completion.json"))
        self.assertEqual(packet["disposition"], "BLOCK")
        self.assertEqual(len(packet["unsupported_claims"]), 1)
        self.assertIn(
            "full-regression",
            packet["unsupported_claims"][0]["reason"]["missing_checks"],
        )
        self.assertIn("review threads remain unresolved", packet["blockers"])
        self.assertIn(
            "AI-authored change has no identified human steward",
            packet["residual_uncertainties"],
        )
        self.assertEqual(
            packet["next_action"],
            "one or more completion claims lack passing evidence",
        )

    def test_public_pr_preserves_review_decision_and_declared_uncertainty(self):
        packet = MODULE.build_packet(
            load_fixture("public_neofs_sdk_go_pr_902_20261027.json")
        )
        self.assertEqual(packet["disposition"], "BLOCK")
        self.assertEqual(packet["review_decision"], "changes_requested")
        self.assertIn(
            "native review decision remains changes requested", packet["blockers"]
        )
        self.assertIn(
            "in-stream wrapping lacks an end-to-end cancellation test",
            packet["residual_uncertainties"],
        )
        self.assertEqual(len(packet["unsupported_claims"]), 1)

    def test_merged_public_pr_is_not_blocked_only_for_missing_owner(self):
        packet = MODULE.build_packet(
            load_fixture("public_getsentry_sentry_for_ai_pr_45_20260309.json")
        )
        self.assertEqual(packet["disposition"], "HUMAN_VERIFY")
        self.assertEqual(packet["review_decision"], "approved")
        self.assertEqual(packet["blockers"], [])
        self.assertEqual(len(packet["verified_claims"]), 1)
        self.assertIn(
            "AI-authored change has no identified human steward",
            packet["residual_uncertainties"],
        )


if __name__ == "__main__":
    unittest.main()
