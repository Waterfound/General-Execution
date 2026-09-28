import json

import pytest

from general_execution.canonical import sha256_digest
from general_execution.persistent_runtime import trigger_digest_from_event
from general_execution.portfolio_persistence import SqlitePortfolioHeadStore
from general_execution.portfolio_state import PortfolioBlocker, PortfolioEntry, PortfolioState
from general_execution.provider_host import (
    ProviderHostError,
    ProviderSnapshot,
    ProviderWatch,
    build_provider_runtime_event,
)
from general_execution.transition_policy import TransitionPolicy, TransitionRule


def portfolio(state="running"):
    kwargs = {}
    if state == "human_gate":
        kwargs = {
            "authority_boundary": "explicit approval required",
            "blockers": (
                PortfolioBlocker(
                    kind="authority",
                    detail="explicit approval required",
                    evidence_refs=("test://authority",),
                ),
            ),
        }
    return PortfolioState(
        portfolio_id="provider-host-test",
        generation=0,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state=state,
            objective="Test provider wake host",
            active_gate="PROVIDER",
            next_action_ref="action://wait-provider",
            source_revision="provider-host-test",
            evidence_required=("provider_ready",),
            **kwargs,
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="Remain inert",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="provider-host-test",
        ),
    )


def policy(from_state="running"):
    if from_state == "human_gate":
        return TransitionPolicy(
            policy_id="provider-host-test-policy",
            revision="1",
            rules=(
                TransitionRule(
                    rule_id="01-resume",
                    from_state="human_gate",
                    event="verification_passed",
                    to_state="running",
                    next_action_ref="action://resume",
                    required_evidence=("provider_ready",),
                    authority_mode="preauthorized_required",
                    authority_boundary="explicit approval required",
                ),
            ),
        )
    return TransitionPolicy(
        policy_id="provider-host-test-policy",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-stop",
                from_state="running",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://provider-host-test/continue",
                effect="stop_human_gate",
                required_evidence=("provider_ready",),
                authority_mode="human_required",
                authority_boundary="explicit approval required",
            ),
        ),
    )


def watch(**overrides):
    values = dict(
        watch_id="provider-host-test-watch",
        provider="test-provider",
        resource_id="resource-1",
        matched_state="available",
        portfolio_id="provider-host-test",
        transition_event="authority_required",
        evidence_kind="provider_ready",
        action_ref="provider://resource-1/available",
        summary="Provider resource became available",
        canonical_refs=("watch://provider-host-test",),
        uncertainties=(),
        policy=policy(),
    )
    values.update(overrides)
    return ProviderWatch(**values)


def snapshot(**overrides):
    values = dict(
        watch_id="provider-host-test-watch",
        provider="test-provider",
        resource_id="resource-1",
        provider_event_id="resource-1:available:1",
        observed_state="available",
        observed_at="2026-09-28T14:00:00Z",
        evidence_locator="provider://resource-1",
        metadata_digest=sha256_digest({"resource": "resource-1", "state": "available"}),
        canonical_refs=("provider://resource-1",),
    )
    values.update(overrides)
    return ProviderSnapshot(**values)


def init_db(tmp_path, state="running"):
    path = tmp_path / "runtime.db"
    SqlitePortfolioHeadStore(path).initialize(portfolio(state))
    return path


def test_unmatched_provider_state_is_noop(tmp_path):
    result = build_provider_runtime_event(
        init_db(tmp_path),
        watch(),
        snapshot(observed_state="pending", provider_event_id="resource-1:pending:1"),
    )
    assert not result.matched
    assert result.event is None
    assert result.event_id is None


def test_matched_snapshot_emits_deterministic_persistent_event(tmp_path):
    db = init_db(tmp_path)
    first = build_provider_runtime_event(db, watch(), snapshot())
    second = build_provider_runtime_event(db, watch(), snapshot())

    assert first.matched
    assert first == second
    assert first.event_id == snapshot().event_identity
    assert first.event["schema_version"] == "ge.persistent-runtime-event.v1"
    assert first.event["operation"] == "transition"
    assert first.event["body"]["observation"]["expected_generation"] == 0
    assert first.event["body"]["observation"]["event"] == "authority_required"
    assert first.event["body"]["observation"]["authority_grant"] is None
    assert trigger_digest_from_event(first.event) == sha256_digest(
        first.event["body"]["trigger"]
    )


def test_snapshot_cannot_choose_provider_or_resource(tmp_path):
    db = init_db(tmp_path)
    with pytest.raises(ProviderHostError, match="provider does not match"):
        build_provider_runtime_event(db, watch(), snapshot(provider="other"))
    with pytest.raises(ProviderHostError, match="resource_id does not match"):
        build_provider_runtime_event(db, watch(), snapshot(resource_id="other"))


def test_watch_must_supply_evidence_required_by_rule(tmp_path):
    db = init_db(tmp_path)
    with pytest.raises(ProviderHostError, match="evidence_kind"):
        build_provider_runtime_event(
            db,
            watch(evidence_kind="untrusted_kind"),
            snapshot(),
        )


def test_provider_snapshot_cannot_resume_human_gate(tmp_path):
    db = init_db(tmp_path, state="human_gate")
    human_watch = ProviderWatch(
        watch_id="provider-host-test-watch",
        provider="test-provider",
        resource_id="resource-1",
        matched_state="available",
        portfolio_id="provider-host-test",
        transition_event="verification_passed",
        evidence_kind="provider_ready",
        action_ref="provider://resource-1/available",
        summary="Provider resource became available",
        canonical_refs=("watch://provider-host-test",),
        uncertainties=(),
        policy=policy("human_gate"),
    )
    with pytest.raises(ProviderHostError, match="cannot resume a human gate"):
        build_provider_runtime_event(db, human_watch, snapshot())


def test_snapshot_payload_contains_no_provider_metadata_or_credentials(tmp_path):
    result = build_provider_runtime_event(init_db(tmp_path), watch(), snapshot())
    encoded = json.dumps(result.event, sort_keys=True)
    assert "password" not in encoded.lower()
    assert "secret" not in encoded.lower()
    assert "credential" not in encoded.lower()
    assert snapshot().digest in encoded\n    assert snapshot().metadata_digest not in encoded
