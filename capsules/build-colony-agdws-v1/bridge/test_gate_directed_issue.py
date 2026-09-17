from types import SimpleNamespace
import unittest

from build_colony.gate_directed_issue import issue_gate_directed_ready
from build_colony.state_models import RunLedger
from build_colony.work_selection import (
    ActiveGateClass, GateRelation, PackageGateBinding, WorkSelectionContract,
    WorkSelectionError,
)


class GateDirectedIssuePublicValidation(unittest.TestCase):
    def _manifest(self):
        return SimpleNamespace(
            packages=tuple(
                SimpleNamespace(domain_id=domain, package_id=f"pkg-{domain}")
                for domain in ("a", "b", "c", "d")
            )
        )

    def test_only_gate_relevant_ready_packages_are_issued(self):
        manifest = self._manifest()
        ledger = RunLedger(ready=("a", "b", "c", "d"))
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_MATERIALIZATION,
            native_progress_unit="admitted_candidates",
            package_bindings=(
                PackageGateBinding("a", GateRelation.DIRECT),
                PackageGateBinding("b", GateRelation.REQUIRED_SERIAL_DEPENDENCY),
                PackageGateBinding("c", GateRelation.NONE),
                PackageGateBinding("d", GateRelation.NONE),
            ),
        )
        result = issue_gate_directed_ready(manifest, ledger, contract)
        self.assertEqual(tuple(event["domain_id"] for event in result.ledger.events), ("a", "b"))
        self.assertEqual(result.ledger.ready, ("c", "d"))
        self.assertEqual(result.decision.eligible_domains, ("a", "b"))
        for event in result.ledger.events:
            self.assertEqual(event["role"], "coordinator")
            self.assertEqual(event["event_type"], "issue")
            self.assertEqual(event["payload"]["selection_contract_digest"], result.selection_contract_digest)
            self.assertEqual(event["payload"]["selection_decision_digest"], result.selection_decision_digest)

    def test_missing_binding_fails_before_issuing(self):
        manifest = self._manifest()
        ledger = RunLedger(ready=("a", "b", "c", "d"))
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.ENGINEERING_DEFECT,
            native_progress_unit="closed_defects",
            package_bindings=(PackageGateBinding("a", GateRelation.DIRECT),),
        )
        with self.assertRaises(WorkSelectionError):
            issue_gate_directed_ready(manifest, ledger, contract)
        self.assertEqual(ledger.events, ())

    def test_unclassified_gate_emits_no_issue(self):
        manifest = self._manifest()
        ledger = RunLedger(ready=("a", "b", "c", "d"))
        contract = WorkSelectionContract(
            active_gate_class=None,
            native_progress_unit="unknown",
            package_bindings=tuple(
                PackageGateBinding(domain, GateRelation.DIRECT)
                for domain in ("a", "b", "c", "d")
            ),
        )
        result = issue_gate_directed_ready(manifest, ledger, contract)
        self.assertEqual(result.ledger.events, ())
        self.assertTrue(result.decision.di_escalation_recommended)


if __name__ == "__main__":
    unittest.main()
