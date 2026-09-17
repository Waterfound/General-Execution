import unittest

from build_colony.work_selection import (
    ActiveGateClass,
    GateRelation,
    HardStopReason,
    PackageGateBinding,
    RouteControl,
    RouteState,
    WorkSelectionContract,
    WorkSelectionError,
    select_gate_directed_work,
)


class EBCGFrozenReplayTests(unittest.TestCase):
    def test_r1_fae_exploration(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.CAPABILITY_GAP,
            native_progress_unit="validated_architectural_capabilities",
            active_gate_evidence_ref=(
                "git:Waterfound/FAE@" + "a" * 40 + ":evidence/capability-gap/eclipse-peer-view"
            ),
            package_bindings=(
                PackageGateBinding("eclipse_peer_view_candidate", GateRelation.DIRECT),
                PackageGateBinding("independent_topology_observer", GateRelation.DIRECT),
                PackageGateBinding("unrelated_generic_subsystem", GateRelation.NONE),
            ),
            generic_development_proposed=True,
        )
        decision = select_gate_directed_work(
            (
                "eclipse_peer_view_candidate",
                "independent_topology_observer",
                "unrelated_generic_subsystem",
            ),
            contract,
        )
        self.assertEqual(
            decision.eligible_domains,
            ("eclipse_peer_view_candidate", "independent_topology_observer"),
        )
        self.assertEqual(decision.filtered_domains, ("unrelated_generic_subsystem",))
        self.assertNotIn(
            "generic_development_without_demonstrated_engineering_defect",
            decision.di_escalation_reasons,
        )

    def test_r2_fae_closure(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EXTERNAL_DEPENDENCY,
            native_progress_unit="representative_device_evidence",
            package_bindings=(
                PackageGateBinding("physical_hfb_evidence_handoff", GateRelation.DIRECT),
                PackageGateBinding("new_generic_network_subsystem", GateRelation.NONE),
            ),
            generic_development_proposed=True,
        )
        decision = select_gate_directed_work(
            ("physical_hfb_evidence_handoff", "new_generic_network_subsystem"),
            contract,
        )
        self.assertEqual(decision.eligible_domains, ("physical_hfb_evidence_handoff",))
        self.assertEqual(decision.filtered_domains, ("new_generic_network_subsystem",))

    def test_r3_fae_engineering_defect(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.ENGINEERING_DEFECT,
            native_progress_unit="closed_demonstrated_defects",
            package_bindings=(
                PackageGateBinding("peer_directory_retention_fix", GateRelation.DIRECT),
            ),
            generic_development_proposed=True,
        )
        decision = select_gate_directed_work(("peer_directory_retention_fix",), contract)
        self.assertEqual(decision.eligible_domains, ("peer_directory_retention_fix",))
        self.assertEqual(decision.filtered_domains, ())

    def test_r4_sqmr_regression(self):
        direct = ("brk-b", "jpm", "bac", "ms")
        wrong_phase = (
            "structural-reviewer",
            "validator-architecture",
            "admission-bridge",
            "pipeline-design",
        )
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_MATERIALIZATION,
            native_progress_unit="admitted_candidates_out_of_37",
            package_bindings=tuple(
                [PackageGateBinding(domain, GateRelation.DIRECT) for domain in direct]
                + [PackageGateBinding(domain, GateRelation.NONE) for domain in wrong_phase]
            ),
            generic_development_proposed=True,
        )
        decision = select_gate_directed_work(direct + wrong_phase, contract)
        self.assertEqual(decision.eligible_domains, tuple(sorted(direct)))
        self.assertEqual(decision.filtered_domains, tuple(sorted(wrong_phase)))

    def test_r5_rls_regression(self):
        routes = (
            RouteControl("public-full", RouteState.ACTIVE, "public full payload may move gate"),
            RouteControl("archival-recovery", RouteState.ACTIVE, "archival recovery may move gate"),
            RouteControl(
                "free-authenticated",
                RouteState.STOPPED,
                "authentication boundary",
                hard_stop_reason=HardStopReason.AUTHORITY_OR_HUMAN_GATE,
            ),
            RouteControl(
                "licensed-paid",
                RouteState.STOPPED,
                "paid boundary",
                hard_stop_reason=HardStopReason.INACCESSIBLE_OR_PRIVATE,
            ),
            RouteControl(
                "private-inaccessible",
                RouteState.STOPPED,
                "private route inaccessible",
                hard_stop_reason=HardStopReason.INACCESSIBLE_OR_PRIVATE,
            ),
            RouteControl(
                "proxy-metadata",
                RouteState.STOPPED,
                "proxy insufficient",
                hard_stop_reason=HardStopReason.SEMANTICALLY_INSUFFICIENT_PROXY,
            ),
        )
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_ACQUISITION,
            native_progress_unit="newly_admitted_PIT_months",
            package_bindings=tuple(
                PackageGateBinding(route.route_id, GateRelation.DIRECT, route.route_id)
                for route in routes
            ),
            routes=routes,
        )
        decision = select_gate_directed_work(tuple(route.route_id for route in routes), contract)
        self.assertEqual(decision.eligible_domains, ("archival-recovery", "public-full"))
        self.assertEqual(
            decision.filtered_domains,
            ("free-authenticated", "licensed-paid", "private-inaccessible", "proxy-metadata"),
        )

    def test_r6_unknown_gate_negative_control(self):
        contract = WorkSelectionContract(
            active_gate_class=None,
            native_progress_unit="unknown",
            package_bindings=(PackageGateBinding("generic", GateRelation.DIRECT),),
        )
        decision = select_gate_directed_work(("generic",), contract)
        self.assertEqual(decision.eligible_domains, ())
        self.assertEqual(decision.filtered_domains, ("generic",))
        self.assertIn("active_gate_unclassified", decision.di_escalation_reasons)

    def test_r7_unbound_capability_gap_negative_control(self):
        with self.assertRaisesRegex(
            WorkSelectionError,
            "capability_gap_requires_immutable_evidence_ref",
        ):
            WorkSelectionContract(
                active_gate_class=ActiveGateClass.CAPABILITY_GAP,
                native_progress_unit="capabilities",
                package_bindings=(PackageGateBinding("candidate", GateRelation.DIRECT),),
                active_gate_evidence_ref=None,
            )

    def test_r8_unrelated_under_valid_gap_negative_control(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.CAPABILITY_GAP,
            native_progress_unit="validated_capabilities",
            active_gate_evidence_ref="sha256:" + "b" * 64,
            package_bindings=(
                PackageGateBinding("bounded_candidate", GateRelation.DIRECT),
                PackageGateBinding("generic_unrelated", GateRelation.NONE),
            ),
        )
        decision = select_gate_directed_work(
            ("bounded_candidate", "generic_unrelated"),
            contract,
        )
        self.assertEqual(decision.eligible_domains, ("bounded_candidate",))
        self.assertEqual(decision.filtered_domains, ("generic_unrelated",))


if __name__ == "__main__":
    unittest.main()
