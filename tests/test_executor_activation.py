from __future__ import annotations

from dataclasses import replace

import pytest

from general_execution.canonical import sha256_digest
from general_execution.execution_launch_admission import (
    ExecutionLaunchOrder,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
    admit_or_replay_execution_launch,
)
from general_execution.executor_activation import (
    ExecutorActivationCapability,
    ExecutorActivationError,
    NativeActivationObservation,
    SqliteExecutorActivationStore,
    activate_or_reconcile_executor,
    begin_activation,
    prepare_executor_activation,
)


def _authority() -> LaunchAuthorityBinding:
    return LaunchAuthorityBinding(
        actor="Waterfound",
        authority_ref="authority://eac01/test",
        authority_boundary="candidate implementation only",
        granted_scopes=("candidate_write",),
    )


def _launch_executor() -> LaunchExecutorBinding:
    return LaunchExecutorBinding(
        executor="build_colony",
        availability="AVAILABLE",
        evidence_ref="executor://build_colony/capability",
        evidence_digest=sha256_digest({"executor": "build_colony", "available": True}),
    )


def _receipt(disposition: str = "ADMITTED"):
    order = ExecutionLaunchOrder(
        workstream_id="eac01-test",
        owner="general-execution",
        repository="Waterfound/General-Execution",
        executor="build_colony",
        objective="Exercise receipt-bound executor activation",
        order_ref="order://eac01-test",
        source_revision="f" * 40,
        required_authority_scopes=("candidate_write",),
        authority=_authority(),
        executor_binding=_launch_executor(),
    )
    admitted = admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor="Waterfound",
    ).receipt
    if disposition == "ADMITTED":
        return admitted
    if disposition == "HUMAN_GATE":
        missing = replace(order, authority=None)
        return admit_or_replay_execution_launch(
            missing,
            authenticated_order_digest=missing.digest,
            authenticated_actor="Waterfound",
        ).receipt
    if disposition == "FAILED_BEFORE_LAUNCH":
        unavailable = replace(
            order,
            executor_binding=LaunchExecutorBinding(
                executor="build_colony",
                availability="UNAVAILABLE",
                evidence_ref="executor://build_colony/unavailable",
                evidence_digest=sha256_digest(
                    {"executor": "build_colony", "available": False}
                ),
            ),
        )
        return admit_or_replay_execution_launch(
            unavailable,
            authenticated_order_digest=unavailable.digest,
            authenticated_actor="Waterfound",
        ).receipt
    raise AssertionError("unsupported test disposition")


def _capability(*, available: bool = True) -> ExecutorActivationCapability:
    return ExecutorActivationCapability(
        executor="build_colony",
        adapter_id="reference-build-colony-activation",
        adapter_version="1",
        evidence_ref="adapter://build-colony/eac01/reference",
        evidence_digest=sha256_digest(
            {"adapter": "reference-build-colony-activation", "available": available}
        ),
        available=available,
    )


class ReferenceAdapter:
    def __init__(self, capability: ExecutorActivationCapability):
        self.capability = capability
        self.calls = 0
        self.native_launches = 0
        self._runs: dict[str, str] = {}

    def activate(self, intent):
        self.calls += 1
        native_ref = self._runs.get(intent.dispatch_identity)
        if native_ref is None:
            native_ref = f"build-colony://run/{intent.dispatch_identity}"
            self._runs[intent.dispatch_identity] = native_ref
            self.native_launches += 1
        return NativeActivationObservation(
            activation_id=intent.activation_id,
            dispatch_identity=intent.dispatch_identity,
            executor=intent.executor,
            outcome="EXECUTOR_ACCEPTED",
            native_execution_ref=native_ref,
            evidence_ref=native_ref + "/receipt",
            evidence_digest=sha256_digest(
                {
                    "dispatch_identity": intent.dispatch_identity,
                    "native_execution_ref": native_ref,
                }
            ),
        )


def test_admitted_receipt_activates_exactly_one_native_execution(tmp_path):
    receipt = _receipt()
    capability = _capability()
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    result = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert result.state.status == "executor_accepted"
    assert result.state.native_execution_ref is not None
    assert result.replay_status == "CREATED"
    assert adapter.calls == 1
    assert adapter.native_launches == 1
    assert result.state.authority_created is False


