import importlib.util
import tempfile
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
        self.assertEqual(observed["configuration_identifiers_only"], [])
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

    def test_public_profile_ignores_comment_examples_and_finds_configured_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.example").write_text(
                "NEXT_PUBLIC_SUPABASE_URL=\nPADDLE_API_KEY=\nVERCEL_TOKEN=\n",
                encoding="utf-8",
            )
            (root / "service.toml").write_text(
                "# example only: AWS_ACCESS_KEY_ID=\n# bucket.s3.amazonaws.com\n",
                encoding="utf-8",
            )
            report = MODULE.audit(root)
            observed = report["observed"]
            self.assertEqual(
                observed["configuration_identifiers_only"],
                ["NEXT_PUBLIC_SUPABASE_URL", "PADDLE_API_KEY", "VERCEL_TOKEN"],
            )
            self.assertEqual(observed["providers"], ["paddle", "supabase", "vercel"])
            self.assertNotIn("aws", observed["providers"])


if __name__ == "__main__":
    unittest.main()
