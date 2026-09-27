from dataclasses import replace

import pytest

from general_execution import (
    CoreRehearsalAssertion,
    CoreRehearsalError,
    CoreRehearsalReport,
    REQUIRED_CORE1_ASSERTIONS,
    build_core_rehearsal_report,
)

REVISION = "2d8b37b3b449edd7aa24f682b7c1c302103fe287"
D = "sha256:" + "d" * 64


def assertion(assertion_id, passed=True):
    return CoreRehearsalAssertion(
        assertion_id=assertion_id,
        passed=passed,
        evidence_refs=(f"artifact://{assertion_id}",),
        evidence_digests=(D,),
    )


def complete_assertions(*, failed_id=None):
    return tuple(
        assertion(
            assertion_id,
            passed=assertion_id != failed_id,
        )
        for assertion_id in REQUIRED_CORE1_ASSERTIONS
    )


def test_complete_green_report_is_canonical_and_deterministic():
    report = build_core_rehearsal_report(
        REVISION,
        D,
        tuple(reversed(complete_assertions())),
    )
    assert report.all_passed
    assert tuple(item.assertion_id for item in report.assertions) == tuple(
        sorted(REQUIRED_CORE1_ASSERTIONS)
    )
    assert report.digest == build_core_rehearsal_report(
        REVISION,
        D,
        tuple(reversed(complete_assertions())),
    ).digest


def test_report_cannot_omit_required_core1_assertion():
    assertions = complete_assertions()[:-1]
    with pytest.raises(
        CoreRehearsalError,
        match="assertion set mismatch",
    ):
        build_core_rehearsal_report(
            REVISION,
            D,
            assertions,
        )


def test_report_cannot_fabricate_green_when_one_assertion_failed():
    assertions = complete_assertions(failed_id="cold_resume")
    report = build_core_rehearsal_report(
        REVISION,
        D,
        assertions,
    )
    assert not report.all_passed

    with pytest.raises(
        CoreRehearsalError,
        match="all_passed does not match",
    ):
        replace(report, all_passed=True)


def test_rehearsal_evidence_cannot_depend_on_chat_context():
    report = build_core_rehearsal_report(
        REVISION,
        D,
        complete_assertions(),
    )
    with pytest.raises(
        CoreRehearsalError,
        match="cannot depend on chat context",
    ):
        replace(report, chat_context_required=True)


def test_rehearsal_evidence_cannot_enable_unattended_runtime():
    report = build_core_rehearsal_report(
        REVISION,
        D,
        complete_assertions(),
    )
    with pytest.raises(
        CoreRehearsalError,
        match="cannot enable unattended runtime",
    ):
        replace(report, unattended_runtime_enabled=True)


def test_assertion_requires_durable_evidence_refs_and_digests():
    with pytest.raises(
        CoreRehearsalError,
        match="requires evidence refs",
    ):
        CoreRehearsalAssertion(
            assertion_id="cold_resume",
            passed=True,
            evidence_refs=(),
            evidence_digests=(D,),
        )

    with pytest.raises(
        CoreRehearsalError,
        match="requires evidence digests",
    ):
        CoreRehearsalAssertion(
            assertion_id="cold_resume",
            passed=True,
            evidence_refs=("artifact://cold-resume",),
            evidence_digests=(),
        )


def test_unknown_assertion_id_is_rejected():
    with pytest.raises(
        CoreRehearsalError,
        match="unsupported CORE-1 assertion id",
    ):
        assertion("not-a-core1-assertion")


def test_report_revision_and_verification_receipt_are_strictly_bound():
    with pytest.raises(
        CoreRehearsalError,
        match="40-character commit SHA",
    ):
        build_core_rehearsal_report(
            "bad",
            D,
            complete_assertions(),
        )

    with pytest.raises(
        CoreRehearsalError,
        match="sha256",
    ):
        build_core_rehearsal_report(
            REVISION,
            "bad",
            complete_assertions(),
        )
