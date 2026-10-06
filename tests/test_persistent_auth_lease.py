import copy

import pytest

from general_execution.canonical import sha256_digest
from general_execution.persistent_auth_lease import (
    ProviderAuthObservation,
    ProviderAuthQueueItem,
    PersistentAuthLeaseError,
    SqliteProviderAuthStateStore,
    apply_auth_observation,
    auth_path_to_dict,
    drain_plan_to_dict,
    auth_handoff_to_dict,
    initialize_auth_lease,
    plan_provider_drain,
    prepare_provider_queue_handoff,
    select_provider_auth_path,
    verify_auth_path_decision,
    verify_provider_drain_plan,
    verify_provider_queue_handoff,
)


def digest(label):
    return sha256_digest({"evidence": label})


def observation(
    provider="vercel",
    surface="cloud_browser",
    outcome="AUTH_SUCCESS",
    when="2026-10-06T07:00:00Z",
    *,
    human=False,
):
    return ProviderAuthObservation(
        provider_id=provider,
        surface=surface,
        outcome=outcome,
        observed_at=when,
        evidence_ref=f"evidence://{provider}/{surface}/{outcome.lower()}",
        evidence_digest=digest(f"{provider}-{surface}-{outcome}-{when}"),
        human_interaction=human,
    )


def queue_item(
    queue_id,
    *,
    provider="vercel",
    priority=100,
    work_id=None,
):
    return ProviderAuthQueueItem(
        queue_id=queue_id,
        provider_id=provider,
        work_id=work_id or queue_id,
        repository="Waterfound/FAE-testnet",
        authority_ref="authority://waterfound/work-sparse-unattended-001",
        source_revision="candidate-sha",
        requested_actions=("read_state",),
        required_capabilities=("browser_ui",),
        priority=priority,
    )


def test_success_creates_non_secret_available_lease():
    lease = initialize_auth_lease(observation())
    assert lease.state == "AUTH_AVAILABLE"
    assert lease.generation == 0
    assert not lease.credentials_persisted
    assert not lease.cookies_persisted
    assert not lease.tokens_persisted
    assert not lease.authority_created


@pytest.mark.parametrize(
    "field",
    ["credentials_persisted", "cookies_persisted", "tokens_persisted"],
)
def test_auth_observation_refuses_secret_persistence(field):
    values = dict(
        provider_id="vercel",
        surface="cloud_browser",
        outcome="AUTH_SUCCESS",
        observed_at="2026-10-06T07:00:00Z",
        evidence_ref="evidence://auth",
        evidence_digest=digest("auth"),
    )
    values[field] = True
    with pytest.raises(PersistentAuthLeaseError):
        ProviderAuthObservation(**values)


def test_rejection_requires_human_then_new_success_reuses_same_lease_lineage():
    first = initialize_auth_lease(observation())
    rejected = apply_auth_observation(
        first,
        observation(
            outcome="AUTH_CHALLENGE",
            when="2026-10-06T08:00:00Z",
        ),
    )
    assert rejected.state == "HUMAN_REAUTH_REQUIRED"
    decision = select_provider_auth_path("vercel", (rejected,))
    assert decision.disposition == "HUMAN_REAUTH_REQUIRED"
    assert decision.human_interaction_required
    assert decision.human_action_ref == "auth://vercel/reauthenticate"

    recovered = apply_auth_observation(
        rejected,
        observation(
            outcome="AUTH_SUCCESS",
            when="2026-10-06T08:05:00Z",
            human=True,
        ),
    )
    assert recovered.state == "AUTH_AVAILABLE"
    assert recovered.generation == 2
    assert recovered.previous_lease_digest == rejected.digest


def test_stale_evidence_probes_before_requesting_human_reauth():
    lease = initialize_auth_lease(observation())
    decision = select_provider_auth_path(
        "vercel",
        (lease,),
        now="2026-10-06T09:00:00Z",
        evidence_stale_after_seconds=3600,
    )
    assert decision.disposition == "PROBE_AUTH"
    assert decision.selected_surface == "cloud_browser"
    assert not decision.human_interaction_required
    assert "probe_before_human_reauthentication" in decision.reasons


def test_connector_api_is_preferred_over_authenticated_browser():
    browser = initialize_auth_lease(observation(surface="cloud_browser"))
    connector = initialize_auth_lease(observation(surface="connector_api"))
    decision = select_provider_auth_path("vercel", (browser, connector))
    assert decision.disposition == "USE_AUTH"
    assert decision.selected_surface == "connector_api"
    assert decision.selected_lease_digest == connector.digest
    assert "connector_first" in decision.reasons


