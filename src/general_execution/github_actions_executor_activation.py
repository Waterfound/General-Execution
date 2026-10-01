from __future__ import annotations

import os
from typing import Mapping

from .canonical import sha256_digest
from .executor_activation import (
    ExecutorActivationCapability,
    ExecutorActivationIntent,
    NativeActivationObservation,
)

ADAPTER_ID = "general-execution/github-actions-production"
ADAPTER_VERSION = "1"


def github_actions_executor_capability(
    repository: str,
    *,
    available: bool = True,
) -> ExecutorActivationCapability:
    evidence = {
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "executor": "github_actions",
        "repository": repository,
        "idempotency_key": "dispatch_identity",
        "authority_created": False,
        "available": available,
    }
    return ExecutorActivationCapability(
        executor="github_actions",
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        evidence_ref=f"github-actions://{repository}/eac01-production-adapter",
        evidence_digest=sha256_digest(evidence),
        available=available,
    )


class GitHubActionsExecutorActivationAdapter:
    """Production EAC-01 adapter for a real GitHub Actions run lineage.

    A workflow run is the native execution lineage. GitHub job re-runs keep the
    same run id, so replay of one dispatch_identity reconciles to the same
    native_execution_ref rather than manufacturing a second native launch.
    """

    def __init__(
        self,
        capability: ExecutorActivationCapability,
        *,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.capability = capability
        self._env = dict(os.environ if env is None else env)
        self.calls = 0

    def activate(
        self,
        intent: ExecutorActivationIntent,
    ) -> NativeActivationObservation:
        self.calls += 1

        if self.capability.executor != "github_actions":
            return self._failed(intent, "unsupported_executor")
        if self._env.get("GITHUB_ACTIONS") != "true":
            return NativeActivationObservation(
                activation_id=intent.activation_id,
                dispatch_identity=intent.dispatch_identity,
                executor=intent.executor,
                outcome="CONDITION_WAIT",
                condition_ref="github-actions://runner/available",
                evidence_ref=self.capability.evidence_ref,
                evidence_digest=self.capability.evidence_digest,
            )

        repository = self._env.get("GITHUB_REPOSITORY", "")
        if repository != intent.repository:
            return self._failed(intent, "repository_mismatch")

        run_id = self._env.get("GITHUB_RUN_ID", "")
        github_sha = self._env.get("GITHUB_SHA", "")
        if not run_id or not run_id.isdigit():
            return self._failed(intent, "github_run_id_missing")
        if (
            len(github_sha) != 40
            or any(ch not in "0123456789abcdef" for ch in github_sha.lower())
        ):
            return self._failed(intent, "github_sha_invalid")

        native_ref = f"github-actions://{repository}/actions/runs/{run_id}"
        evidence = {
            "adapter_id": self.capability.adapter_id,
            "adapter_version": self.capability.adapter_version,
            "dispatch_identity": intent.dispatch_identity,
            "repository": repository,
            "run_id": run_id,
            "github_sha": github_sha.lower(),
            "native_execution_ref": native_ref,
            "authority_created": False,
        }
        return NativeActivationObservation(
            activation_id=intent.activation_id,
            dispatch_identity=intent.dispatch_identity,
            executor=intent.executor,
            outcome="EXECUTOR_ACCEPTED",
            native_execution_ref=native_ref,
            evidence_ref=native_ref + "#eac01",
            evidence_digest=sha256_digest(evidence),
        )

    def _failed(
        self,
        intent: ExecutorActivationIntent,
        reason: str,
    ) -> NativeActivationObservation:
        evidence = {
            "adapter_id": self.capability.adapter_id,
            "dispatch_identity": intent.dispatch_identity,
            "reason": reason,
            "authority_created": False,
        }
        return NativeActivationObservation(
            activation_id=intent.activation_id,
            dispatch_identity=intent.dispatch_identity,
            executor=intent.executor,
            outcome="FAILED_ACTIVATION",
            failure_reason=reason,
            evidence_ref=self.capability.evidence_ref,
            evidence_digest=sha256_digest(evidence),
        )
