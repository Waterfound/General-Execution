from __future__ import annotations

from general_execution.execution_launch_admission import (
    ExecutionLaunchOrder,
    LaunchAuthorityBinding,
    LaunchExecutorBinding,
    admit_or_replay_execution_launch,
)
from general_execution.canonical import sha256_digest
from general_execution.executor_activation import (
    SqliteExecutorActivationStore,
    activate_or_reconcile_executor,
    begin_activation,
    prepare_executor_activation,
)
from general_execution.github_actions_executor_activation import (
    GitHubActionsExecutorActivationAdapter,
    github_actions_executor_capability,
)


def _receipt():
    authority = LaunchAuthorityBinding(
        actor="Waterfound",
        authority_ref="authority://waterfound/eac01-production-executor-adapter-2026-10-01",
        authority_boundary="Bounded EAC-01 production executor adapter candidate only.",
        granted_scopes=("candidate_write", "executor_activation"),
    )
    launch_executor = LaunchExecutorBinding(
        executor="github_actions",
        availability="AVAILABLE",
        evidence_ref="adapter://general-execution/github-actions-production-v1",
        evidence_digest=sha256_digest(
            {
                "adapter": "general-execution/github-actions-production-v1",
                "executor": "github_actions",
                "idempotency_key": "dispatch_identity",
                "authority_created": False,
            }
        ),
    )
    order = ExecutionLaunchOrder(
        workstream_id="eac01-production-github-actions-001",
        owner="general_execution",
        repository="Waterfound/General-Execution",
        executor="github_actions",
        objective="Prove production EAC-01 activation on a real GitHub Actions lineage.",
        order_ref="order://eac01-production-github-actions-001",
        source_revision=None,
        required_authority_scopes=("candidate_write", "executor_activation"),
        authority=authority,
        executor_binding=launch_executor,
    )
    return admit_or_replay_execution_launch(
        order,
        authenticated_order_digest=order.digest,
        authenticated_actor="Waterfound",
    ).receipt


def _env(run_id="36830000001", repository="Waterfound/General-Execution"):
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": repository,
        "GITHUB_RUN_ID": run_id,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "1" * 40,
    }


def test_real_adapter_binds_native_run_and_is_terminal_replay_safe(tmp_path):
    receipt = _receipt()
    capability = github_actions_executor_capability(receipt.repository)
    adapter = GitHubActionsExecutorActivationAdapter(capability, env=_env())
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    first = activate_or_reconcile_executor(store, receipt, capability, adapter)
    second = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert first.state.status == "executor_accepted"
    assert first.state.native_execution_ref == (
        "github-actions://Waterfound/General-Execution/actions/runs/36830000001"
    )
    assert second.state == first.state
    assert second.replay_status == "ALREADY_RECORDED"
    assert adapter.calls == 1
    assert first.state.authority_created is False


def test_crash_after_native_side_effect_reconciles_same_real_run_lineage(tmp_path):
    receipt = _receipt()
    capability = github_actions_executor_capability(receipt.repository)
    adapter = GitHubActionsExecutorActivationAdapter(capability, env=_env())
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    intent = prepare_executor_activation(receipt, capability)
    prepared = store.initialize(intent)
    store.compare_and_swap(prepared, begin_activation(prepared))

    lost = adapter.activate(intent)
    recovered = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert lost.native_execution_ref == recovered.state.native_execution_ref
    assert adapter.calls == 2
    assert recovered.replay_status == "RECOVERED"
    assert recovered.state.authority_created is False


def test_job_rerun_attempt_keeps_same_native_execution_ref():
    receipt = _receipt()
    capability = github_actions_executor_capability(receipt.repository)
    intent = prepare_executor_activation(receipt, capability)

    first = GitHubActionsExecutorActivationAdapter(
        capability,
        env={**_env(), "GITHUB_RUN_ATTEMPT": "1"},
    ).activate(intent)
    second = GitHubActionsExecutorActivationAdapter(
        capability,
        env={**_env(), "GITHUB_RUN_ATTEMPT": "2"},
    ).activate(intent)

    assert first.native_execution_ref == second.native_execution_ref
    assert first.evidence_digest == second.evidence_digest
    assert first.dispatch_identity == second.dispatch_identity


def test_runner_absence_is_explicit_condition_wait(tmp_path):
    receipt = _receipt()
    capability = github_actions_executor_capability(receipt.repository)
    adapter = GitHubActionsExecutorActivationAdapter(capability, env={})
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    result = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert result.state.status == "condition_wait"
    assert result.state.condition_ref == "github-actions://runner/available"
    assert result.state.authority_created is False


def test_repository_mismatch_is_explicit_failed_activation(tmp_path):
    receipt = _receipt()
    capability = github_actions_executor_capability(receipt.repository)
    adapter = GitHubActionsExecutorActivationAdapter(
        capability,
        env=_env(repository="Waterfound/Another-Repository"),
    )
    store = SqliteExecutorActivationStore(tmp_path / "activation.sqlite")

    result = activate_or_reconcile_executor(store, receipt, capability, adapter)

    assert result.state.status == "failed_activation"
    assert result.state.failure_reason == "repository_mismatch"
    assert result.state.authority_created is False
