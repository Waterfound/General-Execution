from __future__ import annotations

from general_execution.continuity_check import (
    ContinuitySnapshot,
    DevelopmentVerdict,
    ExecutorActivationDisposition,
    ExecutorActivationEvidence,
    LaunchAdmissionEvidence,
    LaunchDisposition,
    RepositoryEvidence,
    WorkstreamCandidate,
    inspect_continuity,
)


WORKSTREAM = "eac01-continuity"
REPOSITORY = "Waterfound/General-Execution"
DISPATCH = "geld-eac01-continuity"
RECEIPT_REF = "launch-receipt://gelr-eac01-continuity"


def _candidate():
    return WorkstreamCandidate(
        workstream_id=WORKSTREAM,
        canonical_name=WORKSTREAM,
        repository=REPOSITORY,
        branch="build-colony/eac01-receipt-bound-executor-activation-001",
    )


def _repo():
    return RepositoryEvidence(
        repository=REPOSITORY,
        branch="build-colony/eac01-receipt-bound-executor-activation-001",
        branch_head="a" * 40,
    )


def _launch():
    return LaunchAdmissionEvidence(
        validated=True,
        workstream_id=WORKSTREAM,
        disposition=LaunchDisposition.ADMITTED,
        receipt_ref=RECEIPT_REF,
        launch_id="gel-eac01-continuity",
        repository=REPOSITORY,
        executor="build_colony",
        dispatch_identity=DISPATCH,
        observed_at="2026-10-01T05:00:00Z",
    )


def _activation(
    disposition: ExecutorActivationDisposition,
    *,
    dispatch_identity: str = DISPATCH,
):
    native = (
        "build-colony://run/bc2-eac01"
        if disposition is ExecutorActivationDisposition.EXECUTOR_ACCEPTED
        else None
    )
    condition = (
        "executor://build_colony/available"
        if disposition is ExecutorActivationDisposition.CONDITION_WAIT
        else None
    )
    detail = (
        "native executor rejected bounded activation"
        if disposition is ExecutorActivationDisposition.FAILED_ACTIVATION
        else None
    )
    return ExecutorActivationEvidence(
        validated=True,
        workstream_id=WORKSTREAM,
        disposition=disposition,
        activation_ref="executor-activation://gea-eac01",
        launch_receipt_ref=RECEIPT_REF,
        dispatch_identity=dispatch_identity,
        repository=REPOSITORY,
        executor="build_colony",
        native_execution_ref=native,
        condition_ref=condition,
        observed_at="2026-10-01T05:01:00Z",
        detail=detail,
    )


def _snapshot(activation):
    return ContinuitySnapshot(
        checked_at="2026-10-01T05:02:00Z",
        query=WORKSTREAM,
        candidates=(_candidate(),),
        repository=_repo(),
        launch_admission=_launch(),
        executor_activation=activation,
    )


def test_executor_accepted_is_progress_only_with_native_evidence():
    report = inspect_continuity(
        _snapshot(_activation(ExecutorActivationDisposition.EXECUTOR_ACCEPTED))
    )

    assert report.development_verdict == DevelopmentVerdict.DEVELOPMENT_PROGRESSING.value
    assert report.latest_execution_evidence is not None
    assert report.latest_execution_evidence["ref"].startswith("executor_activation:")
    assert report.execution_triggered is False


def test_activation_condition_wait_is_explicit_and_not_execution():
    report = inspect_continuity(
        _snapshot(_activation(ExecutorActivationDisposition.CONDITION_WAIT))
    )

    assert report.development_verdict == DevelopmentVerdict.CONDITION_WAIT.value
    assert report.blocking_gate is not None
    assert report.blocking_gate["ref"] == "executor://build_colony/available"
    assert report.execution_triggered is False


def test_failed_activation_is_explicit_failure():
    report = inspect_continuity(
        _snapshot(_activation(ExecutorActivationDisposition.FAILED_ACTIVATION))
    )

    assert report.development_verdict == DevelopmentVerdict.FAILED.value
    assert report.blocking_gate is not None
    assert report.blocking_gate["ref"] == "executor-activation://gea-eac01"
    assert report.execution_triggered is False


def test_mismatched_dispatch_identity_cannot_create_false_progress():
    report = inspect_continuity(
        _snapshot(
            _activation(
                ExecutorActivationDisposition.EXECUTOR_ACCEPTED,
                dispatch_identity="geld-wrong",
            )
        )
    )

    assert report.development_verdict == DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value
    assert "executor_activation_mismatch_or_unvalidated" in report.evidence_warnings
    assert report.latest_execution_evidence is not None
    assert report.latest_execution_evidence["ref"].startswith("launch_admission:")
