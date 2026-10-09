from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .canonical import sha256_digest
from .persistent_burst_host import (
    PersistentBurstExecutionReport,
    PersistentBurstManifest,
    execute_persistent_burst,
)
from .resume_tick import CoreVerificationReceipt, CoreVerificationRequirement
from .core_rehearsal import CoreRehearsalReport
from .state_boundary import StateTransportReceipt

STATE_PLANE_HOST_SCHEMA = "ge.state-plane-host.v1"


class StatePlaneHostError(ValueError):
    pass


class StatePlaneTransport(Protocol):
    def load(self) -> tuple[StateTransportReceipt, bytes]: ...
    def commit(
        self,
        payload: bytes,
        *,
        expected_receipt_digest: str,
    ) -> StateTransportReceipt: ...


def _raw_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class StatePlaneHostReport:
    state_ref: str
    pre_blob_digest: str
    post_blob_digest: str
    pre_receipt_digest: str
    post_receipt_digest: str
    execution_report_digest: str
    execution_disposition: str
    execution_stop_reason: str
    authority_created: bool = False
    schema_version: str = STATE_PLANE_HOST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != STATE_PLANE_HOST_SCHEMA:
            raise StatePlaneHostError("unsupported state-plane host schema")
        if self.authority_created:
            raise StatePlaneHostError("state-plane host cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def execute_burst_over_state_plane(
    transport: StatePlaneTransport,
    manifest: PersistentBurstManifest,
    load_event_bytes: Callable[[str], bytes],
    *,
    core_requirement: CoreVerificationRequirement,
    core_verification: CoreVerificationReceipt,
    core_report: CoreRehearsalReport,
) -> tuple[PersistentBurstExecutionReport, StatePlaneHostReport]:
    pre_receipt, payload = transport.load()
    if _raw_digest(payload) != pre_receipt.blob_digest:
        raise StatePlaneHostError("loaded state payload does not match receipt digest")

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "runtime.sqlite"
        db.write_bytes(payload)

        execution = execute_persistent_burst(
            db,
            manifest,
            load_event_bytes,
            core_requirement=core_requirement,
            core_verification=core_verification,
            core_report=core_report,
        )

        post_payload = db.read_bytes()

    post_receipt = transport.commit(
        post_payload,
        expected_receipt_digest=pre_receipt.digest,
    )
    if post_receipt.state_ref != pre_receipt.state_ref:
        raise StatePlaneHostError("state-plane commit changed opaque state_ref")
    if _raw_digest(post_payload) != post_receipt.blob_digest:
        raise StatePlaneHostError("committed state payload does not match receipt digest")

    report = StatePlaneHostReport(
        state_ref=pre_receipt.state_ref,
        pre_blob_digest=pre_receipt.blob_digest,
        post_blob_digest=post_receipt.blob_digest,
        pre_receipt_digest=pre_receipt.digest,
        post_receipt_digest=post_receipt.digest,
        execution_report_digest=execution.digest,
        execution_disposition=execution.disposition,
        execution_stop_reason=execution.stop_reason,
    )
    return execution, report
