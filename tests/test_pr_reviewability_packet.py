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
        self.assertIn("post-merge ownership is undefined", packet["blockers"])
        self.assertEqual(
            packet["next_action"],
            "one or more completion claims lack passing evidence",
        )


if __name__ == "__main__":
    unittest.main()
