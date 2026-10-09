from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .canonical import canonical_json, sha256_digest
from .persistent_burst_host import (
    PersistentBurstExecutionReport,
    PersistentBurstManifest,
    execute_persistent_burst,
)
from .persistent_runtime import (
    PersistentRuntimeEventReport,
    process_persistent_runtime_event,
    trigger_digest_from_event,
)
from .resume_tick import CoreVerificationReceipt, CoreVerificationRequirement
from .core_rehearsal import CoreRehearsalReport
from .state_boundary import StateTransportReceipt

STATE_PLANE_HOST_SCHEMA = "ge.state-plane-host.v1"


class StatePlaneHostError(ValueError):
    pass


class StatePlaneTransport(Protocol):
    def load(self) -> tuple[StateTransportReceipt, bytes]: ...
    def stage_text(self, relative_path: str, content: str) -> None: ...
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


def execute_event_over_state_plane(
    transport: StatePlaneTransport,
    event: dict,
    *,
    core_requirement: CoreVerificationRequirement | None = None,
    core_verification: CoreVerificationReceipt | None = None,
    core_report: CoreRehearsalReport | None = None,
    persist_private_ledger: bool = False,
    runtime_source_revision: str | None = None,
    trigger_commit: str | None = None,
) -> tuple[PersistentRuntimeEventReport, StatePlaneHostReport]:
    """Execute exactly one canonical persistent-runtime event over private state.

    This preserves the current live single-event execution model while changing
    only the persistence transport.
    """
    pre_receipt, payload = transport.load()
    if _raw_digest(payload) != pre_receipt.blob_digest:
        raise StatePlaneHostError("loaded state payload does not match receipt digest")

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "runtime.sqlite"
        db.write_bytes(payload)

        kwargs = {}
        if event.get("operation") == "transition":
            if (
                core_requirement is None
                or core_verification is None
                or core_report is None
            ):
                raise StatePlaneHostError(
                    "transition requires the existing core verification gate"
                )
            authenticated = trigger_digest_from_event(event)
            if authenticated is None:
                raise StatePlaneHostError(
                    "transition did not yield an authenticated trigger digest"
                )
            kwargs = {
                "authenticated_trigger_digest": authenticated,
                "core_requirement": core_requirement,
                "core_verification": core_verification,
                "core_report": core_report,
            }

        execution = process_persistent_runtime_event(db, event, **kwargs)
        post_payload = db.read_bytes()

    if persist_private_ledger:
        if not runtime_source_revision or not trigger_commit:
            raise StatePlaneHostError(
                "private ledger persistence requires runtime source and trigger binding"
            )
        stage_text = getattr(transport, "stage_text", None)
        if not callable(stage_text):
            raise StatePlaneHostError(
                "state transport does not support atomic private ledger staging"
            )
        event_id = event.get("event_id")
        if (
            not isinstance(event_id, str)
            or not event_id
            or len(event_id) > 120
            or re.fullmatch(r"[A-Za-z0-9._-]+", event_id) is None
        ):
            raise StatePlaneHostError("event_id is not safe for private ledger path")
        db_digest = _raw_digest(post_payload)
        envelope = {
            "schema_version": "ge.persistent-runtime-execution.v1",
            "event_report": json.loads(canonical_json(execution)),
            "event_report_digest": execution.digest,
            "database_sha256": db_digest,
        }
        processed = {
            "schema_version": "ge.persistent-runtime-processed-event.v1",
            "event_id": event_id,
            "operation": event.get("operation"),
            "trigger_commit": trigger_commit,
            "event_report_digest": execution.digest,
            "database_sha256": db_digest,
            "runtime_source_revision": runtime_source_revision,
            "authority_created": False,
        }
        manifest = {
            "schema_version": "ge.persistent-runtime-manifest.v1",
            "last_event_id": event_id,
            "last_operation": event.get("operation"),
            "last_trigger_commit": trigger_commit,
            "last_event_report_digest": execution.digest,
            "database_sha256": db_digest,
            "runtime_source_revision": runtime_source_revision,
            "persistent_provider_trigger_enabled": True,
            "authority_created": False,
        }
        stage_text(
            f"ledger/reports/{event_id}.json",
            json.dumps(envelope, sort_keys=True, indent=2) + "\n",
        )
        stage_text(
            f"ledger/processed/{event_id}.json",
            json.dumps(processed, sort_keys=True, indent=2) + "\n",
        )
        stage_text(
            "state/manifest.json",
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        )

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
        execution_disposition=execution.status,
        execution_stop_reason=execution.requested_action_ref or execution.status,
    )
    return execution, report
