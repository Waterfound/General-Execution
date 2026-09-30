from __future__ import annotations

import pytest

from general_execution.canonical import sha256_digest
from general_execution.continuity_check import (
    BuildColonyEvidence,
    ContinuitySnapshot,
    ConversationAssessment,
    ConversationEvidence,
    DevelopmentVerdict,
    DurableStateEvidence,
    FailureScope,
    InfrastructureStatus,
    LaunchAdmissionEvidence,
    LaunchDisposition,
    ProviderEvidence,
    ProviderState,
    RepositoryEvidence,
    WorkstreamCandidate,
    inspect_continuity,
)
from general_execution.execution_launch_admission import (
    ExecutionLaunchAdmissionError,
    ExecutionLaunchOrder,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
    admit_or_replay_execution_launch,
)


def authority(*scopes: str) -> LaunchAuthorityBinding:
    return LaunchAuthorityBinding(
        actor="Waterfound",
        authority_ref="authority://explicit-order/elg01-test",
        authority_boundary="Bounded local/project execution only.",
        granted_scopes=tuple(sorted(scopes)),
    )


def executor(
    name: str = "build_colony",
    availability: str = "AVAILABLE",
) -> LaunchExecutorBinding:
    return LaunchExecutorBinding(
        executor=name,
        availability=availability,
        evidence_ref=f"executor://{name}/capability",
        evidence_digest=sha256_digest({"executor": name, "availability": availability}),
    )


def order(
    *,
    workstream_id: str = "elg01-test",
    owner: str | None = "engineering",
    repository: str | None = "Waterfound/General-Execution",
    executor_name: str | None = "build_colony",
    objective: str = "Exercise ELG-01",
    required_scopes: tuple[str, ...] = ("candidate_write",),
    authority_binding: LaunchAuthorityBinding | None = None,
    executor_binding: LaunchExecutorBinding | None = None,
    first_artifact_ref: str | None = None,
) -> ExecutionLaunchOrder:
    if authority_binding is None and required_scopes:
        authority_binding = authority(*required_scopes)
    if executor_binding is None and executor_name is not None:
        executor_binding = executor(executor_name)
    return ExecutionLaunchOrder(
        workstream_id=workstream_id,
        owner=owner,
        repository=repository,
        executor=executor_name,
        objective=objective,
        order_ref=f"order://{workstream_id}",
        source_revision="aa230a84157b47769c29942f1dbae8079bb2b58c",
        required_authority_scopes=tuple(sorted(required_scopes)),
        authority=authority_binding,
        executor_binding=executor_binding,
        known_first_artifact_ref=first_artifact_ref,
    )


def admit(value: ExecutionLaunchOrder, existing=None):
    return admit_or_replay_execution_launch(
        value,
        authenticated_order_digest=value.digest,
        authenticated_actor="Waterfound",
        existing_receipt=existing,
    )


def candidate(workstream_id: str, repository: str, branch: str | None = None):
    return WorkstreamCandidate(
        workstream_id=workstream_id,
        canonical_name=workstream_id,
        repository=repository,
        branch=branch,
    )


def repo(repository: str, branch: str | None = None):
    return RepositoryEvidence(
        repository=repository,
        branch=branch,
        branch_head="1" * 40 if branch else None,
    )


def launch_evidence(receipt, *, observed_at="2026-09-29T22:00:00Z", exhausted=False):
    return LaunchAdmissionEvidence(
        validated=True,
        workstream_id=receipt.workstream_id,
        disposition=LaunchDisposition(receipt.disposition),
        receipt_ref=f"launch-receipt://{receipt.receipt_id}",
        launch_id=receipt.launch_id,
        repository=receipt.repository,
        executor=receipt.executor,
        dispatch_identity=receipt.dispatch_identity,
        first_artifact_ref=receipt.first_artifact_ref,
        observed_at=observed_at,
        recovery_semantics_exhausted=exhausted,
        detail=receipt.disposition_reason,
    )


def test_admitted_receipt_is_deterministic_and_does_not_trigger_execution_or_authority():
    value = order()
    first = admit(value)
    second = admit(value)

    assert first.replay_status == second.replay_status == "CREATED"
    assert first.receipt == second.receipt
    receipt = first.receipt
    assert receipt.disposition == "ADMITTED"
    assert receipt.launch_id.startswith("gel-")
    assert receipt.dispatch_identity.startswith("geld-")
    assert receipt.recovery_required is True
    assert receipt.authority_created is False
    assert receipt.execution_triggered is False


def test_retry_after_receipt_is_idempotent():
    value = order()
    first = admit(value).receipt
    replay = admit(value, first)
    assert replay.replay_status == "ALREADY_RECORDED"
    assert replay.receipt == first


def test_crash_immediately_before_receipt_recomputes_identical_receipt():
    value = order()
    before_crash = admit(value).receipt
    after_restart = admit(value).receipt
    assert before_crash == after_restart


def test_same_workstream_with_changed_order_cannot_duplicate_launch():
    first_order = order()
    first = admit(first_order).receipt
    changed = order(objective="Changed execution request")
    with pytest.raises(
        ExecutionLaunchAdmissionError,
        match="workstream already has a different execution launch order",
    ):
        admit(changed, first)


