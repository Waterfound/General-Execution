import unittest

from general_execution.build_colony_bridge import (
    CLIENT_CAPABILITY,
    BuildColonyBridgeError,
    admit_build_colony_dispatch,
)
from general_execution.canonical import sha256_digest
from general_execution.models import RunnerCapabilities, RunnerRegistry
from general_execution.planner import plan_execution


BC_REV = "a4891dd838545736022580811d6131efc0b93096"
GE_REV = "1f85f261ce30822e2018e9b56741b7fb0079a3eb"


def raw(value):
    return sha256_digest(value).split(":", 1)[1]


def artifact():
    capabilities = {
        "adapter_id": "general-execution-bridge",
        "provider": "general-execution",
        "adapter_version": "0.1",
        "modes": ["execute"],
        "supports_write": True,
        "supports_artifact_refs": True,
        "max_parallelism": 1,
    }
    capabilities["capability_digest"] = raw(capabilities)
    request = {
        "schema_version": 1,
        "session_protocol_version": "0.0.5",
        "dispatch_attempt": 1,
        "run_id": "bc2-fixture",
        "manifest_digest": "a" * 64,
        "source_revision": "source-revision-1",
        "package_id": "bc2-fixture:a",
        "package_digest": "b" * 64,
        "domain_id": "a",
        "adapter_id": capabilities["adapter_id"],
        "provider": capabilities["provider"],
        "capability_digest": capabilities["capability_digest"],
        "mode": "execute",
        "objective": "implement bounded change",
        "dependencies": [],
        "write_scopes": ["src/a"],
        "exclusive_resources": ["resource:a"],
        "invariants": ["preserve bridge invariant"],
        "forbidden_actions": ["do not integrate"],
        "gates": [
            {
                "id": "g",
                "description": "gate",
                "accepted_kinds": ["test"],
                "minimum": 1,
            }
        ],
    }
    seed = {
        "session_protocol_version": request["session_protocol_version"],
        "run_id": request["run_id"],
        "manifest_digest": request["manifest_digest"],
        "source_revision": request["source_revision"],
        "package_id": request["package_id"],
        "package_digest": request["package_digest"],
        "adapter_id": request["adapter_id"],
        "provider": request["provider"],
        "capability_digest": request["capability_digest"],
        "mode": request["mode"],
        "dispatch_attempt": request["dispatch_attempt"],
    }
    request["dispatch_id"] = "bcs-" + raw(seed)[:20]
    request["request_digest"] = raw(request)
    core = {
        "schema_version": "bc.ge-session-dispatch.v1",
        "artifact_type": "build_colony_session_dispatch_request",
        "producer_system": "build_colony",
        "producer_repository": "Waterfound/Build-Colony",
        "producer_revision": BC_REV,
        "capabilities": capabilities,
        "request": request,
        "execution_semantics": {
            "requires_build_colony_bind_before_physical_execution": True,
            "verification_authorized": False,
            "integration_authorized": False,
            "promotion_authorized": False,
        },
    }
    return {**core, "artifact_digest": sha256_digest(core)}


class BuildColonyBridgeTests(unittest.TestCase):
    def test_admission_preserves_constraints_and_grants_no_execution(self):
        spec, receipt = admit_build_colony_dispatch(
            artifact(),
            expected_producer_revision=BC_REV,
            general_execution_revision=GE_REV,
        )
        self.assertEqual(spec.required_capabilities, (CLIENT_CAPABILITY,))
        self.assertEqual(spec.allowed_scopes, ("src/a",))
        metadata = dict(spec.metadata)
        self.assertIn(
            "preserve bridge invariant", metadata["build_colony.invariants_json"]
        )
        self.assertIn(
            "resource:a", metadata["build_colony.exclusive_resources_json"]
        )
        self.assertFalse(receipt["execution_authorized"])
        self.assertFalse(receipt["verification_authorized"])
        self.assertFalse(receipt["integration_authorized"])
        self.assertFalse(receipt["promotion_authorized"])

    def test_generic_runner_cannot_silently_drop_build_colony_semantics(self):
        spec, _ = admit_build_colony_dispatch(
            artifact(),
            expected_producer_revision=BC_REV,
            general_execution_revision=GE_REV,
        )
        generic = RunnerCapabilities(
            runner_id="generic",
            provider="test",
            adapter="generic",
            adapter_version="1",
            capabilities=(),
            modes=("bounded_write",),
        )
        aware = RunnerCapabilities(
            runner_id="aware",
            provider="test",
            adapter="aware",
            adapter_version="1",
            capabilities=(CLIENT_CAPABILITY,),
            modes=("bounded_write",),
        )
        deferred = plan_execution(
            spec, RunnerRegistry((generic,)), mode="bounded_write"
        )
        self.assertEqual(deferred.deferral_reason, "no_compatible_runner")
        assigned = plan_execution(
            spec, RunnerRegistry((generic, aware)), mode="bounded_write"
        )
        self.assertEqual(assigned.runner_id, "aware")

    def test_tampered_invariants_are_rejected(self):
        document = artifact()
        document["request"]["invariants"] = ["tampered"]
        with self.assertRaises(BuildColonyBridgeError):
            admit_build_colony_dispatch(
                document,
                expected_producer_revision=BC_REV,
                general_execution_revision=GE_REV,
            )

    def test_wrong_producer_revision_is_rejected(self):
        with self.assertRaises(BuildColonyBridgeError):
            admit_build_colony_dispatch(
                artifact(),
                expected_producer_revision="deadbeef",
                general_execution_revision=GE_REV,
            )


if __name__ == "__main__":
    unittest.main()
