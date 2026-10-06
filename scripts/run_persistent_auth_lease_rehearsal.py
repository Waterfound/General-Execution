#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from general_execution.canonical import sha256_digest
from general_execution.persistent_auth_lease import (
    ProviderAuthObservation,
    ProviderAuthQueueItem,
    SqliteProviderAuthStateStore,
    auth_path_to_dict,
    select_provider_auth_path,
)


def evidence(label: str) -> str:
    return sha256_digest({"persistent-auth-rehearsal": label})


def observation(surface: str, outcome: str, when: str, *, human: bool = False):
    return ProviderAuthObservation(
        provider_id="vercel",
        surface=surface,
        outcome=outcome,
        observed_at=when,
        evidence_ref=f"rehearsal://vercel/{surface}/{outcome.lower()}",
        evidence_digest=evidence(f"{surface}-{outcome}-{when}"),
        human_interaction=human,
    )


def item(queue_id: str, priority: int):
    return ProviderAuthQueueItem(
        queue_id=queue_id,
        provider_id="vercel",
        work_id=f"work-{queue_id}",
        repository="Waterfound/FAE-testnet",
        authority_ref="authority://waterfound/work-sparse-unattended-001",
        source_revision="rehearsal-source",
        requested_actions=("read_state",),
        required_capabilities=("browser_ui",),
        priority=priority,
    )


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    out=args.output
    if out.exists():
        raise SystemExit("Refusing to overwrite persistent-auth rehearsal evidence")
    out.mkdir(parents=True)
    db=out/"provider-auth.db"

    store=SqliteProviderAuthStateStore(db)
    q1=item("q1",10)
    q2=item("q2",20)
    q3=item("q3",30)
    for q in (q3,q1,q2):
        store.enqueue(q)

    before=store.plan_drain("vercel",max_items=3)
    assert before.disposition=="HUMAN_REAUTH_REQUIRED"
    assert before.queue_depth==3
    assert before.selected_queue_ids==()

    browser=store.observe(
        observation(
            "cloud_browser",
            "AUTH_SUCCESS",
            "2026-10-06T07:30:00Z",
            human=True,
        )
    )
    after_login=store.plan_drain("vercel",max_items=3)
    assert after_login.disposition=="USE_AUTH"
    assert after_login.selected_queue_ids==("q1","q2","q3")

    store.mark_drained(
        "q1",
        expected_item_digest=q1.digest,
        evidence_ref="rehearsal://q1/complete",
        evidence_digest=evidence("q1-complete"),
    )

    # Fresh-process equivalent: reopen durable SQLite state.
    recovered=SqliteProviderAuthStateStore(db)
    recovered_plan=recovered.plan_drain("vercel",max_items=3)
    assert recovered_plan.selected_queue_ids==("q2","q3")
    assert recovered.load_leases("vercel")[0].digest==browser.digest

    connector=recovered.observe(
        observation(
            "connector_api",
            "AUTH_SUCCESS",
            "2026-10-06T07:35:00Z",
        )
    )
    connector_decision=select_provider_auth_path(
        "vercel",
        recovered.load_leases("vercel"),
    )
    assert connector_decision.selected_surface=="connector_api"
    assert connector_decision.selected_lease_digest==connector.digest

    recovered.mark_drained(
        "q2",
        expected_item_digest=q2.digest,
        evidence_ref="rehearsal://q2/complete",
        evidence_digest=evidence("q2-complete"),
    )

    # Both supported auth surfaces are explicitly rejected/challenged.
    recovered.observe(
        observation(
            "cloud_browser",
            "AUTH_CHALLENGE",
            "2026-10-06T08:00:00Z",
        )
    )
    recovered.observe(
        observation(
            "connector_api",
            "AUTH_REJECTED",
            "2026-10-06T08:00:01Z",
        )
    )
    final_plan=recovered.plan_drain("vercel",max_items=3)
    assert final_plan.disposition=="HUMAN_REAUTH_REQUIRED"
    assert final_plan.queue_depth==1
    assert final_plan.selected_queue_ids==()

    report={
        "schema_version":"ge.persistent-auth-lease-rehearsal.v1",
        "status":"PASS_NOT_ACTIVATED",
        "provider":"vercel",
        "initial_human_gate_queue_depth":before.queue_depth,
        "one_login_unlocked_queue_ids":list(after_login.selected_queue_ids),
        "restart_recovered_queue_ids":list(recovered_plan.selected_queue_ids),
        "connector_preferred_after_available":connector_decision.selected_surface=="connector_api",
        "final_human_gate_queue_depth":final_plan.queue_depth,
        "credentials_persisted":False,
        "cookies_persisted":False,
        "tokens_persisted":False,
        "keepalive_attempted":False,
        "provider_expiry_bypassed":False,
        "authority_created":False,
        "execution_triggered":False,
        "browser_lease_digest":browser.digest,
        "connector_auth_decision":auth_path_to_dict(connector_decision),
        "final_plan_digest":final_plan.plan_digest,
    }
    (out/"report.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
