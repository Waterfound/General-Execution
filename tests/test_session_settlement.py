import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from general_execution import (
    ArtifactRef,
    ExecutionSpec,
    REFERENCE_CAPABILITY,
    REFERENCE_EVIDENCE,
    REFERENCE_TASK_KIND,
    ResultEnvelope,
    RunnerRegistry,
    bind_session,
    plan_execution,
    reference_runner,
    start_session,
)
from general_execution.session_settlement import (
    DurableSessionRecord,
    SessionSettlementConflict,
    SessionSettlementIntegrityError,
    SQLiteSessionSettlementStore,
    load_session_record,
    serialize_session_record,
)

D = "sha256:" + "7" * 64
ZERO = "sha256:" + "0" * 64


def running_session(suffix="one"):
    runner = reference_runner()
    spec = ExecutionSpec(
        producer="build-colony",
        producer_revision="bc-session-settlement",
        task_kind=REFERENCE_TASK_KIND,
        objective=f"Durable Session settlement {suffix}",
        source_revision=f"source-session-settlement-{suffix}",
        required_capabilities=(REFERENCE_CAPABILITY,),
        evidence_requirements=(REFERENCE_EVIDENCE,),
        inputs=(ArtifactRef("package", f"bc://session-settlement/{suffix}", D),),
    )
    registry = RunnerRegistry((runner,))
    plan = plan_execution(spec, registry)
    session = start_session(bind_session(spec, registry, plan))
    return runner, spec, registry, plan, session


def result_for(session, spec, runner, summary="result-a"):
    return ResultEnvelope(
        session_id=session.session_id,
        spec_id=spec.spec_id,
        spec_digest=spec.digest,
        runner_id=runner.runner_id,
        attempt=session.attempt,
        status="completed",
        evidence=(),
        summary=summary,
    )


def test_running_session_registration_survives_reopen(tmp_path):
    path = tmp_path / "sessions.db"
    _, _, _, _, session = running_session()
    receipt = SQLiteSessionSettlementStore(path).register_running(session)
    assert not receipt.idempotent
    assert receipt.state == "running"
    reopened = SQLiteSessionSettlementStore(path)
    record = reopened.load(session.session_id)
    assert record == DurableSessionRecord(session, session)