def test_exact_replay_returns_existing_terminal_state_without_second_adapter_call(tmp_path):
    receipt = _receipt()
    capability = _capability()
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    first = activate_or_reconcile_executor(store, receipt, capability, adapter)
    second = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert second.state == first.state
    assert second.replay_status == "ALREADY_RECORDED"
    assert adapter.calls == 1
    assert adapter.native_launches == 1


def test_crash_before_native_call_recovers_same_dispatch_identity(tmp_path):
    receipt = _receipt()
    capability = _capability()
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")
    intent = prepare_executor_activation(receipt, capability)
    prepared = store.initialize(intent)
    store.compare_and_swap(prepared, begin_activation(prepared))

    recovered = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert recovered.replay_status == "RECOVERED"
    assert recovered.state.status == "executor_accepted"
    assert adapter.native_launches == 1


def test_crash_after_native_side_effect_replays_idempotently_without_duplicate_launch(tmp_path):
    receipt = _receipt()
    capability = _capability()
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")
    intent = prepare_executor_activation(receipt, capability)
    prepared = store.initialize(intent)
    unknown = store.compare_and_swap(prepared, begin_activation(prepared))

    lost_observation = adapter.activate(intent)
    assert lost_observation.native_execution_ref is not None
    assert unknown.status == "activation_unknown"
    assert adapter.native_launches == 1

    recovered = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert recovered.replay_status == "RECOVERED"
    assert recovered.state.native_execution_ref == lost_observation.native_execution_ref
    assert adapter.calls == 2
    assert adapter.native_launches == 1


@pytest.mark.parametrize("disposition", ["HUMAN_GATE", "FAILED_BEFORE_LAUNCH"])
def test_non_admitted_receipt_never_invokes_executor(tmp_path, disposition):
    receipt = _receipt(disposition)
    capability = _capability()
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    with pytest.raises(
        ExecutorActivationError,
        match="requires an ADMITTED launch receipt",
    ):
        activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert adapter.calls == 0
    assert adapter.native_launches == 0


def test_executor_unavailable_after_admission_persists_condition_wait_without_invocation(tmp_path):
    receipt = _receipt()
    capability = _capability(available=False)
    adapter = ReferenceAdapter(capability)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    result = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert result.state.status == "condition_wait"
    assert result.state.condition_ref == "executor://build_colony/available"
    assert adapter.calls == 0
    assert adapter.native_launches == 0


def test_capability_must_be_idempotent_by_dispatch_identity():
    with pytest.raises(
        ExecutorActivationError,
        match="idempotent by dispatch_identity",
    ):
        ExecutorActivationCapability(
            executor="build_colony",
            adapter_id="bad-adapter",
            adapter_version="1",
            evidence_ref="adapter://bad",
            evidence_digest=sha256_digest({"bad": True}),
            idempotency_key="random-request-id",
        )


def test_native_observation_cannot_create_authority():
    receipt = _receipt()
    capability = _capability()
    intent = prepare_executor_activation(receipt, capability)
    with pytest.raises(
        ExecutorActivationError,
        match="cannot create authority",
    ):
        NativeActivationObservation(
            activation_id=intent.activation_id,
            dispatch_identity=intent.dispatch_identity,
            executor=intent.executor,
            outcome="EXECUTOR_ACCEPTED",
            native_execution_ref="build-colony://run/1",
            evidence_ref="artifact://1",
            evidence_digest=sha256_digest({"artifact": 1}),
            authority_created=True,
        )


def test_adapter_capability_substitution_is_rejected_before_invocation(tmp_path):
    receipt = _receipt()
    capability = _capability()
    wrong = ExecutorActivationCapability(
        executor="build_colony",
        adapter_id="other-adapter",
        adapter_version="1",
        evidence_ref="adapter://other",
        evidence_digest=sha256_digest({"adapter": "other"}),
    )
    adapter = ReferenceAdapter(wrong)
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    with pytest.raises(
        ExecutorActivationError,
        match="adapter capability binding mismatch",
    ):
        activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert adapter.calls == 0
