import unittest

from build_colony.work_selection import (
    ActiveGateClass,
    GateRelation,
    HardStopReason,
    PackageGateBinding,
    RouteAttempt,
    RouteControl,
    RouteState,
    WorkSelectionContract,
    WorkSelectionError,
    effective_route_state,
    select_gate_directed_work,
)


class AGDWSTests(unittest.TestCase):
    def test_sqmr_replay_filters_wrong_phase_work(self):
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
        self.assertEqual(len(decision.eligible_domains), 4)
        self.assertIn(
            "generic_development_without_demonstrated_engineering_defect",
            decision.di_escalation_reasons,
        )

    def test_rls_replay_dispatches_only_two_currently_actionable_routes(self):
        routes = (
            RouteControl(
                "public-full",
                RouteState.ACTIVE,
                "credential-free public full payload may move gate",
            ),
            RouteControl(
                "archival-recovery",
                RouteState.ACTIVE,
                "archival namespace/rightsholder recovery may move gate",
            ),
            RouteControl(
                "free-authenticated",
                RouteState.STOPPED,
                "authentication is a current authority boundary",
                hard_stop_reason=HardStopReason.AUTHORITY_OR_HUMAN_GATE,
            ),
            RouteControl(
                "licensed-paid",
                RouteState.STOPPED,
                "paid authority is outside current authority",
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
                "metadata cannot satisfy PIT admission semantics",
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
        decision = select_gate_directed_work(
            (route.route_id for route in routes), contract
        )
        self.assertEqual(
            decision.eligible_domains, ("archival-recovery", "public-full")
        )
        self.assertEqual(len(decision.filtered_domains), 4)
        self.assertFalse(decision.di_escalation_recommended)

    def test_route_suspends_after_two_distinct_same_boundary_zero_delta_attempts(self):
        route = RouteControl(
            "mirror-search",
            RouteState.ACTIVE,
            "search route",
            attempts=(
                RouteAttempt("a", "no_full_payload", 0),
                RouteAttempt("b", "no_full_payload", 0),
            ),
        )
        disposition = effective_route_state(route)
        self.assertEqual(disposition.state, RouteState.DEFERRED)
        self.assertTrue(disposition.saturation_suspended)

    def test_material_new_basis_reopens_saturated_route(self):
        route = RouteControl(
            "mirror-search",
            RouteState.DEFERRED,
            "previously saturated",
            attempts=(
                RouteAttempt("a", "no_full_payload", 0),
                RouteAttempt("b", "no_full_payload", 0),
            ),
            reopen_basis="new authoritative archival namespace",
        )
        disposition = effective_route_state(route)
        self.assertEqual(disposition.state, RouteState.ACTIVE)
        self.assertFalse(disposition.saturation_suspended)

    def test_required_serial_dependency_remains_eligible(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.VALIDATION_ADMISSION,
            native_progress_unit="admitted_candidates",
            package_bindings=(
                PackageGateBinding(
                    "source-replay", GateRelation.REQUIRED_SERIAL_DEPENDENCY
                ),
            ),
        )
        decision = select_gate_directed_work(("source-replay",), contract)
        self.assertEqual(decision.eligible_domains, ("source-replay",))

    def test_unclassified_gate_fails_closed_and_recommends_di(self):
        contract = WorkSelectionContract(
            active_gate_class=None,
            native_progress_unit="unknown",
            package_bindings=(PackageGateBinding("generic", GateRelation.DIRECT),),
        )
        decision = select_gate_directed_work(("generic",), contract)
        self.assertEqual(decision.eligible_domains, ())
        self.assertEqual(decision.filtered_domains, ("generic",))
        self.assertIn("active_gate_unclassified", decision.di_escalation_reasons)

    def test_evidence_bound_capability_gap_allows_bounded_exploration(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.CAPABILITY_GAP,
            native_progress_unit="validated_architectural_capabilities",
            package_bindings=(
                PackageGateBinding("eclipse_peer_view_candidate", GateRelation.DIRECT),
                PackageGateBinding("independent_topology_observer", GateRelation.DIRECT),
                PackageGateBinding("unrelated_generic_subsystem", GateRelation.NONE),
            ),
            generic_development_proposed=True,
            active_gate_evidence_ref=(
                "git:Waterfound/FAE@"
                + "a" * 40
                + ":evidence/capability-gap/eclipse-peer-view"
            ),
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
        self.assertEqual(
            decision.filtered_domains,
            ("unrelated_generic_subsystem",),
        )
        self.assertNotIn(
            "generic_development_without_demonstrated_engineering_defect",
            decision.di_escalation_reasons,
        )

    def test_unbound_capability_gap_fails_closed(self):
        with self.assertRaisesRegex(
            WorkSelectionError,
            "capability_gap_requires_immutable_evidence_ref",
        ):
            WorkSelectionContract(
                active_gate_class=ActiveGateClass.CAPABILITY_GAP,
                native_progress_unit="validated_capabilities",
                package_bindings=(
                    PackageGateBinding("bounded_candidate", GateRelation.DIRECT),
                ),
            )

    def test_unrelated_work_remains_filtered_under_valid_capability_gap(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.CAPABILITY_GAP,
            native_progress_unit="validated_capabilities",
            package_bindings=(
                PackageGateBinding("bounded_candidate", GateRelation.DIRECT),
                PackageGateBinding("generic_unrelated", GateRelation.NONE),
            ),
            active_gate_evidence_ref="sha256:" + "b" * 64,
        )
        decision = select_gate_directed_work(
            ("bounded_candidate", "generic_unrelated"), contract
        )
        self.assertEqual(decision.eligible_domains, ("bounded_candidate",))
        self.assertEqual(decision.filtered_domains, ("generic_unrelated",))

    def test_two_zero_yield_runs_emit_advisory_only_di_escalation(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.EVIDENCE_ACQUISITION,
            native_progress_unit="new_months",
            package_bindings=(PackageGateBinding("route-a", GateRelation.DIRECT),),
            recent_run_native_deltas=(0, 0),
        )
        decision = select_gate_directed_work(("route-a",), contract)
        self.assertTrue(decision.di_escalation_recommended)
        self.assertIn(
            "two_consecutive_zero_yield_runs_without_hard_external_gate",
            decision.di_escalation_reasons,
        )
        self.assertEqual(decision.eligible_domains, ("route-a",))

    def test_missing_package_binding_fails_closed(self):
        contract = WorkSelectionContract(
            active_gate_class=ActiveGateClass.ENGINEERING_DEFECT,
            native_progress_unit="closed_defects",
            package_bindings=(),
        )
        with self.assertRaises(WorkSelectionError):
            select_gate_directed_work(("unbound",), contract)


if __name__ == "__main__":
    unittest.main()