def test_exact_running_registration_replay_is_idempotent(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    *_, session = running_session()
    first = store.register_running(session)
    second = store.register_running(session)
    assert not first.idempotent
    assert second.idempotent
    assert first.committed_record_digest == second.committed_record_digest


def test_result_submission_is_durable_and_reconstructs_result(tmp_path):
    path = tmp_path / "sessions.db"
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    store = SQLiteSessionSettlementStore(path)
    store.register_running(session)
    receipt = store.submit_result(session, result)
    assert not receipt.idempotent
    assert receipt.state == "result_submitted"
    assert receipt.result_digest == result.digest

    record = SQLiteSessionSettlementStore(path).load(session.session_id)
    assert record is not None
    assert record.current_session.state == "result_submitted"
    assert record.current_session.result_digest == result.digest
    assert record.result == result


def test_lost_ack_result_replay_is_idempotent(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    store.register_running(session)
    first = store.submit_result(session, result)
    second = store.submit_result(session, result)
    assert not first.idempotent
    assert second.idempotent
    assert first.committed_record_digest == second.committed_record_digest


def test_different_result_cannot_replace_committed_result(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    first = result_for(session, spec, runner, "first")
    second = result_for(session, spec, runner, "second")
    assert first.digest != second.digest
    store.register_running(session)
    store.submit_result(session, first)
    with pytest.raises(SessionSettlementConflict):
        store.submit_result(session, second)
    assert store.load(session.session_id).result == first


def test_revocation_is_durable_and_idempotent(tmp_path):
    path = tmp_path / "sessions.db"
    *_, session = running_session()
    store = SQLiteSessionSettlementStore(path)
    store.register_running(session)
    first = store.revoke(session)
    second = store.revoke(session)
    assert not first.idempotent
    assert second.idempotent
    assert second.state == "revoked"
    record = SQLiteSessionSettlementStore(path).load(session.session_id)
    assert record.current_session.state == "revoked"
    assert record.result is None


def test_result_after_revocation_is_conflict(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    store.register_running(session)
    store.revoke(session)
    with pytest.raises(SessionSettlementConflict):
        store.submit_result(session, result)


def test_revocation_after_result_is_conflict(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    store.register_running(session)
    store.submit_result(session, result)
    with pytest.raises(SessionSettlementConflict):
        store.revoke(session)


def test_two_concurrent_same_result_settlements_converge(tmp_path):
    path = tmp_path / "sessions.db"
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    SQLiteSessionSettlementStore(path).register_running(session)

    def settle_once():
        receipt = SQLiteSessionSettlementStore(path).submit_result(session, result)
        return receipt.idempotent, receipt.committed_record_digest

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: settle_once(), range(2)))
    assert sorted(flag for flag, _ in outcomes) == [False, True]
    assert outcomes[0][1] == outcomes[1][1]


def test_competing_result_and_revocation_have_one_terminal_winner(tmp_path):
    path = tmp_path / "sessions.db"
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    SQLiteSessionSettlementStore(path).register_running(session)

    def submit():
        try:
            return SQLiteSessionSettlementStore(path).submit_result(session, result).state
        except SessionSettlementConflict:
            return "conflict"

    def revoke():
        try:
            return SQLiteSessionSettlementStore(path).revoke(session).state
        except SessionSettlementConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(submit)
        b = pool.submit(revoke)
        states = {a.result(), b.result()}
    assert "conflict" in states
    assert len(states & {"result_submitted", "revoked"}) == 1
    assert SQLiteSessionSettlementStore(path).load(session.session_id).current_session.state in {
        "result_submitted",
        "revoked",
    }


def test_settlement_requires_prior_durable_running_registration(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    with pytest.raises(SessionSettlementConflict):
        store.submit_result(session, result_for(session, spec, runner))


def test_same_session_id_with_changed_source_binding_is_rejected(tmp_path):
    store = SQLiteSessionSettlementStore(tmp_path / "sessions.db")
    runner, spec, _, _, session = running_session()
    store.register_running(session)
    forged = replace(session, spec_id="ges-forged")
    assert forged.session_id == session.session_id
    forged_result = ResultEnvelope(
        session_id=forged.session_id,
        spec_id=forged.spec_id,
        spec_digest=forged.spec_digest,
        runner_id=forged.runner_id,
        attempt=forged.attempt,
        status="completed",
        summary="forged binding",
    )
    with pytest.raises(SessionSettlementConflict):
        store.submit_result(forged, forged_result)
    assert store.load(session.session_id).current_session == session


def test_record_round_trip_is_canonical_and_strict(tmp_path):
    runner, spec, _, _, session = running_session()
    result = result_for(session, spec, runner)
    from general_execution import submit_result

    record = DurableSessionRecord(session, submit_result(session, result), result)
    payload = serialize_session_record(record)
    loaded = load_session_record(payload, expected_record_digest=record.digest)
    assert loaded == record

    import json

    data = json.loads(payload)
    del data["current_session"]["schema_version"]
    bad = json.dumps(data, sort_keys=True, separators=(",", ":"))
    with pytest.raises(SessionSettlementIntegrityError):
        load_session_record(bad)


def test_store_metadata_corruption_is_rejected(tmp_path):
    path = tmp_path / "sessions.db"
    *_, session = running_session()
    SQLiteSessionSettlementStore(path).register_running(session)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_session_settlement_metadata SET value = 'unsupported' "
            "WHERE key = 'schema_version'"
        )
    with pytest.raises(SessionSettlementIntegrityError):
        SQLiteSessionSettlementStore(path)


def test_row_digest_corruption_is_rejected(tmp_path):
    path = tmp_path / "sessions.db"
    *_, session = running_session()
    store = SQLiteSessionSettlementStore(path)
    store.register_running(session)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE ge_session_settlements SET record_digest = ? WHERE session_id = ?",
            (ZERO, session.session_id),
        )
    with pytest.raises(SessionSettlementIntegrityError):
        store.load(session.session_id)


def test_memory_store_is_rejected():
    with pytest.raises(ValueError):
        SQLiteSessionSettlementStore(":memory:")
