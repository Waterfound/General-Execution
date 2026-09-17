import copy
import unittest

from general_execution.canonical import sha256_digest
from general_execution.ecl import ECLCarrierError, attach_ecl_context, validate_bound_context, validate_spec_ecl
from general_execution.models import ExecutionSpec


MANIFEST = {
    "context_version": "0.1",
    "project_id": "FAE",
    "repository": "Waterfound/FAE-testnet",
    "project_revision": "abcdef1234567890abcdef1234567890abcdef12",
    "domain": "protocol-engineering",
    "purpose": "Defensive reliability engineering of a user-owned project.",
    "terminology": {"hardening": "reliability and robustness improvement"},
    "authorization": {
        "scope_type": "user-owned-project",
        "external_targets": False,
        "grants_authority": False,
        "authority_source": "target-owned",
    },
    "constraints": {
        "safeguard_bypass": False,
        "external_intrusion": False,
        "credential_acquisition": False,
        "external_persistence": False,
    },
    "related_systems": ["Build Colony", "General Execution"],
}


def bound_context():
    sidecar = {
        "context_version": "0.1",
        "project_id": MANIFEST["project_id"],
        "repository": MANIFEST["repository"],
        "project_revision": MANIFEST["project_revision"],
        "prompt_digest": "sha256:" + "1" * 64,
        "manifest_digest": sha256_digest(MANIFEST),
        "adapter_id": "thin-envelope-ecl",
        "adapter_version": "0.1",
        "grants_authority": False,
    }
    return {
        "context_manifest": copy.deepcopy(MANIFEST),
        "context_sidecar": sidecar,
        "binding_digest": sha256_digest(sidecar),
        "grants_authority": False,
    }


def spec():
    return ExecutionSpec(
        producer="build-colony",
        producer_revision="1234567890abcdef1234567890abcdef12345678",
        task_kind="reference-probe",
        objective="Run bounded conformance probe",
        source_revision=MANIFEST["project_revision"],
        metadata=(("existing", "kept"),),
    )


class ECLCarrierTests(unittest.TestCase):
    def test_bound_context_validates_without_authority(self):
        receipt = validate_bound_context(bound_context())
        self.assertFalse(receipt["grants_authority"])

    def test_attach_carries_manifest_and_changes_spec_digest(self):
        original = spec()
        contextualized = attach_ecl_context(original, bound_context())
        self.assertNotEqual(original.digest, contextualized.digest)
        self.assertEqual(dict(contextualized.metadata)["existing"], "kept")
        self.assertIn("ecl.manifest", dict(contextualized.metadata))
        self.assertIsNone(validate_spec_ecl(original))
        self.assertTrue(validate_spec_ecl(contextualized)["context_carried"])

    def test_context_does_not_create_authority_reference(self):
        contextualized = attach_ecl_context(spec(), bound_context())
        self.assertIsNone(contextualized.authority_ref)
        self.assertEqual(dict(contextualized.metadata)["ecl.grants_authority"], "false")

    def test_manifest_tamper_fails_closed(self):
        bound = bound_context()
        bound["context_manifest"]["purpose"] = "tampered"
        with self.assertRaises(ECLCarrierError):
            validate_bound_context(bound)

    def test_authority_fabrication_fails_closed(self):
        bound = bound_context()
        bound["context_manifest"]["authorization"]["grants_authority"] = True
        with self.assertRaises(ECLCarrierError):
            validate_bound_context(bound)

    def test_second_attachment_is_rejected(self):
        contextualized = attach_ecl_context(spec(), bound_context())
        with self.assertRaises(ECLCarrierError):
            attach_ecl_context(contextualized, bound_context())


if __name__ == "__main__":
    unittest.main()