def test_missing_authority_stops_at_human_gate():
    value = order(authority_binding=None, required_scopes=("candidate_write",))
    # helper supplies authority for non-empty scopes, so construct exact missing case.
    value = ExecutionLaunchOrder(
        workstream_id=value.workstream_id,
        owner=value.owner,
        repository=value.repository,
        executor=value.executor,
        objective=value.objective,
        order_ref=value.order_ref,
        source_revision=value.source_revision,
        required_authority_scopes=value.required_authority_scopes,
        authority=None,
        executor_binding=value.executor_binding,
    )
    receipt = admit(value).receipt
    assert receipt.disposition == "HUMAN_GATE"
    assert receipt.launch_id is None
    assert receipt.execution_triggered is False


def test_insufficient_authority_stops_at_human_gate():
    value = order(
        required_scopes=("candidate_write", "network_read"),
        authority_binding=authority("candidate_write"),
    )
    receipt = admit(value).receipt
    assert receipt.disposition == "HUMAN_GATE"
    assert "network_read" in receipt.disposition_reason


def test_authority_actor_substitution_is_rejected():
    value = order(authority_binding=LaunchAuthorityBinding(
        actor="someone-else",
        authority_ref="authority://wrong",
        authority_boundary="wrong actor",
        granted_scopes=("candidate_write",),
    ))
    receipt = admit(value).receipt
    assert receipt.disposition == "REJECTED"
    assert receipt.disposition_reason == "authority_actor_mismatch"


def test_missing_repository_binding_is_rejected():
    receipt = admit(order(repository=None)).receipt
    assert receipt.disposition == "REJECTED"
    assert receipt.disposition_reason == "repository_binding_missing"


def test_executor_unavailable_fails_before_launch():
    receipt = admit(order(executor_binding=executor("build_colony", "UNAVAILABLE"))).receipt
    assert receipt.disposition == "FAILED_BEFORE_LAUNCH"
    assert receipt.disposition_reason == "executor_unavailable"
    assert receipt.launch_id is None


def test_missing_executor_evidence_fails_before_launch():
    value = order()
    value = ExecutionLaunchOrder(
        workstream_id=value.workstream_id,
        owner=value.owner,
        repository=value.repository,
        executor=value.executor,
        objective=value.objective,
        order_ref=value.order_ref,
        source_revision=value.source_revision,
        required_authority_scopes=value.required_authority_scopes,
        authority=value.authority,
        executor_binding=None,
    )
    receipt = admit(value).receipt
    assert receipt.disposition == "FAILED_BEFORE_LAUNCH"


def test_authority_free_read_only_launch_can_be_admitted_without_authority_binding():
    value = order(
        required_scopes=(),
        authority_binding=None,
        executor_name="project_assurance",
        executor_binding=executor("project_assurance"),
    )
    receipt = admit(value).receipt
    assert receipt.disposition == "ADMITTED"
    assert receipt.authority_ref is None


def test_known_first_artifact_eliminates_recovery_required_flag():
    value = order(first_artifact_ref="github://Waterfound/General-Execution/commit/" + "2" * 40)
    receipt = admit(value).receipt
    assert receipt.disposition == "ADMITTED"
    assert receipt.first_artifact_ref is not None
    assert receipt.recovery_required is False


def test_branch_created_without_substantive_artifact_is_checkpointed_resumable():
    value = order(
        workstream_id="fae-browsercoin-design-assurance-001",
        owner="fae-design-assurance",
        repository="Waterfound/FAE-testnet",
        executor_name="build_colony",
        required_scopes=("candidate_write",),
    )
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository, "colony/fae-browsercoin-design-assurance-001"),),
        repository=repo(value.repository, "colony/fae-browsercoin-design-assurance-001"),
        launch_admission=launch_evidence(receipt),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert report.latest_execution_evidence["ref"].startswith("launch_admission:")
    assert report.execution_triggered is False


def test_admitted_launch_becomes_stalled_only_when_recovery_semantics_are_exhausted():
    value = order()
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt, exhausted=True),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.DEVELOPMENT_STALLED.value


def test_build_colony_bootstrap_failure_is_explicit_failure_without_erasing_receipt():
    value = order()
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt),
        provider=ProviderEvidence(
            provider="build-colony-bootstrap",
            state=ProviderState.FAILED,
            failure_scope=FailureScope.WORKLOAD,
            detail="bootstrap failed before first substantive artifact",
        ),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.FAILED.value
    assert report.latest_execution_evidence is not None
    assert receipt.disposition == "ADMITTED"


def test_durable_temporarily_unavailable_does_not_erase_admitted_launch():
    value = order()
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt),
        provider=ProviderEvidence(
            provider="durable-runtime-host",
            state=ProviderState.UNAVAILABLE,
            detail="temporary runner unavailable",
        ),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert report.infrastructure_status == InfrastructureStatus.PROVIDER_RUNNER_UNAVAILABLE.value


