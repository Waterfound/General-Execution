from __future__ import annotations

import hashlib

import pytest

from general_execution.state_boundary import StateTransportReceipt
from general_execution.state_plane_host import (
    StatePlaneHostError,
    execute_burst_over_state_plane,
)
from tests.test_persistent_burst_host import (
    bootstrap,
    build_three_events,
    gate,
    loader,
    manifest,
    materialize_events,
)


def raw_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class MemoryCasTransport:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.state_ref = "s_1111111111111111"
        self.receipt = StateTransportReceipt(
            state_ref=self.state_ref,
            blob_digest=raw_digest(payload),
            byte_count=len(payload),
            storage_visibility="private",
        )
        self.commit_count = 0

    def load(self):
        return self.receipt, self.payload

    def commit(self, payload: bytes, *, expected_receipt_digest: str):
        if expected_receipt_digest != self.receipt.digest:
            raise StatePlaneHostError("stale state-plane receipt")
        self.payload = payload
        self.receipt = StateTransportReceipt(
            state_ref=self.state_ref,
            blob_digest=raw_digest(payload),
            byte_count=len(payload),
            storage_visibility="private",
        )
        self.commit_count += 1
        return self.receipt


def initial_db(tmp_path):
    db = tmp_path / "initial.db"
    bootstrap(db)
    return db.read_bytes()


def test_native_burst_runs_over_private_transport_without_provider_coupling(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    transport = MemoryCasTransport(initial_db(tmp_path))

    execution, host = execute_burst_over_state_plane(
        transport,
        manifest(refs),
        loader(root),
        core_requirement=requirement,
        core_verification=receipt,
        core_report=core_report,
    )

    assert execution.stop_reason == "HUMAN_GATE"
    assert execution.final_generation == 3
    assert transport.commit_count == 1
    assert host.state_ref == "s_1111111111111111"
    assert host.pre_blob_digest != host.post_blob_digest
    assert host.execution_report_digest == execution.digest
    assert not host.authority_created


def test_state_plane_host_fails_closed_on_stale_compare_and_swap(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    transport = MemoryCasTransport(initial_db(tmp_path))
    original_commit = transport.commit

    def stale_commit(payload, *, expected_receipt_digest):
        return original_commit(
            payload,
            expected_receipt_digest="sha256:" + "0" * 64,
        )

    transport.commit = stale_commit

    with pytest.raises(StatePlaneHostError, match="stale state-plane receipt"):
        execute_burst_over_state_plane(
            transport,
            manifest(refs),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )


def test_state_plane_host_rejects_payload_receipt_mismatch(tmp_path):
    events, requirement, receipt, core_report = build_three_events(tmp_path)
    root, refs = materialize_events(tmp_path, events)
    transport = MemoryCasTransport(initial_db(tmp_path))
    transport.payload += b"x"

    with pytest.raises(StatePlaneHostError, match="loaded state payload"):
        execute_burst_over_state_plane(
            transport,
            manifest(refs),
            loader(root),
            core_requirement=requirement,
            core_verification=receipt,
            core_report=core_report,
        )
