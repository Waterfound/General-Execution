from __future__ import annotations

from general_execution.continuity_check import (
    BuildColonyEvidence,
    ConversationAssessment,
    ConversationEvidence,
    ContinuitySnapshot,
    DevelopmentVerdict,
    DurableStateEvidence,
    FailureScope,
    GateEvidence,
    GateKind,
    ProviderEvidence,
    ProviderState,
    RepositoryEvidence,
    WorkstreamCandidate,
    inspect_continuity,
    render_report,
)

C = WorkstreamCandidate(
    workstream_id="rde",
    canonical_name="FAE — Representative Device Evidence Readiness",
    repository="Waterfound/FAE-testnet",
    branch="colony/fae-representative-device-evidence-readiness-001",
    aliases=("Representative Device Evidence Readiness", "RDE"),
)


def snap(**kwargs):
    base = dict(checked_at="2026-09-28T21:50:00Z", query="RDE", candidates=(C,))
    base.update(kwargs)
    return ContinuitySnapshot(**base)


def repo(**kwargs):
    base = dict(
        repository="Waterfound/FAE-testnet",
        main_revision="a" * 40,
        branch=C.branch,
        branch_head="b" * 40,
    )
    base.update(kwargs)
    return RepositoryEvidence(**base)


def durable(**kwargs):
    base = dict(
        validated=True,
        workstream_id="rde",
        bound_repository="Waterfound/FAE-testnet",
        bound_branch=C.branch,
        bound_branch_head="b" * 40,
        current_frontier="RDE-08",
    )
    base.update(kwargs)
    return DurableStateEvidence(**base)


def verdict(snapshot):
    return inspect_continuity(snapshot).development_verdict


def test_conversation_stops_but_active_execution_continues_after_it():
    s = snap(
        conversation=ConversationEvidence(ConversationAssessment.INTERRUPTION_SUSPECTED, "2026-09-28T20:00:00Z"),
        repository=repo(latest_related_commit="b" * 40, latest_related_commit_at="2026-09-28T20:05:00Z"),
        durable=durable(active_dispatch=True, last_progress_at="2026-09-28T20:05:00Z"),
    )
    assert verdict(s) == DevelopmentVerdict.CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED.value


def test_checkpointed_resumable_requires_validated_matching_state():
    s = snap(repository=repo(), durable=durable(admissible_next=("RDE-08", "RDE-09")))
    assert verdict(s) == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_scheduled_wait():
    s = snap(repository=repo(), durable=durable(scheduled_checkpoint="2026-10-01T00:00:00Z"))
    assert verdict(s) == DevelopmentVerdict.SCHEDULED_WAIT.value


def test_condition_wait():
    s = snap(repository=repo(), durable=durable(wake_condition="provider artifact becomes AVAILABLE"))
    assert verdict(s) == DevelopmentVerdict.CONDITION_WAIT.value


def test_human_gate_requires_exact_gate_evidence():
    gate = GateEvidence(GateKind.HUMAN, "authority://test/physical", "physical device measurement required", "RDE-16")
    s = snap(repository=repo(), durable=durable(admissible_next=("RDE-16",)), gates=(gate,))
    assert verdict(s) == DevelopmentVerdict.HUMAN_GATE.value


def test_external_evidence_gate():
    gate = GateEvidence(GateKind.EXTERNAL_EVIDENCE, "evidence://independent-operator", "independent operator evidence required", "IO-12")
    s = snap(repository=repo(), durable=durable(terminal_verdict="INDEPENDENT_OPERATOR_EVIDENCE_PACKAGE_READY"), gates=(gate,))
    assert verdict(s) == DevelopmentVerdict.EXTERNAL_EVIDENCE_GATE.value


def test_done_technical_before_canonical_merge():
    s = snap(repository=repo(), durable=durable(terminal_verdict="CONTINUITY_CHECK_V1_READY"))
    report = inspect_continuity(s)
    assert report.development_verdict == DevelopmentVerdict.DONE_TECHNICAL.value
    assert report.canonical_state_reconciliation_recommended is True


def test_done_canonical_repository_wins_over_stale_durable_active_state():
    s = snap(
        repository=repo(pull_request_number=10, pull_request_state="closed", pull_request_merged=True, canonical_contains_workstream=True),
        durable=durable(active_dispatch=True),
    )
    assert verdict(s) == DevelopmentVerdict.DONE_CANONICAL.value


def test_open_pr_alone_is_not_progress():
    s = snap(repository=repo(pull_request_number=10, pull_request_state="open", pull_request_merged=False))
    assert verdict(s) == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value


