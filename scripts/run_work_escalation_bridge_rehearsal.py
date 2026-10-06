#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.canonical import sha256_digest
from general_execution.execution_launch_admission import admit_or_replay_execution_launch
from general_execution.executor_activation import (
    SqliteExecutorActivationStore,
    activate_or_reconcile_executor,
)
from general_execution.work_escalation_bridge import (
    ExternalWorkExecutorActivationAdapter,
    SqliteWorkEscalationStore,
    WorkInvocationAuthority,
    WorkPlatformObservation,
    build_work_launch_order,
    prepare_work_escalation_request,
    prepare_work_platform_activation_request,
    record_work_platform_observation,
    work_executor_capability,
)
from general_execution.work_sparse_unattended import (
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    decide_work_sparse_route,
)


AUTH_REF = "authority://rehearsal/work-escalation"


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    out=args.output
    if out.exists():
        raise SystemExit("Refusing to overwrite Work escalation rehearsal evidence")
    out.mkdir(parents=True)

    envelope=UnattendedAuthorityEnvelope(
        envelope_id="work-escalation-rehearsal",
        authority_ref=AUTH_REF,
        allowed_repositories=("Waterfound/General-Execution",),
        allowed_actions=("read_state",),
        forbidden_actions=("merge_main","release","paid_spend"),
        max_work_invocations=1,
        max_paid_spend_cents=0,
    )
    work=UnattendedWorkItem(
        work_id="work-escalation-rehearsal-001",
        objective="Rehearse receipt-bound Work escalation without launching real Work",
        repository="Waterfound/General-Execution",
        source_revision="a"*40,
        authority_ref=AUTH_REF,
        required_capabilities=("browser_ui",),
        requested_actions=("read_state",),
    )
    route=decide_work_sparse_route(
        envelope,
        work,
        (
            ExecutorCapability(
                executor_id="work",
                capabilities=("browser_ui","cloud_computer"),
                cost_rank=100,
                requires_work=True,
                evidence_ref="chatgpt-work://rehearsal-capability",
            ),
        ),
    )
    assert route.disposition=="DISPATCH"
    assert route.selected_executor_id=="work"

    authority=WorkInvocationAuthority(
        actor="Waterfound",
        authority_ref=AUTH_REF,
        authority_boundary="Synthetic rehearsal only; no real Work launch.",
        granted_scopes=("executor_activation","work_invocation"),
        max_invocations=1,
    )
    request=prepare_work_escalation_request(envelope,work,route,authority)
    bridge_db=out/"work-escalation.sqlite"
    bridge=SqliteWorkEscalationStore(bridge_db)
    reserved=bridge.reserve(request)
    assert reserved.slot_index==1

    capability=work_executor_capability(
        evidence_ref="chatgpt-work://external-platform-rehearsal"
    )
    order=build_work_launch_order(request,authority,capability)
    receipt=admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor="Waterfound",
    ).receipt
    assert receipt.disposition=="ADMITTED"
    platform_request=prepare_work_platform_activation_request(reserved,receipt)
    assert platform_request.execution_triggered is False

    reauth=WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="HUMAN_REAUTH_REQUIRED",
        observed_at="2026-10-06T16:50:00Z",
        evidence_ref="rehearsal://vercel/auth-challenge",
        evidence_digest=sha256_digest({"provider":"vercel","reauth":True}),
        condition_ref="auth://vercel/reauthenticate",
    )
    gated=bridge.compare_and_swap(
        reserved,
        record_work_platform_observation(reserved,platform_request,reauth),
    )
    assert gated.status=="human_reauth_required"

    recovered=SqliteWorkEscalationStore(bridge_db).load(request.request_id)
    assert recovered==gated
    assert recovered.slot_index==1

    accepted=WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="PLATFORM_ACCEPTED",
        observed_at="2026-10-06T16:55:00Z",
        evidence_ref="rehearsal://work/native-execution",
        evidence_digest=sha256_digest({"native":"synthetic-work-ref"}),
        native_execution_ref="chatgpt-work://rehearsal/native-execution",
    )
    accepted_state=bridge.compare_and_swap(
        recovered,
        record_work_platform_observation(recovered,platform_request,accepted),
    )
    assert accepted_state.status=="platform_accepted"

    adapter=ExternalWorkExecutorActivationAdapter(
        capability,
        platform_request,
        accepted,
    )
    eac=SqliteExecutorActivationStore(out/"eac.sqlite")
    first=activate_or_reconcile_executor(eac,receipt,capability,adapter)
    second=activate_or_reconcile_executor(eac,receipt,capability,adapter)
    assert first.state.status=="executor_accepted"
    assert first.state.native_execution_ref=="chatgpt-work://rehearsal/native-execution"
    assert second.state==first.state
    assert adapter.calls==1

    report={
        "schema_version":"ge.work-escalation-bridge-rehearsal.v1",
        "status":"PASS_NOT_REAL_WORK",
        "route_selected_executor":route.selected_executor_id,
        "work_required":route.work_required,
        "budget_slot":reserved.slot_index,
        "request_id":request.request_id,
        "launch_receipt_id":receipt.receipt_id,
        "dispatch_identity":receipt.dispatch_identity,
        "platform_request_id":platform_request.platform_request_id,
        "reauth_action_ref":gated.condition_ref,
        "restart_recovered_same_slot":recovered.slot_index==reserved.slot_index,
        "native_execution_ref":first.state.native_execution_ref,
        "eac_replay_status":second.replay_status,
        "provider_observation_simulated":True,
        "real_work_launched":False,
        "credentials_persisted":False,
        "cookies_persisted":False,
        "tokens_persisted":False,
        "authority_created":False,
        "pre_platform_execution_triggered":False,
        "terminal_disposition":"CONTROL_PLANE_PASS__REAL_WORK_PLATFORM_ACTIVATION_CAPABILITY_EXTERNAL_GATE",
    }
    (out/"report.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
