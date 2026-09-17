import unittest

from work_selection import (
    ActiveGateClass, GateRelation, HardStopReason, PackageGateBinding,
    RouteAttempt, RouteControl, RouteState, WorkSelectionContract,
    WorkSelectionError, effective_route_state, select_gate_directed_work,
)


class AGDWSPublicValidation(unittest.TestCase):
    def test_sqmr_frozen_replay(self):
        direct = ("brk-b", "jpm", "bac", "ms")
        wrong = ("structural-reviewer", "validator-architecture", "admission-bridge", "pipeline-design")
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_MATERIALIZATION,
            native_progress_unit="admitted_candidates_out_of_37",
            package_bindings=tuple(
                [PackageGateBinding(item, GateRelation.DIRECT) for item in direct]
                + [PackageGateBinding(item, GateRelation.NONE) for item in wrong]
            ),
            generic_development_proposed=True,
        )
        decision = select_gate_directed_work(direct + wrong, contract)
        self.assertEqual(decision.eligible_domains, tuple(sorted(direct)))
        self.assertEqual(decision.filtered_domains, tuple(sorted(wrong)))
        self.assertIn("generic_development_without_demonstrated_engineering_defect", decision.di_escalation_reasons)

    def test_rls_frozen_replay(self):
        routes = (
            RouteControl("public-full", RouteState.ACTIVE, "credential-free public full payload"),
            RouteControl("archival-recovery", RouteState.ACTIVE, "credential-free archival recovery"),
            RouteControl("free-authenticated", RouteState.STOPPED, "authority boundary", hard_stop_reason=HardStopReason.AUTHORITY_OR_HUMAN_GATE),
            RouteControl("licensed-paid", RouteState.STOPPED, "paid authority", hard_stop_reason=HardStopReason.INACCESSIBLE_OR_PRIVATE),
            RouteControl("private-inaccessible", RouteState.STOPPED, "private route", hard_stop_reason=HardStopReason.INACCESSIBLE_OR_PRIVATE),
            RouteControl("proxy-metadata", RouteState.STOPPED, "semantically insufficient", hard_stop_reason=HardStopReason.SEMANTICALLY_INSUFFICIENT_PROXY),
        )
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_ACQUISITION,
            native_progress_unit="newly_admitted_PIT_months",
            package_bindings=tuple(PackageGateBinding(r.route_id, GateRelation.DIRECT, r.route_id) for r in routes),
            routes=routes,
        )
        decision = select_gate_directed_work((r.route_id for r in routes), contract)
        self.assertEqual(decision.eligible_domains, ("archival-recovery", "public-full"))
        self.assertEqual(len(decision.filtered_domains), 4)
        self.assertFalse(decision.di_escalation_recommended)

    def test_saturation_suspend_and_reopen(self):
        attempts = (RouteAttempt("a", "no_full_payload", 0), RouteAttempt("b", "no_full_payload", 0))
        suspended = effective_route_state(RouteControl("search", RouteState.ACTIVE, "search", attempts=attempts))
        self.assertEqual(suspended.state, RouteState.DEFERRED)
        self.assertTrue(suspended.saturation_suspended)
        reopened = effective_route_state(RouteControl("search", RouteState.DEFERRED, "saturated", attempts=attempts, reopen_basis="new namespace"))
        self.assertEqual(reopened.state, RouteState.ACTIVE)

    def test_required_serial_dependency_eligible(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.VALIDATION_ADMISSION,
            native_progress_unit="admitted_candidates",
            package_bindings=(PackageGateBinding("source-replay", GateRelation.REQUIRED_SERIAL_DEPENDENCY),),
        )
        self.assertEqual(select_gate_directed_work(("source-replay",), contract).eligible_domains, ("source-replay",))

    def test_unclassified_gate_fail_closed(self):
        contract = WorkSelectionContract(None, "unknown", (PackageGateBinding("generic", GateRelation.DIRECT),))
        decision = select_gate_directed_work(("generic",), contract)
        self.assertEqual(decision.eligible_domains, ())
        self.assertIn("active_gate_unclassified", decision.di_escalation_reasons)

    def test_two_zero_yield_runs_recommend_di_only(self):
        contract = WorkSelectionContract(
            ActiveGateClass.EVIDENCE_ACQUISITION, "new_months",
            (PackageGateBinding("route-a", GateRelation.DIRECT),),
            recent_run_native_deltas=(0, 0),
        )
        decision = select_gate_directed_work(("route-a",), contract)
        self.assertEqual(decision.eligible_domains, ("route-a",))
        self.assertIn("two_consecutive_zero_yield_runs_without_hard_external_gate", decision.di_escalation_reasons)

    def test_unbound_dispatchable_fails_closed(self):
        contract = WorkSelectionContract(ActiveGateClass.ENGINEERING_DEFECT, "closed_defects", ())
        with self.assertRaises(WorkSelectionError):
            select_gate_directed_work(("unbound",), contract)


if __name__ == "__main__":
    unittest.main()
