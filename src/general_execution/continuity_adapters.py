from __future__ import annotations

from typing import Mapping, Sequence

from .continuity_check import (
    BuildColonyEvidence,
    ConversationAssessment,
    ConversationEvidence,
    DurableStateEvidence,
    FailureScope,
    GateEvidence,
    GateKind,
    LaunchAdmissionEvidence,
    LaunchDisposition,
    ProviderEvidence,
    ProviderState,
    RepositoryEvidence,
    WorkstreamCandidate,
)


def _tuple_strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise ValueError("expected a sequence of strings")
    return tuple(value)


def candidate_from_mapping(data: Mapping[str, object]) -> WorkstreamCandidate:
    return WorkstreamCandidate(
        workstream_id=str(data["workstream_id"]),
        canonical_name=str(data["canonical_name"]),
        repository=str(data["repository"]) if data.get("repository") is not None else None,
        branch=str(data["branch"]) if data.get("branch") is not None else None,
        aliases=_tuple_strings(data.get("aliases")),
    )


def conversation_from_mapping(data: Mapping[str, object] | None) -> ConversationEvidence:
    if data is None:
        return ConversationEvidence()
    return ConversationEvidence(
        assessment=ConversationAssessment(str(data.get("assessment", ConversationAssessment.STATE_UNKNOWN.value))),
        last_observed_at=str(data["last_observed_at"]) if data.get("last_observed_at") is not None else None,
    )


def repository_from_mapping(data: Mapping[str, object] | None) -> RepositoryEvidence | None:
    if data is None:
        return None
    return RepositoryEvidence(
        repository=str(data["repository"]),
        main_revision=str(data["main_revision"]) if data.get("main_revision") is not None else None,
        branch=str(data["branch"]) if data.get("branch") is not None else None,
        branch_head=str(data["branch_head"]) if data.get("branch_head") is not None else None,
        latest_related_commit=str(data["latest_related_commit"]) if data.get("latest_related_commit") is not None else None,
        latest_related_commit_at=str(data["latest_related_commit_at"]) if data.get("latest_related_commit_at") is not None else None,
        pull_request_number=int(data["pull_request_number"]) if data.get("pull_request_number") is not None else None,
        pull_request_state=str(data["pull_request_state"]) if data.get("pull_request_state") is not None else None,
        pull_request_mergeable=bool(data["pull_request_mergeable"]) if data.get("pull_request_mergeable") is not None else None,
        pull_request_merged=bool(data.get("pull_request_merged", False)),
        canonical_contains_workstream=bool(data.get("canonical_contains_workstream", False)),
    )


def durable_from_mapping(data: Mapping[str, object] | None) -> DurableStateEvidence | None:
    if data is None:
        return None
    return DurableStateEvidence(
        validated=bool(data.get("validated", False)),
        workstream_id=str(data["workstream_id"]),
        bound_repository=str(data["bound_repository"]) if data.get("bound_repository") is not None else None,
        bound_branch=str(data["bound_branch"]) if data.get("bound_branch") is not None else None,
        bound_branch_head=str(data["bound_branch_head"]) if data.get("bound_branch_head") is not None else None,
        current_frontier=str(data["current_frontier"]) if data.get("current_frontier") is not None else None,
        completed_frontiers=_tuple_strings(data.get("completed_frontiers")),
        admissible_next=_tuple_strings(data.get("admissible_next")),
        active_dispatch=bool(data.get("active_dispatch", False)),
        last_progress_at=str(data["last_progress_at"]) if data.get("last_progress_at") is not None else None,
        wake_condition=str(data["wake_condition"]) if data.get("wake_condition") is not None else None,
        scheduled_checkpoint=str(data["scheduled_checkpoint"]) if data.get("scheduled_checkpoint") is not None else None,
        execution_expected=bool(data.get("execution_expected", False)),
        recovery_semantics_exhausted=bool(data.get("recovery_semantics_exhausted", False)),
        terminal_verdict=str(data["terminal_verdict"]) if data.get("terminal_verdict") is not None else None,
        failed_terminal_reason=str(data["failed_terminal_reason"]) if data.get("failed_terminal_reason") is not None else None,
    )


def build_colony_from_mapping(data: Mapping[str, object] | None) -> BuildColonyEvidence | None:
    if data is None:
        return None
    return BuildColonyEvidence(
        validated=bool(data.get("validated", False)),
        workstream_id=str(data["workstream_id"]),
        bound_repository=str(data["bound_repository"]) if data.get("bound_repository") is not None else None,
        bound_branch=str(data["bound_branch"]) if data.get("bound_branch") is not None else None,
        bound_branch_head=str(data["bound_branch_head"]) if data.get("bound_branch_head") is not None else None,
        current_frontier=str(data["current_frontier"]) if data.get("current_frontier") is not None else None,
        completed_frontiers=_tuple_strings(data.get("completed_frontiers")),
        admissible_next=_tuple_strings(data.get("admissible_next")),
        terminal_verdict=str(data["terminal_verdict"]) if data.get("terminal_verdict") is not None else None,
        last_progress_at=str(data["last_progress_at"]) if data.get("last_progress_at") is not None else None,
    )


def provider_from_mapping(data: Mapping[str, object] | None) -> ProviderEvidence | None:
    if data is None:
        return None
    return ProviderEvidence(
        provider=str(data["provider"]),
        state=ProviderState(str(data.get("state", ProviderState.UNKNOWN.value))),
        observed_at=str(data["observed_at"]) if data.get("observed_at") is not None else None,
        subject_revision=str(data["subject_revision"]) if data.get("subject_revision") is not None else None,
        failure_scope=FailureScope(str(data.get("failure_scope", FailureScope.NONE.value))),
        detail=str(data["detail"]) if data.get("detail") is not None else None,
    )


def gates_from_mappings(values: Sequence[Mapping[str, object]] | None) -> tuple[GateEvidence, ...]:
    if not values:
        return ()
    return tuple(
        GateEvidence(
            kind=GateKind(str(item["kind"])),
            ref=str(item["ref"]),
            reason=str(item["reason"]),
            frontier=str(item["frontier"]),
            satisfied=bool(item.get("satisfied", False)),
        )
        for item in values
    )


def launch_admission_from_mapping(
    data: Mapping[str, object] | None,
) -> LaunchAdmissionEvidence | None:
    if data is None:
        return None
    return LaunchAdmissionEvidence(
        validated=bool(data.get("validated", False)),
        workstream_id=str(data["workstream_id"]),
        disposition=LaunchDisposition(str(data["disposition"])),
        receipt_ref=str(data["receipt_ref"]),
        launch_id=str(data["launch_id"]) if data.get("launch_id") is not None else None,
        repository=str(data["repository"]) if data.get("repository") is not None else None,
        executor=str(data["executor"]) if data.get("executor") is not None else None,
        dispatch_identity=(
            str(data["dispatch_identity"])
            if data.get("dispatch_identity") is not None
            else None
        ),
        first_artifact_ref=(
            str(data["first_artifact_ref"])
            if data.get("first_artifact_ref") is not None
            else None
        ),
        observed_at=str(data["observed_at"]) if data.get("observed_at") is not None else None,
        recovery_semantics_exhausted=bool(
            data.get("recovery_semantics_exhausted", False)
        ),
        detail=str(data["detail"]) if data.get("detail") is not None else None,
    )
