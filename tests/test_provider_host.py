from __future__ import annotations

import json

import pytest

from general_execution import sha256_digest
from general_execution.portfolio_state import PortfolioEntry, PortfolioState
from general_execution.provider_host import (
    ProviderHostError,
    build_provider_runtime_event,
    provider_input_from_dict,
    provider_watch_contract_from_dict,
)


def state(*, generation=2, active_state="verifying"):
    return PortfolioState(
        portfolio_id="pilot-provider-host",
        generation=generation,
        active=PortfolioEntry(
            work_id="ACTIVE",
            role="active",
            state=active_state,
            objective="provider pilot",
            active_gate="PILOT",
            next_action_ref="action://pilot",
            source_revision="abc",
            evidence_required=("provider_ready",),
        ),
        secondary=PortfolioEntry(
            work_id="SECONDARY",
            role="secondary",
            state="ready",
            objective="secondary",
            active_gate="SECONDARY",
            next_action_ref="action://secondary",
            source_revision="abc",
        ),
        passive=(),
        previous_state_digest=(
            None if generation == 0 else "sha256:" + "1" * 64
        ),
    )


def contract_dict(*, provider="aws-test", subject="provider://subject", active_state="verifying"):
    return {
        "watch_id": "watch-1",
        "provider": provider,
        "subject_ref": subject,
        "satisfied_state": "available",
        "portfolio_id": "pilot-provider-host",
        "transition_event": "authority_required",
        "evidence_kind": "provider_ready",
        "contract_ref": "github://contract/watch-1",
        "required_bindings": {
            "commit": "deadbeef",
            "artifact": "sha256-artifact",
        },
        "policy": {
            "policy_id": "provider-pilot",
            "revision": "1",
            "rules": [
                {
                    "rule_id": "01-stop",
                    "from_state": active_state,
                    "event": "authority_required",
                    "to_state": "human_gate",
                    "next_action_ref": "authority://pilot",
                    "effect": "stop_human_gate",
                    "required_evidence": ["provider_ready"],
                    "authority_mode": "human_required",
                    "authority_boundary": "pilot approval",
                    "schema_version": "ge.transition-rule.v1",
                }
            ],
            "default_disposition": "stop",
            "schema_version": "ge.transition-policy.v1",
        },
        "schema_version": "ge.provider-watch-contract.v1",
    }


def input_dict(*, provider="aws-test", subject="provider://subject", observed_state="available"):
    payload = {
        "watch_id": "watch-1",
        "provider": provider,
        "provider_event_id": "provider-event-123",
        "subject_ref": subject,
        "observed_state": observed_state,
        "observed_at": "2026-09-28T12:00:00Z",
        "evidence_locator": "provider-evidence://event-123",
        "evidence_digest": sha256_digest({"provider": provider, "state": observed_state}),
        "bindings": {
            "artifact": "sha256-artifact",
            "commit": "deadbeef",
        },
        "canonical_refs": [
            "provider://subject",
            "provider-evidence://event-123",
        ],
        "schema_version": "ge.provider-input.v1",
    }
    return payload


def build(**kwargs):
    contract = provider_watch_contract_from_dict(contract_dict(**kwargs))
    provider_input = provider_input_from_dict(input_dict(
        provider=kwargs.get("provider", "aws-test"),
        subject=kwargs.get("subject", "provider://subject"),
    ))
    return build_provider_runtime_event(state(active_state=kwargs.get("active_state", "verifying")), contract, provider_input)


def test_provider_host_builds_deterministic_human_stop_event_without_authority_grant():
    event_a, result_a = build()
    event_b, result_b = build()
    assert event_a == event_b
    assert result_a == result_b
    assert result_a.status == "event_ready"
    assert event_a["event_id"].startswith("geph-")
    body = event_a["body"]
    assert body["observation"]["authority_grant"] is None
    assert body["observation"]["event"] == "authority_required"
    assert body["policy"]["rules"][0]["authority_mode"] == "human_required"
    assert body["policy"]["rules"][0]["to_state"] == "human_gate"
    assert body["trigger"]["payload_digest"] == result_a.provider_input_digest
    assert body["trigger"]["observation_digest"].startswith("sha256:")


def test_unsatisfied_provider_state_is_a_clean_noop():
    contract = provider_watch_contract_from_dict(contract_dict())
    provider_input = provider_input_from_dict(input_dict(observed_state="pending"))
    event, result = build_provider_runtime_event(state(), contract, provider_input)
    assert event is None
    assert result.status == "condition_not_satisfied"
    assert result.event_id is None
    assert result.event_digest is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("provider", "wrong-provider", "provider mismatch"),
        ("subject_ref", "provider://wrong", "subject_ref mismatch"),
    ],
)
def test_identity_substitution_fails_closed(field, value, message):
    contract = provider_watch_contract_from_dict(contract_dict())
    raw = input_dict()
    raw[field] = value
    provider_input = provider_input_from_dict(raw)
    with pytest.raises(ProviderHostError, match=message):
        build_provider_runtime_event(state(), contract, provider_input)


def test_binding_substitution_fails_closed():
    contract = provider_watch_contract_from_dict(contract_dict())
    raw = input_dict()
    raw["bindings"]["artifact"] = "other"
    provider_input = provider_input_from_dict(raw)
    with pytest.raises(ProviderHostError, match="provider binding mismatch"):
        build_provider_runtime_event(state(), contract, provider_input)


def test_input_cannot_smuggle_policy_or_authority():
    raw = input_dict()
    raw["authority_grant"] = {"anything": "forbidden"}
    with pytest.raises(ProviderHostError, match="unknown=.*authority_grant"):
        provider_input_from_dict(raw)


def test_contract_cannot_resume_human_gate():
    raw = contract_dict(active_state="human_gate")
    raw["policy"]["rules"][0]["authority_mode"] = "preauthorized_required"
    raw["policy"]["rules"][0]["effect"] = "none"
    raw["policy"]["rules"][0]["to_state"] = "running"
    with pytest.raises(ProviderHostError, match="cannot resume human-gated work"):
        provider_watch_contract_from_dict(raw)


def test_current_state_must_have_unique_matching_rule():
    contract = provider_watch_contract_from_dict(contract_dict(active_state="ready"))
    provider_input = provider_input_from_dict(input_dict())
    with pytest.raises(ProviderHostError, match="no unique rule"):
        build_provider_runtime_event(state(active_state="verifying"), contract, provider_input)


def test_replay_identity_changes_if_durable_generation_changes():
    contract = provider_watch_contract_from_dict(contract_dict(active_state="verifying"))
    provider_input = provider_input_from_dict(input_dict())
    e2, _ = build_provider_runtime_event(state(generation=2), contract, provider_input)
    e3, _ = build_provider_runtime_event(state(generation=3), contract, provider_input)
    assert e2["event_id"] != e3["event_id"]
    assert e2["body"]["observation"]["expected_generation"] == 2
    assert e3["body"]["observation"]["expected_generation"] == 3


def test_same_host_contract_generalizes_across_provider_names():
    aws_event, _ = build(provider="aws-test", subject="provider://aws")
    gh_event, _ = build(provider="github-test", subject="provider://github")
    assert aws_event["body"]["trigger"]["source"] == "provider-host:aws-test"
    assert gh_event["body"]["trigger"]["source"] == "provider-host:github-test"
    assert aws_event["event_id"] != gh_event["event_id"]
