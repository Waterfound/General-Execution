#!/usr/bin/env python3
from __future__ import annotations

import json

from general_execution.execution_protocol import (
    CapabilityProjection,
    ExecutionMethodProfile,
    ExecutionProtocolRequest,
    ResourceCauseKind,
    ResourceObservation,
    decide_execution_protocol,
    decision_to_dict,
)
from general_execution.work_sparse_unattended import (
    ControllerUsage,
    ExecutorCapability,
    UnattendedAuthorityEnvelope,
)

PROJECTION = "p_03fc2c6548c8d191"
REGISTRY = "sha256:9f6956f251a9edf7a2de9aff79af5765aafc219c5eb55af4ce90ce1ae0b51cb1"
AUTHORITY_DIGEST = "sha256:be2b780e4bbeefb01f978c81b87328de6fb6642eb1a9f6fa464d59828127bf74"
PREDICATE = "predicate://opaque-001"


def main() -> int:
    candidates = (
        CapabilityProjection(
            candidate_id="c_c84ee03c107b3a1f",
            capability_ids=("k_a8e1fe6153d08df5",),
            projection_id=PROJECTION,
            registry_revision_digest=REGISTRY,
            authority_ref_digest=AUTHORITY_DIGEST,
            cost_rank=0,
            execution_capable=True,
        ),
        CapabilityProjection(
            candidate_id="c_b42d412ef5ff8624",
            capability_ids=("k_40211771465d71da",),
            projection_id=PROJECTION,
            registry_revision_digest=REGISTRY,
            authority_ref_digest=AUTHORITY_DIGEST,
            cost_rank=0,
            execution_capable=True,
        ),
        CapabilityProjection(
            candidate_id="c_4759960586eecaba",
            capability_ids=("k_268328fff13df53b",),
            projection_id=PROJECTION,
            registry_revision_digest=REGISTRY,
            authority_ref_digest=AUTHORITY_DIGEST,
            cost_rank=0,
            execution_capable=True,
        ),
    )

    request = ExecutionProtocolRequest(
        request_id="opaque-decision-001",
        objective="bounded private candidate with independent verification",
        evidence_predicate=PREDICATE,
        required_capability_ids=(
            "k_a8e1fe6153d08df5",
            "k_40211771465d71da",
            "k_268328fff13df53b",
        ),
        repository="opaque/private-target",
        authority_ref="authority://opaque/candidate",
        projection_id=PROJECTION,
        registry_revision_digest=REGISTRY,
        authority_ref_digest=AUTHORITY_DIGEST,
        required_executor_capabilities=("repo_read", "repo_write", "test_execution"),
        requested_actions=("candidate_write", "run_verification"),
        requires_observed_evidence=True,
        requires_state_change=True,
        advisory_allowed=False,
    )

    envelope = UnattendedAuthorityEnvelope(
        envelope_id="opaque-envelope-001",
        authority_ref="authority://opaque/candidate",
        allowed_repositories=("opaque/private-target",),
        allowed_actions=("candidate_write", "run_verification"),
        forbidden_actions=(
            "canonical_merge",
            "provider_mutation",
            "credential_mutation",
            "paid_spend",
            "runtime_activation",
        ),
        max_work_invocations=0,
        max_paid_spend_cents=0,
    )

    executor = ExecutorCapability(
        executor_id="connector-executor",
        capabilities=("repo_read", "repo_write", "test_execution"),
        cost_rank=0,
        available=True,
        evidence_ref="executor://connector/available",
    )
    resource = ResourceObservation(
        executor_id="connector-executor",
        available=True,
        cause_kind=ResourceCauseKind.NONE,
        cause_code="available",
        evidence_ref="resource://connector/available",
    )
    method = ExecutionMethodProfile(
        executor_id="connector-executor",
        evidence_predicates=(PREDICATE,),
        evidence_quality_rank=2,
    )

    decision = decide_execution_protocol(
        request=request,
        candidates=candidates,
        envelope=envelope,
        executors=(executor,),
        resource_observations=(resource,),
        method_profiles=(method,),
        usage=ControllerUsage(),
        minimum_evidence_quality_rank=2,
    )

    result = decision_to_dict(decision)
    assert result["invocation_mode"] == "COMPOSED_REAL_RUN"
    assert result["disposition"] == "READY_FOR_EXISTING_ADMISSION"
    assert result["selected_candidate_ids"] == [
        "c_4759960586eecaba",
        "c_b42d412ef5ff8624",
        "c_c84ee03c107b3a1f",
    ]
    assert result["selected_executor_id"] == "connector-executor"
    assert result["evidence_predicate_preserved"] is True
    assert result["authority_created"] is False
    assert result["execution_triggered"] is False
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
