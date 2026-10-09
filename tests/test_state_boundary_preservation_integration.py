import json

from general_execution import (
    CheckpointEvidence,
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    PortfolioEntry,
    PortfolioState,
    ResumeTickObservation,
    TransitionPolicy,
    TransitionRule,
    canonical_json,
    sha256_digest,
)
from general_execution.continuity_check import (
    ContinuitySnapshot,
    ConversationEvidence,
    DevelopmentVerdict,
    DurableStateEvidence,
    ProviderEvidence,
    ProviderState,
    RecommendedAction,
    RepositoryEvidence,
    WorkstreamCandidate,
    inspect_continuity,
)
from general_execution.core_rehearsal import (
    CoreRehearsalAssertion,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)
from general_execution.external_trigger import ExternalTriggerEvidence, TriggerContract
from general_execution.holistic_symbiosis import compose_symbiotic_route
from general_execution.persistent_runtime import (
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from general_execution.portfolio_persistence import (
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from general_execution.portfolio_state import portfolio_state_to_dict
from general_execution.state_boundary import (
    FilePrivateStateBoundary,
    StateTransportBinding,
    compare_semantic_preservation,
    semantic_receipt_from_runtime,
)
from general_execution.transition_policy import transition_policy_to_dict
from general_execution.work_sparse_unattended import (
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
)


REVISION = "b" * 40
AUTH = "authority://example/preservation"
DIG = lambda value: sha256_digest(value)


def _encoded(value):
    return json.loads(canonical_json(value))


def _portfolio():
    return PortfolioState(
        portfolio_id="preservation-proof",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state="ready",
            objective="preserve durable semantics",
            active_gate="PRESERVE",
            next_action_ref="action://await",
            source_revision=REVISION,
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="remain ready",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision=REVISION,
        ),
        passive=(),
    )


def _policy():
    return TransitionPolicy(
        policy_id="preservation-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-wait",
                from_state="ready",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://preservation-proof",
                effect="stop_human_gate",
                required_evidence=("authority_boundary_reached",),
                authority_mode="human_required",
                authority_boundary="preservation proof authority boundary",
            ),
        ),
    )


def _bootstrap():
    return {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": "preservation-bootstrap",
        "operation": "bootstrap",
        "body": {"portfolio": portfolio_state_to_dict(_portfolio())},
    }


def _gate():
    req = CoreVerificationRequirement(
        required_revision=REVISION,
        required_suite_ref="tests://state-boundary-preservation",
        required_verifier_ref="verifier://state-boundary-preservation",
        minimum_test_count=1,
    )
    receipt = CoreVerificationReceipt(
        target_revision=REVISION,
        suite_ref=req.required_suite_ref,
        evidence_ref="artifact://state-boundary-preservation",
        evidence_digest=DIG("preservation-core"),
        verifier_ref=req.required_verifier_ref,
        executed_at="2026-10-09T06:00:00Z",
        passed=True,
        test_count=1,
    )
    assertions = tuple(
        CoreRehearsalAssertion(
            assertion_id=assertion_id,
            passed=True,
            evidence_refs=(f"fixture://{assertion_id}",),
            evidence_digests=(DIG(assertion_id),),
        )
        for assertion_id in sorted(REQUIRED_CORE1_ASSERTIONS)
    )
    report = build_core_rehearsal_report(REVISION, receipt.digest, assertions)
    return req, receipt, report


def _transition():
    state = _portfolio()
    policy = _policy()
    evidence = CheckpointEvidence(
        kind="authority_boundary_reached",
        locator="fixture://preservation/authority",
        digest=DIG("authority-boundary"),
    )
    observation = ResumeTickObservation(
        portfolio_id=state.portfolio_id,
        expected_generation=0,
        expected_state_digest=state.digest,
        policy_digest=policy.digest,
        event="authority_required",
        evidence=(evidence,),
        action_ref="fixture://preservation/stop",
        observed_at="2026-10-09T06:01:00Z",
        summary="same semantic stop under both persistence transports",
        canonical_refs=("fixture://preservation",),
    )
    trigger = ExternalTriggerEvidence(
        source="provider-event",
        event_id="preservation-transition",
        event_kind="durable-transition",
        payload_digest=DIG("payload"),
        observation_digest=observation.digest,
        admission_ref="provider://preservation-transition",
    )
    contract = TriggerContract(
        source=trigger.source,
        event_kind=trigger.event_kind,
        portfolio_id=state.portfolio_id,
        policy_digest=policy.digest,
        transition_event=observation.event,
    )
    return {
        "schema_version": "ge.persistent-runtime-event.v1",
        "event_id": trigger.event_id,
        "operation": "transition",
        "body": {
            "policy": transition_policy_to_dict(policy),
            "contract": _encoded(contract),
            "trigger": _encoded(trigger),
            "observation": _encoded(observation),
        },
    }