def test_existing_browser_session_is_reused_when_no_connector_is_available():
    browser = initialize_auth_lease(observation(surface="cloud_browser"))
    decision = select_provider_auth_path("vercel", (browser,))
    assert decision.disposition == "USE_AUTH"
    assert decision.selected_surface == "cloud_browser"
    assert "reuse_existing_browser_session" in decision.reasons


def test_no_auth_evidence_consolidates_to_one_human_gate_for_provider_queue():
    items = (
        queue_item("q3", priority=30),
        queue_item("q1", priority=10),
        queue_item("q2", priority=20),
    )
    plan = plan_provider_drain("vercel", (), items, max_items=3)
    assert plan.disposition == "HUMAN_REAUTH_REQUIRED"
    assert plan.queue_depth == 3
    assert plan.selected_queue_ids == ()
    assert plan.human_interaction_required
    assert plan.human_action_ref == "auth://vercel/reauthenticate"


def test_one_human_login_unlocks_ordered_batch_drain():
    items = (
        queue_item("q3", priority=30),
        queue_item("q1", priority=10),
        queue_item("q2", priority=20),
    )
    lease = initialize_auth_lease(
        observation(
            outcome="AUTH_SUCCESS",
            when="2026-10-06T08:05:00Z",
            human=True,
        )
    )
    plan = plan_provider_drain("vercel", (lease,), items, max_items=3)
    assert plan.disposition == "USE_AUTH"
    assert plan.queue_depth == 3
    assert plan.selected_queue_ids == ("q1", "q2", "q3")
    assert not plan.human_interaction_required
    assert not plan.execution_triggered
    assert not plan.authority_created


def test_batch_size_is_bounded_without_losing_queue_depth():
    items = (
        queue_item("q1", priority=10),
        queue_item("q2", priority=20),
        queue_item("q3", priority=30),
    )
    lease = initialize_auth_lease(observation())
    plan = plan_provider_drain("vercel", (lease,), items, max_items=1)
    assert plan.queue_depth == 3
    assert plan.selected_queue_ids == ("q1",)


def test_auth_path_replay_detects_surface_substitution():
    browser = initialize_auth_lease(observation(surface="cloud_browser"))
    connector = initialize_auth_lease(observation(surface="connector_api"))
    leases = (browser, connector)
    decision = auth_path_to_dict(select_provider_auth_path("vercel", leases))
    assert verify_auth_path_decision("vercel", leases, decision)

    tampered = copy.deepcopy(decision)
    tampered["selected_surface"] = "cloud_browser"
    assert not verify_auth_path_decision("vercel", leases, tampered)


def test_drain_replay_detects_queue_substitution():
    lease = initialize_auth_lease(observation())
    items = (queue_item("q1", priority=10), queue_item("q2", priority=20))
    plan = drain_plan_to_dict(
        plan_provider_drain("vercel", (lease,), items, max_items=2)
    )
    assert verify_provider_drain_plan(
        "vercel", (lease,), items, plan, max_items=2
    )

    tampered = copy.deepcopy(plan)
    tampered["selected_queue_ids"] = ["q2", "q1"]
    assert not verify_provider_drain_plan(
        "vercel", (lease,), items, tampered, max_items=2
    )


def test_durable_store_recovers_auth_and_queue_after_restart(tmp_path):
    path = tmp_path / "auth.db"
    store = SqliteProviderAuthStateStore(path)
    lease = store.observe(observation())
    q1 = queue_item("q1", priority=20)
    q2 = queue_item("q2", priority=10)
    store.enqueue(q1)
    store.enqueue(q2)

    recovered = SqliteProviderAuthStateStore(path)
    assert recovered.load_leases("vercel") == (lease,)
    assert recovered.queued("vercel") == (q2, q1)
    plan = recovered.plan_drain("vercel", max_items=2)
    assert plan.selected_queue_ids == ("q2", "q1")


