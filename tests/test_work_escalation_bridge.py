from __future__ import annotations

from dataclasses import replace

import pytest

from general_execution.canonical import sha256_digest
from general_execution.execution_launch_admission import admit_or_replay_execution_launch
from general_execution.executor_activation import (
    SqliteExecutorActivationStore,
    activate_or_reconcile_executor,
)
from general_execution.work_escalation_bridge import (
    ExternalWorkExecutorActivationAdapter,
    SqliteWorkEscalationStore,
    WorkEscalationBudgetExhausted,
    WorkEscalationError,
    WorkInvocationAuthority,
    WorkPlatformObservation,
    build_work_launch_order,
    prepare_work_escalation_request,
    prepare_work_platform_activation_request,
    record_work_platform_observation,
    work_executor_capability,
)
from general_execution.work_sparse_unattended import (
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
    UnattendedWorkItem,
    decide_work_sparse_route,
)


AUTH_REF = "authority://waterfound/work-escalation-test"


def envelope(max_work=2):
    return UnattendedAuthorityEnvelope(
        envelope_id="work-escalation-test",
        authority_ref=AUTH_REF,
        allowed_repositories=("Waterfound/General-Execution",),
        allowed_actions=("read_state", "run_tests"),
        forbidden_actions=("merge_main", "release", "paid_spend"),
        max_work_invocations=max_work,
        max_paid_spend_cents=0,
    )


def authority(max_work=2):
    return WorkInvocationAuthority(
        actor="Waterfound",
        authority_ref=AUTH_REF,
        authority_boundary="Bounded Work invocation candidate only.",
        granted_scopes=("executor_activation", "work_invocation"),
        max_invocations=max_work,
    )


def work(work_id="work-1", objective="Perform Work-only browser task"):
    return UnattendedWorkItem(
        work_id=work_id,
        objective=objective,
        repository="Waterfound/General-Execution",
        source_revision="a" * 40,
        authority_ref=AUTH_REF,
        required_capabilities=("browser_ui",),
        requested_actions=("read_state",),
    )


def work_route(item=None, env=None, usage=None):
    item = item or work()
    env = env or envelope()
    usage = usage or ControllerUsage()
    decision = decide_work_sparse_route(
        env,
        item,
        (
            ExecutorCapability(
                executor_id="work",
                capabilities=("browser_ui", "cloud_computer"),
                cost_rank=100,
                requires_work=True,
                evidence_ref="chatgpt-work://capability",
            ),
        ),
        usage,
    )
    assert decision.disposition == "DISPATCH"
    assert decision.selected_executor_id == "work"
    assert decision.work_required
    return item, env, decision


def prepared_request(work_id="work-1", max_work=2):
    item, env, decision = work_route(
        item=work(work_id=work_id),
        env=envelope(max_work=max_work),
    )
    auth = authority(max_work=max_work)
    request = prepare_work_escalation_request(env, item, decision, auth)
    return item, env, decision, auth, request


def admitted_receipt(request, auth, capability=None):
    capability = capability or work_executor_capability()
    order = build_work_launch_order(request, auth, capability)
    receipt = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor="Waterfound",
    ).receipt
    assert receipt.disposition == "ADMITTED"
    assert receipt.executor == "work"
    return capability, order, receipt


def accepted_observation(platform_request, *, native_ref="chatgpt-work://tasks/work-123"):
    return WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="PLATFORM_ACCEPTED",
        observed_at="2026-10-06T16:45:00Z",
        evidence_ref=native_ref + "#receipt",
        evidence_digest=sha256_digest(
            {
                "platform_request_id": platform_request.platform_request_id,
                "native_execution_ref": native_ref,
            }
        ),
        native_execution_ref=native_ref,
    )


def test_work_sparse_selection_requires_explicit_positive_budget():
    item = work()
    env = envelope(max_work=0)
    decision = decide_work_sparse_route(
        env,
        item,
        (
            ExecutorCapability(
                executor_id="work",
                capabilities=("browser_ui",),
                cost_rank=1,
                requires_work=True,
                evidence_ref="chatgpt-work://capability",
            ),
        ),
        ControllerUsage(),
    )
    assert decision.disposition == "CONDITION_WAIT"
    assert decision.selected_executor_id is None
    assert any("work_budget_exhausted" in reason for reason in decision.reasons)


def test_bridge_binds_exact_work_sparse_selection_and_authority():
    item, env, decision, auth, request = prepared_request()
    assert request.work_item_digest == item.digest
    assert request.envelope_digest == env.digest
    assert request.routing_decision_digest == decision.decision_digest
    assert request.authority_ref == AUTH_REF
    assert request.authority_digest == auth.digest
    assert request.max_work_invocations == 2
    assert request.execution_triggered is False
    assert request.authority_created is False


