import importlib.util
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("continuity_audit", HERE / "continuity_audit.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AuditTest(unittest.TestCase):
    def test_fixture_finds_surface_without_secret_values(self):
        report = MODULE.audit(HERE / "fixture")
        observed = report["observed"]
        self.assertEqual(observed["secret_identifiers_only"], ["NPM_TOKEN", "VERCEL_TOKEN"])
        self.assertIn("17 3 * * 1", observed["schedules"])
        self.assertIn("api.example.com", observed["domains"])
        self.assertIn("vercel", observed["providers"])
        self.assertIn("npm", observed["providers"])
        self.assertEqual(
            report["gaps"],
            ["payment_processor_recovery", "private_repository_recovery", "restore_test_evidence"],
        )
        serialized = str(report)
        self.assertNotIn("secret-value", serialized)
        self.assertEqual(len(report["public_attestation"]["digest"]), 64)


if __name__ == "__main__":
    unittest.main()