def test_stall_requires_explicit_bounded_recovery_exhaustion():
    s = snap(repository=repo(), durable=durable(admissible_next=("RDE-08",), execution_expected=True, recovery_semantics_exhausted=True))
    assert verdict(s) == DevelopmentVerdict.DEVELOPMENT_STALLED.value


def test_no_elapsed_time_only_stall():
    s = snap(repository=repo(), durable=durable(admissible_next=("RDE-08",), execution_expected=True, recovery_semantics_exhausted=False))
    assert verdict(s) == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_provider_unavailable_does_not_mean_failed():
    s = snap(
        repository=repo(),
        durable=durable(admissible_next=("RDE-08",)),
        provider=ProviderEvidence("github-actions", ProviderState.UNAVAILABLE, subject_revision="b" * 40, failure_scope=FailureScope.PROVIDER),
    )
    report = inspect_continuity(s)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert report.infrastructure_status == "PROVIDER_RUNNER_UNAVAILABLE"


def test_provider_failure_isolated_does_not_mean_failed():
    s = snap(
        repository=repo(),
        durable=durable(admissible_next=("RDE-08",)),
        provider=ProviderEvidence("github-actions", ProviderState.FAILED, subject_revision="b" * 40, failure_scope=FailureScope.PROVIDER),
    )
    assert verdict(s) == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_workload_test_failure_is_failed():
    s = snap(
        repository=repo(),
        provider=ProviderEvidence("runner", ProviderState.FAILED, subject_revision="b" * 40, failure_scope=FailureScope.WORKLOAD, detail="pytest failed"),
    )
    assert verdict(s) == DevelopmentVerdict.FAILED.value


def test_wrong_sha_provider_run_is_ignored():
    s = snap(
        repository=repo(),
        durable=durable(admissible_next=("RDE-08",)),
        provider=ProviderEvidence("runner", ProviderState.ACTIVE, subject_revision="c" * 40),
    )
    report = inspect_continuity(s)
    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert "provider_evidence_revision_mismatch" in report.evidence_warnings


def test_copied_durable_state_from_other_branch_fails_closed():
    bad = durable(bound_branch="other", admissible_next=("RDE-08",))
    s = snap(repository=repo(), durable=bad)
    report = inspect_continuity(s)
    assert report.development_verdict == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value
    assert "durable_state_mismatch_or_unvalidated" in report.evidence_warnings


def test_branch_head_mismatch_fails_closed():
    bad = durable(bound_branch_head="d" * 40, admissible_next=("RDE-08",))
    s = snap(repository=repo(), durable=bad)
    assert verdict(s) == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value


def test_ambiguous_workstream_name_fails_closed():
    other = WorkstreamCandidate("rde2", "RDE Secondary", aliases=("RDE",))
    s = ContinuitySnapshot(checked_at="2026-09-28T00:00:00Z", query="RDE", candidates=(C, other))
    assert verdict(s) == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value


def test_conversation_alive_does_not_override_stall():
    s = snap(
        conversation=ConversationEvidence(ConversationAssessment.ACTIVE_OBSERVED, "2026-09-28T21:00:00Z"),
        repository=repo(),
        durable=durable(admissible_next=("RDE-08",), execution_expected=True, recovery_semantics_exhausted=True),
    )
    assert verdict(s) == DevelopmentVerdict.DEVELOPMENT_STALLED.value


def test_old_green_ci_alone_cannot_create_progress():
    provider = ProviderEvidence("github-actions", ProviderState.COMPLETED, observed_at="2026-09-20T00:00:00Z", subject_revision="b" * 40)
    s = snap(repository=repo(), provider=provider)
    assert verdict(s) == DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value


def test_build_colony_can_support_resumable_when_durable_absent():
    bc = BuildColonyEvidence(
        validated=True,
        workstream_id="rde",
        bound_repository="Waterfound/FAE-testnet",
        bound_branch=C.branch,
        bound_branch_head="b" * 40,
        current_frontier="RDE-08",
        admissible_next=("RDE-08",),
    )
    s = snap(repository=repo(), build_colony=bc)
    assert verdict(s) == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value


def test_renderer_is_compact_and_read_only_language():
    s = snap(repository=repo(), durable=durable(admissible_next=("RDE-08",)))
    text = render_report(inspect_continuity(s))
    assert "Continuity Check" in text
    assert "CHECKPOINTED_RESUMABLE" in text
    assert "Action: RESUME_DURABLE_EXECUTION" in text
    assert "trigger" not in text.lower()


def test_authority_and_execution_side_effect_flags_are_always_false():
    report = inspect_continuity(snap(repository=repo(), durable=durable(admissible_next=("RDE-08",))))
    assert report.authority_created is False
    assert report.execution_triggered is False