def test_durable_store_rejection_survives_restart_and_does_not_drop_queue(tmp_path):
    path = tmp_path / "auth.db"
    store = SqliteProviderAuthStateStore(path)
    store.observe(observation())
    store.enqueue(queue_item("q1"))
    rejected = store.observe(
        observation(
            outcome="AUTH_REJECTED",
            when="2026-10-06T08:00:00Z",
        )
    )
    assert rejected.state == "HUMAN_REAUTH_REQUIRED"

    recovered = SqliteProviderAuthStateStore(path)
    plan = recovered.plan_drain("vercel")
    assert plan.disposition == "HUMAN_REAUTH_REQUIRED"
    assert plan.queue_depth == 1
    assert plan.selected_queue_ids == ()


def test_mark_drained_is_idempotent_and_restart_safe(tmp_path):
    path = tmp_path / "auth.db"
    store = SqliteProviderAuthStateStore(path)
    store.observe(observation())
    item = queue_item("q1")
    store.enqueue(item)

    drained = store.mark_drained(
        "q1",
        expected_item_digest=item.digest,
        evidence_ref="evidence://q1/complete",
        evidence_digest=digest("q1-complete"),
    )
    replay = store.mark_drained(
        "q1",
        expected_item_digest=item.digest,
        evidence_ref="evidence://q1/complete",
        evidence_digest=digest("q1-complete"),
    )
    assert replay == drained

    recovered = SqliteProviderAuthStateStore(path)
    assert recovered.queued("vercel") == ()


def test_queue_id_cannot_be_rebound_to_another_work_item(tmp_path):
    store = SqliteProviderAuthStateStore(tmp_path / "auth.db")
    store.enqueue(queue_item("q1", work_id="work-a"))
    with pytest.raises(PersistentAuthLeaseError):
        store.enqueue(queue_item("q1", work_id="work-b"))


def test_older_observation_cannot_overwrite_newer_auth_state():
    current = initialize_auth_lease(
        observation(when="2026-10-06T09:00:00Z")
    )
    with pytest.raises(PersistentAuthLeaseError):
        apply_auth_observation(
            current,
            observation(
                outcome="AUTH_REJECTED",
                when="2026-10-06T08:59:59Z",
            ),
        )


def test_human_gate_requires_explicit_provider_rejection_not_age_alone():
    lease = initialize_auth_lease(observation())
    decision = select_provider_auth_path(
        "vercel",
        (lease,),
        now="2026-10-07T07:00:00Z",
        evidence_stale_after_seconds=60,
    )
    assert decision.disposition == "PROBE_AUTH"
    assert not decision.human_interaction_required


def test_auth_approved_queue_handoff_binds_exact_work_sparse_item():
    lease = initialize_auth_lease(observation())
    items = (
        queue_item("q1", priority=10),
        queue_item("q2", priority=20),
    )
    plan = plan_provider_drain("vercel", (lease,), items, max_items=2)
    handoff, work = prepare_provider_queue_handoff(plan, items, queue_id="q2")
    document = auth_handoff_to_dict(handoff)

    assert handoff.queue_id == "q2"
    assert handoff.queue_item_digest == items[1].digest
    assert handoff.work_item_digest == work.digest
    assert handoff.authority_ref == items[1].authority_ref
    assert work.work_id == items[1].work_id
    assert work.repository == items[1].repository
    assert work.requested_actions == items[1].requested_actions
    assert work.required_capabilities == items[1].required_capabilities
    assert not handoff.authority_created
    assert not handoff.execution_authorized
    assert verify_provider_queue_handoff(
        plan,
        items,
        document,
        queue_id="q2",
    )


def test_auth_queue_handoff_rejects_unselected_or_tampered_work():
    lease = initialize_auth_lease(observation())
    items = (
        queue_item("q1", priority=10),
        queue_item("q2", priority=20),
    )
    plan = plan_provider_drain("vercel", (lease,), items, max_items=1)
    with pytest.raises(PersistentAuthLeaseError):
        prepare_provider_queue_handoff(plan, items, queue_id="q2")

    handoff, _ = prepare_provider_queue_handoff(plan, items)
    tampered = auth_handoff_to_dict(handoff)
    tampered["authority_ref"] = "authority://invented"
    assert not verify_provider_queue_handoff(plan, items, tampered)


def test_human_gate_plan_cannot_be_handed_to_work_sparse():
    items = (queue_item("q1"),)
    plan = plan_provider_drain("vercel", (), items)
    assert plan.disposition == "HUMAN_REAUTH_REQUIRED"
    with pytest.raises(PersistentAuthLeaseError):
        prepare_provider_queue_handoff(plan, items)
