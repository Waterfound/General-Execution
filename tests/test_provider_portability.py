import json

import pytest

from general_execution.provider_portability import (
    InternalLineageBinding,
    ProviderPortabilityError,
    ProviderResource,
    ProviderRoutingAuthority,
    ResourceDisposition,
    build_provider_task_envelope,
    provider_visible_dict,
    route_provider_task,
    verify_provider_binding,
)


def digest(char: str) -> str:
    return "sha256:" + char * 64


def lineage():
    return InternalLineageBinding(
        work_id="FAE-secret-frontier-name",
        portfolio_ref="portfolio://one-man-one-machine/internal",
        source_revision="branch/private-semantic-name@abc123",
        authority_ref="authority://waterfound/internal",
        required_capabilities=("reasoning", "verification"),
        input_artifact_digests=(digest("1"), digest("2")),
        output_contract_digest=digest("3"),
        semantic_context=("FAE", "Temporal Compression", "private objective"),
    )


def resource(resource_id, provider_id, disposition=ResourceDisposition.AVAILABLE):
    return ProviderResource(
        resource_id=resource_id,
        provider_id=provider_id,
        disposition=disposition,
        capabilities=("reasoning", "verification"),
        billing_scope_ref=f"tenant://{provider_id}/authorized",
        authority_ref="authority://resource/approved",
        admission_digest=digest("4"),
        evidence_refs=(f"evidence://{resource_id}",),
    )


def routing():
    return ProviderRoutingAuthority(
        authority_ref="authority://routing/approved",
        allowed_resource_ids=("a", "b"),
        allowed_capabilities=("reasoning", "verification"),
    )


def test_provider_visible_envelope_excludes_internal_semantics():
    internal = lineage()
    envelope, binding = build_provider_task_envelope(
        internal,
        resource("a", "provider-a"),
        dispatch_nonce="attempt-001",
        max_runtime_seconds=900,
    )
    payload = json.dumps(provider_visible_dict(envelope), sort_keys=True)
    for forbidden in (
        internal.work_id,
        internal.portfolio_ref,
        internal.source_revision,
        internal.authority_ref,
        *internal.semantic_context,
    ):
        assert forbidden not in payload
    assert "tenant://provider-a/authorized" in payload
    assert verify_provider_binding(internal, envelope, binding)


def test_dispatch_nonce_changes_external_task_ref_without_changing_internal_lineage():
    internal = lineage()
    res = resource("a", "provider-a")
    first, first_binding = build_provider_task_envelope(
        internal, res, dispatch_nonce="attempt-001", max_runtime_seconds=900
    )
    second, second_binding = build_provider_task_envelope(
        internal, res, dispatch_nonce="attempt-002", max_runtime_seconds=900
    )
    assert first.provider_task_ref != second.provider_task_ref
    assert first_binding.internal_lineage_digest == second_binding.internal_lineage_digest


def test_declined_resource_is_excluded_and_other_authorized_resource_is_selected():
    internal = lineage()
    decision = route_provider_task(
        internal,
        routing(),
        (
            resource("a", "provider-a", ResourceDisposition.DECLINED),
            resource("b", "provider-b", ResourceDisposition.AVAILABLE),
        ),
    )
    assert decision.selected_resource_id == "b"
    assert decision.selected_provider_id == "provider-b"
    rejected = {item.resource_id: item.reasons for item in decision.rejected}
    assert rejected["a"] == ("resource_declined",)
    assert decision.deferred is False
    assert decision.authority_created is False
    assert decision.execution_authorized is False


def test_all_resources_declined_or_unavailable_defer_without_circumvention():
    decision = route_provider_task(
        lineage(),
        routing(),
        (
            resource("a", "provider-a", ResourceDisposition.DECLINED),
            resource("b", "provider-b", ResourceDisposition.UNAVAILABLE),
        ),
    )
    assert decision.deferred is True
    assert decision.selected_resource_id is None
    assert decision.selected_provider_id is None
    reasons = {item.resource_id: item.reasons for item in decision.rejected}
    assert reasons["a"] == ("resource_declined",)
    assert reasons["b"] == ("resource_unavailable",)


def test_resource_outside_authority_cannot_be_used_as_fallback():
    decision = route_provider_task(
        lineage(),
        routing(),
        (
            resource("a", "provider-a", ResourceDisposition.DECLINED),
            resource("c", "provider-c", ResourceDisposition.AVAILABLE),
        ),
    )
    assert decision.deferred is True
    reasons = {item.resource_id: item.reasons for item in decision.rejected}
    assert "resource_outside_authority" in reasons["c"]


def test_cannot_build_provider_envelope_for_declined_resource():
    with pytest.raises(ProviderPortabilityError):
        build_provider_task_envelope(
            lineage(),
            resource("a", "provider-a", ResourceDisposition.DECLINED),
            dispatch_nonce="attempt-001",
            max_runtime_seconds=900,
        )


def test_binding_detects_envelope_substitution():
    internal = lineage()
    envelope, binding = build_provider_task_envelope(
        internal,
        resource("a", "provider-a"),
        dispatch_nonce="attempt-001",
        max_runtime_seconds=900,
    )
    other, _ = build_provider_task_envelope(
        internal,
        resource("b", "provider-b"),
        dispatch_nonce="attempt-001",
        max_runtime_seconds=900,
    )
    assert verify_provider_binding(internal, envelope, binding)
    assert not verify_provider_binding(internal, other, binding)