def test_bridge_rejects_non_work_route():
    item = UnattendedWorkItem(
        work_id="api-work",
        objective="Use API executor",
        repository="Waterfound/General-Execution",
        source_revision="b" * 40,
        authority_ref=AUTH_REF,
        required_capabilities=("repo_read",),
        requested_actions=("read_state",),
    )
    env = envelope()
    decision = decide_work_sparse_route(
        env,
        item,
        (
            ExecutorCapability(
                executor_id="github_actions",
                capabilities=("repo_read",),
                cost_rank=1,
                evidence_ref="github-actions://capability",
            ),
        ),
    )
    with pytest.raises(WorkEscalationError, match="did not select Work"):
        prepare_work_escalation_request(env, item, decision, authority())


def test_bridge_rejects_authority_substitution():
    item, env, decision = work_route()
    wrong = WorkInvocationAuthority(
        actor="Waterfound",
        authority_ref="authority://other",
        authority_boundary="Other authority.",
        granted_scopes=("executor_activation", "work_invocation"),
        max_invocations=2,
    )
    with pytest.raises(WorkEscalationError, match="authority reference mismatch"):
        prepare_work_escalation_request(env, item, decision, wrong)


def test_authority_requires_explicit_work_invocation_scope():
    with pytest.raises(WorkEscalationError, match="requires executor_activation and work_invocation"):
        WorkInvocationAuthority(
            actor="Waterfound",
            authority_ref=AUTH_REF,
            authority_boundary="Incomplete authority.",
            granted_scopes=("executor_activation",),
            max_invocations=1,
        )


def test_durable_budget_reservation_is_idempotent_and_bounded(tmp_path):
    store = SqliteWorkEscalationStore(tmp_path / "work.sqlite")
    *_, first = prepared_request("work-1", max_work=2)
    *_, second = prepared_request("work-2", max_work=2)
    *_, third = prepared_request("work-3", max_work=2)

    first_state = store.reserve(first)
    replay = store.reserve(first)
    second_state = store.reserve(second)

    assert replay == first_state
    assert first_state.slot_index == 1
    assert second_state.slot_index == 2
    with pytest.raises(WorkEscalationBudgetExhausted):
        store.reserve(third)


def test_restart_recovers_same_reserved_slot_without_duplicate_budget(tmp_path):
    path = tmp_path / "work.sqlite"
    *_, request = prepared_request()
    first = SqliteWorkEscalationStore(path).reserve(request)
    recovered = SqliteWorkEscalationStore(path).reserve(request)
    assert recovered == first
    assert recovered.slot_index == 1
    assert recovered.reservation_digest == first.reservation_digest


def test_launch_order_consumes_existing_authority_but_does_not_create_it():
    *_, auth, request = prepared_request()
    capability, order, receipt = admitted_receipt(request, auth)

    assert order.authority is not None
    assert order.authority.authority_ref == auth.authority_ref
    assert order.authority.granted_scopes == auth.granted_scopes
    assert order.executor == "work"
    assert receipt.authority_created is False
    assert receipt.execution_triggered is False
    assert capability.authority_created is False


def test_platform_request_exists_before_any_native_work_execution(tmp_path):
    *_, auth, request = prepared_request()
    capability, _, receipt = admitted_receipt(request, auth)
    state = SqliteWorkEscalationStore(tmp_path / "work.sqlite").reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)

    assert platform_request.dispatch_identity == receipt.dispatch_identity
    assert platform_request.reservation_digest == state.reservation_digest
    assert platform_request.execution_triggered is False
    assert platform_request.authority_created is False
    assert state.status == "reserved"
    assert state.native_execution_ref is None
    assert capability.executor == "work"


def test_platform_wait_does_not_claim_execution_and_can_later_progress(tmp_path):
    *_, auth, request = prepared_request()
    _, _, receipt = admitted_receipt(request, auth)
    store = SqliteWorkEscalationStore(tmp_path / "work.sqlite")
    state = store.reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)

    waiting = WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="PLATFORM_WAIT",
        observed_at="2026-10-06T16:40:00Z",
        evidence_ref="chatgpt-work://activation/availability",
        evidence_digest=sha256_digest({"status": "wait"}),
        condition_ref="chatgpt-work://activation-adapter/available",
    )
    wait_state = store.compare_and_swap(
        state,
        record_work_platform_observation(state, platform_request, waiting),
    )
    assert wait_state.status == "platform_wait"
    assert wait_state.native_execution_ref is None

    accepted = accepted_observation(platform_request)
    accepted_state = store.compare_and_swap(
        wait_state,
        record_work_platform_observation(wait_state, platform_request, accepted),
    )
    assert accepted_state.status == "platform_accepted"
    assert accepted_state.native_execution_ref == "chatgpt-work://tasks/work-123"