def test_conversation_termination_after_launch_does_not_erase_checkpoint():
    value = order()
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        conversation=ConversationEvidence(
            assessment=ConversationAssessment.INTERRUPTION_SUSPECTED,
            last_observed_at="2026-09-29T21:59:00Z",
        ),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_active_conversation_does_not_mask_failed_launch():
    value = order(executor_binding=executor("build_colony", "UNAVAILABLE"))
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        conversation=ConversationEvidence(
            assessment=ConversationAssessment.ACTIVE_OBSERVED,
            last_observed_at="2026-09-29T22:04:00Z",
        ),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.FAILED.value


def test_no_launch_or_execution_evidence_preserves_insufficient_evidence():
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query="missing-launch",
        candidates=(candidate("missing-launch", "Waterfound/FAE-testnet"),),
        repository=repo("Waterfound/FAE-testnet"),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value


def test_red_team_browsercoin_historical_order_replay_materializes_prework_receipt_only():
    value = order(
        workstream_id="red-team-browsercoin-project-assurance",
        owner="project_assurance",
        repository="Waterfound/Red-Team",
        executor_name="red-team/project-assurance",
        objective="BrowserCoin Project Assurance bounded local validation",
        required_scopes=("browsercoin_bounded_local_validation",),
        authority_binding=authority("browsercoin_bounded_local_validation"),
        executor_binding=executor("red-team/project-assurance"),
    )
    first = admit(value).receipt
    replay = admit(value).receipt
    assert first == replay
    assert first.disposition == "ADMITTED"
    assert first.first_artifact_ref is None
    assert first.execution_triggered is False


def test_fae_design_assurance_historical_branch_only_replay_is_not_silent():
    value = order(
        workstream_id="fae-browsercoin-design-assurance-001",
        owner="fae-design-assurance",
        repository="Waterfound/FAE-testnet",
        executor_name="build_colony",
        objective="BrowserCoin design assurance evidence review",
        required_scopes=("candidate_write",),
    )
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository, "colony/fae-browsercoin-design-assurance-001"),),
        repository=repo(value.repository, "colony/fae-browsercoin-design-assurance-001"),
        launch_admission=launch_evidence(receipt),
    )
    report = inspect_continuity(snapshot)
    assert receipt.disposition == "ADMITTED"
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_fae_design_assurance_replay_converges_when_build_colony_artifact_appears():
    value = order(
        workstream_id="fae-browsercoin-design-assurance-001",
        owner="fae-design-assurance",
        repository="Waterfound/FAE-testnet",
        executor_name="build_colony",
        required_scopes=("candidate_write",),
    )
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-30T01:08:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository, "colony/fae-browsercoin-design-assurance-001"),),
        repository=repo(value.repository, "colony/fae-browsercoin-design-assurance-001"),
        launch_admission=launch_evidence(receipt, observed_at="2026-09-29T22:00:00Z"),
        build_colony=BuildColonyEvidence(
            validated=True,
            workstream_id=value.workstream_id,
            bound_repository=value.repository,
            bound_branch="colony/fae-browsercoin-design-assurance-001",
            current_frontier="BDA-00",
            completed_frontiers=("BDA-LAUNCH-MATERIALIZED",),
            admissible_next=("BDA-01",),
            last_progress_at="2026-09-30T01:07:37Z",
        ),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert report.latest_execution_evidence["ref"].startswith("build_colony:")


def test_wallet_transaction_ux_positive_control_keeps_existing_running_path_authoritative():
    value = order(
        workstream_id="fae-wallet-transaction-ux",
        owner="fae-wallet",
        repository="Waterfound/FAE-testnet",
        executor_name="build_colony",
        required_scopes=("candidate_write",),
        first_artifact_ref=(
            "github://Waterfound/FAE-testnet/branch/"
            "build-colony/wallet-tx-ux-current-main-20260927"
        ),
    )
    receipt = admit(value).receipt
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-27T16:07:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository, "build-colony/wallet-tx-ux-current-main-20260927"),),
        repository=repo(value.repository, "build-colony/wallet-tx-ux-current-main-20260927"),
        launch_admission=launch_evidence(receipt, observed_at="2026-09-27T16:05:00Z"),
        durable=DurableStateEvidence(
            validated=True,
            workstream_id=value.workstream_id,
            bound_repository=value.repository,
            bound_branch="build-colony/wallet-tx-ux-current-main-20260927",
            current_frontier="WTX-01R",
            active_dispatch=True,
            last_progress_at="2026-09-27T16:06:00Z",
        ),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.DEVELOPMENT_PROGRESSING.value
    assert report.latest_execution_evidence["ref"].startswith("durable_state:")


def test_artifact_not_discovered_cannot_be_invented_by_continuity_check():
    value = order()
    receipt = admit(value).receipt
    assert receipt.first_artifact_ref is None
    snapshot = ContinuitySnapshot(
        checked_at="2026-09-29T22:05:00Z",
        query=value.workstream_id,
        candidates=(candidate(value.workstream_id, value.repository),),
        repository=repo(value.repository),
        launch_admission=launch_evidence(receipt),
    )
    report = inspect_continuity(snapshot)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert report.latest_execution_evidence["ref"].startswith("launch_admission:")