def test_durable_semantics_survive_private_boundary_and_restart(tmp_path):
    baseline_db = tmp_path / "baseline.db"
    candidate_db = tmp_path / "candidate.db"

    baseline_boot = process_persistent_runtime_event(baseline_db, _bootstrap())
    candidate_boot = process_persistent_runtime_event(candidate_db, _bootstrap())

    private = FilePrivateStateBoundary(tmp_path / "private-state")
    private_receipt = private.persist(
        "s_0000000000000002",
        candidate_db.read_bytes(),
    )
    candidate_db.unlink()
    candidate_db.write_bytes(private.restore(private_receipt))

    event = _transition()
    admission = trigger_digest_from_event(event)
    requirement, receipt, report = _gate()

    baseline_transition = process_persistent_runtime_event(
        baseline_db,
        event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )
    candidate_transition = process_persistent_runtime_event(
        candidate_db,
        event,
        authenticated_trigger_digest=admission,
        core_requirement=requirement,
        core_verification=receipt,
        core_report=report,
    )

    for left, right in (
        (baseline_boot, candidate_boot),
        (baseline_transition, candidate_transition),
    ):
        decision = compare_semantic_preservation(
            semantic_receipt_from_runtime(left),
            semantic_receipt_from_runtime(right),
            baseline_binding=StateTransportBinding(
                state_ref="s_0000000000000001",
                storage_visibility="public",
                execution_resource_ref="executor://baseline",
            ),
            candidate_binding=StateTransportBinding(
                state_ref="s_0000000000000002",
                storage_visibility="private",
                execution_resource_ref="executor://provider-neutral-local",
                execution_requires_storage_provider=False,
            ),
            evidence_predicate_preserved=True,
        )
        assert decision.equivalent, decision

    baseline_state, baseline_checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(baseline_db),
        _portfolio().portfolio_id,
    )
    candidate_state, candidate_checkpoint, _ = recover_portfolio_after_restart(
        SqlitePortfolioHeadStore(candidate_db),
        _portfolio().portfolio_id,
    )
    assert baseline_state == candidate_state
    assert baseline_checkpoint == candidate_checkpoint
    assert candidate_state.active.state == "human_gate"


def _route():
    envelope = UnattendedAuthorityEnvelope(
        envelope_id="preserve",
        authority_ref=AUTH,
        allowed_repositories=("example/repo",),
        allowed_actions=("run_tests",),
        forbidden_actions=("merge_main", "paid_spend"),
        max_work_invocations=0,
        max_paid_spend_cents=0,
    )
    work = UnattendedWorkItem(
        work_id="preserve-route",
        objective="preserve selection",
        repository="example/repo",
        source_revision=REVISION,
        authority_ref=AUTH,
        required_capabilities=("test_execution",),
        requested_actions=("run_tests",),
    )
    executors = (
        ExecutorCapability(
            executor_id="local_provider_neutral",
            capabilities=("test_execution",),
            cost_rank=0,
            estimated_cost_cents=0,
            requires_work=False,
            paid=False,
            available=True,
            evidence_ref="evidence://local",
        ),
        ExecutorCapability(
            executor_id="private_actions",
            capabilities=("test_execution",),
            cost_rank=10,
            estimated_cost_cents=0,
            requires_work=False,
            paid=False,
            available=False,
            evidence_ref="evidence://private-actions-unavailable",
        ),
    )
    return compose_symbiotic_route(
        envelope=envelope,
        work=work,
        executors=executors,
        evidence_predicate="same-preservation-predicate",
    )


def test_symbiotic_selection_is_transport_orthogonal_and_non_actions():
    baseline = _route()
    candidate = _route()
    assert baseline.digest == candidate.digest
    assert candidate.selected_executor_id == "local_provider_neutral"
    assert candidate.substitution.selected_method_id == "local_provider_neutral"
    assert candidate.ready_for_existing_admission
    assert not candidate.execution_triggered


def _continuity(provider_name):
    candidate = WorkstreamCandidate(
        workstream_id="preserve",
        canonical_name="preserve",
        repository="example/repo",
    )
    snapshot = ContinuitySnapshot(
        checked_at="2026-10-09T06:02:00Z",
        query="preserve",
        candidates=(candidate,),
        conversation=ConversationEvidence(),
        repository=RepositoryEvidence(
            repository="example/repo",
            main_revision=REVISION,
            branch="candidate",
            branch_head=REVISION,
        ),
        durable=DurableStateEvidence(
            validated=True,
            workstream_id="preserve",
            bound_repository="example/repo",
            bound_branch="candidate",
            bound_branch_head=REVISION,
            current_frontier="verification",
            admissible_next=("resume",),
            execution_expected=True,
        ),
        provider=ProviderEvidence(
            provider=provider_name,
            state=ProviderState.UNAVAILABLE,
            subject_revision=REVISION,
        ),
        canonical_integration_required=True,
    )
    return inspect_continuity(snapshot)


def test_continuity_verdict_is_preserved_when_storage_provider_identity_changes():
    baseline = _continuity("baseline-transport")
    candidate = _continuity("private-state-transport")
    assert baseline.development_verdict == candidate.development_verdict
    assert baseline.recommended_action == candidate.recommended_action
    assert baseline.infrastructure_status == candidate.infrastructure_status
    assert baseline.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert baseline.recommended_action == RecommendedAction.RESUME_DURABLE_EXECUTION.value