def test_human_reauth_gate_uses_provider_action_ref_and_preserves_queue_lineage(tmp_path):
    *_, auth, request = prepared_request()
    _, _, receipt = admitted_receipt(request, auth)
    store = SqliteWorkEscalationStore(tmp_path / "work.sqlite")
    state = store.reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)

    reauth = WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="HUMAN_REAUTH_REQUIRED",
        observed_at="2026-10-06T16:41:00Z",
        evidence_ref="provider://vercel/auth-challenge",
        evidence_digest=sha256_digest({"provider": "vercel", "challenge": True}),
        condition_ref="auth://vercel/reauthenticate",
    )
    gated = store.compare_and_swap(
        state,
        record_work_platform_observation(state, platform_request, reauth),
    )
    assert gated.status == "human_reauth_required"
    assert gated.condition_ref == "auth://vercel/reauthenticate"
    assert gated.request == request
    assert gated.native_execution_ref is None

    accepted = accepted_observation(
        platform_request,
        native_ref="chatgpt-work://tasks/after-reauth",
    )
    resumed = store.compare_and_swap(
        gated,
        record_work_platform_observation(gated, platform_request, accepted),
    )
    assert resumed.status == "platform_accepted"
    assert resumed.native_execution_ref == "chatgpt-work://tasks/after-reauth"


@pytest.mark.parametrize(
    "secret_field",
    ["credentials_persisted", "cookies_persisted", "tokens_persisted"],
)
def test_platform_observation_refuses_secret_persistence(secret_field, tmp_path):
    *_, auth, request = prepared_request()
    _, _, receipt = admitted_receipt(request, auth)
    state = SqliteWorkEscalationStore(tmp_path / "work.sqlite").reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)
    values = dict(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="PLATFORM_WAIT",
        observed_at="2026-10-06T16:42:00Z",
        evidence_ref="chatgpt-work://wait",
        evidence_digest=sha256_digest({"wait": True}),
        condition_ref="chatgpt-work://activation-adapter/available",
    )
    values[secret_field] = True
    with pytest.raises(WorkEscalationError, match="cannot persist auth secrets"):
        WorkPlatformObservation(**values)


def test_platform_observation_rejects_request_substitution(tmp_path):
    *_, auth, request = prepared_request()
    _, _, receipt = admitted_receipt(request, auth)
    state = SqliteWorkEscalationStore(tmp_path / "work.sqlite").reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)
    accepted = accepted_observation(platform_request)
    tampered = replace(accepted, platform_request_id="gewp-tampered")
    with pytest.raises(WorkEscalationError, match="request identity mismatch"):
        record_work_platform_observation(state, platform_request, tampered)


def test_accepted_platform_observation_binds_into_existing_eac01_lineage(tmp_path):
    *_, auth, request = prepared_request()
    capability, _, receipt = admitted_receipt(request, auth)
    bridge_store = SqliteWorkEscalationStore(tmp_path / "work.sqlite")
    state = bridge_store.reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)
    accepted = accepted_observation(platform_request)

    accepted_state = bridge_store.compare_and_swap(
        state,
        record_work_platform_observation(state, platform_request, accepted),
    )
    assert accepted_state.status == "platform_accepted"

    adapter = ExternalWorkExecutorActivationAdapter(
        capability,
        platform_request,
        accepted,
    )
    eac_store = SqliteExecutorActivationStore(tmp_path / "eac.sqlite")
    first = activate_or_reconcile_executor(eac_store, receipt, capability, adapter)
    second = activate_or_reconcile_executor(eac_store, receipt, capability, adapter)

    assert first.state.status == "executor_accepted"
    assert first.state.native_execution_ref == "chatgpt-work://tasks/work-123"
    assert second.state == first.state
    assert second.replay_status == "ALREADY_RECORDED"
    assert adapter.calls == 1
    assert first.state.authority_created is False


def test_wait_or_reauth_observation_is_not_misrepresented_as_eac_execution(tmp_path):
    *_, auth, request = prepared_request()
    capability, _, receipt = admitted_receipt(request, auth)
    state = SqliteWorkEscalationStore(tmp_path / "work.sqlite").reserve(request)
    platform_request = prepare_work_platform_activation_request(state, receipt)
    waiting = WorkPlatformObservation(
        platform_request_id=platform_request.platform_request_id,
        platform_request_digest=platform_request.digest,
        dispatch_identity=platform_request.dispatch_identity,
        outcome="PLATFORM_WAIT",
        observed_at="2026-10-06T16:43:00Z",
        evidence_ref="chatgpt-work://wait",
        evidence_digest=sha256_digest({"wait": True}),
        condition_ref="chatgpt-work://activation-adapter/available",
    )
    adapter = ExternalWorkExecutorActivationAdapter(
        capability,
        platform_request,
        waiting,
    )
    with pytest.raises(WorkEscalationError, match="remain in the bridge"):
        adapter.activate(
            __import__(
                "general_execution.executor_activation",
                fromlist=["prepare_executor_activation"],
            ).prepare_executor_activation(receipt, capability)
        )


def test_unavailable_work_activation_capability_fails_before_platform_request(tmp_path):
    *_, auth, request = prepared_request()
    capability = work_executor_capability(available=False)
    order = build_work_launch_order(request, auth, capability)
    receipt = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor="Waterfound",
    ).receipt
    assert receipt.disposition == "FAILED_BEFORE_LAUNCH"
    state = SqliteWorkEscalationStore(tmp_path / "work.sqlite").reserve(request)
    with pytest.raises(WorkEscalationError, match="requires ADMITTED"):
        prepare_work_platform_activation_request(state, receipt)
