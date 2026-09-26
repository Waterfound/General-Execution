import json
from dataclasses import replace

import pytest

from general_execution import (
    PortfolioBlocker,
    PortfolioEntry,
    PortfolioState,
    PortfolioStateError,
    WakeCondition,
    deserialize_portfolio_state,
    portfolio_state_from_dict,
    portfolio_state_to_dict,
    serialize_portfolio_state,
)

D = "sha256:" + "a" * 64


def blocker(kind="external_dependency", detail="waiting for provider"):
    return PortfolioBlocker(kind=kind, detail=detail, evidence_refs=("artifact:blocker",))


def wake(kind="event_received", value="provider.available"):
    return WakeCondition(kind=kind, value=value)


def active(**changes):
    values = dict(
        work_id="FAE-BE-04",
        role="active",
        state="running",
        objective="Bind the public explorer to an independently reachable node",
        active_gate="PUBLIC_NODE_BINDING",
        next_action_ref="action://deploy-prebind",
        source_revision="abc123",
        evidence_required=("deployment_url", "commit_sha", "verifier_pass"),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def secondary(**changes):
    values = dict(
        work_id="FAE-WALLET-UX",
        role="secondary",
        state="ready",
        objective="Expose transaction IDs and transaction history",
        active_gate="WALLET_TX_DISCOVERABILITY",
        next_action_ref="action://inspect-wallet-current-state",
        source_revision="def456",
        evidence_required=("ui_test",),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def passive(work_id="FAE-SOAK-V3", **changes):
    values = dict(
        work_id=work_id,
        role="passive",
        state="passive",
        objective="Run the prepared 96h network stability soak",
        active_gate="RENDER_CAPACITY_AVAILABLE",
        next_action_ref="action://soak-preflight",
        source_revision="8e061f81",
        evidence_required=("render_unsuspended", "budget_floor"),
        blockers=(blocker("infrastructure", "Render capacity unavailable"),),
        wake_condition=wake("event_received", "render.unsuspended"),
    )
    values.update(changes)
    return PortfolioEntry(**values)


def portfolio(**changes):
    values = dict(
        portfolio_id="fae-mainnet-critical",
        generation=0,
        active=active(),
        secondary=secondary(),
        passive=(passive(),),
    )
    values.update(changes)
    return PortfolioState(**values)


def test_portfolio_state_has_deterministic_identity():
    assert portfolio().digest == portfolio().digest
    assert portfolio().digest.startswith("sha256:")


def test_portfolio_state_round_trip_is_canonical():
    state = portfolio()
    encoded = serialize_portfolio_state(state)
    decoded = deserialize_portfolio_state(encoded)
    assert decoded == state
    assert decoded.digest == state.digest
    assert encoded == serialize_portfolio_state(decoded)


def test_portfolio_state_dict_round_trip():
    state = portfolio()
    decoded = portfolio_state_from_dict(json.loads(json.dumps(portfolio_state_to_dict(state))))
    assert decoded == state


def test_exactly_one_active_and_one_secondary_are_structural():
    state = portfolio()
    assert state.active.role == "active"
    assert state.secondary.role == "secondary"
    assert len(state.passive) == 1


def test_active_slot_rejects_non_active_role():
    with pytest.raises(PortfolioStateError, match="active slot"):
        portfolio(active=replace(active(), role="secondary", state="ready"))


def test_secondary_slot_rejects_non_secondary_role():
    with pytest.raises(PortfolioStateError, match="secondary slot"):
        portfolio(secondary=replace(secondary(), role="active", state="running"))


def test_passive_slot_rejects_non_passive_role():
    with pytest.raises(PortfolioStateError, match="passive slots"):
        portfolio(passive=(replace(passive(), role="active", state="running", wake_condition=None),))


def test_duplicate_work_ids_are_rejected():
    with pytest.raises(PortfolioStateError, match="work_id values must be unique"):
        portfolio(secondary=secondary(work_id="FAE-BE-04"))


def test_secondary_must_remain_ready():
    with pytest.raises(PortfolioStateError, match="secondary entry must remain ready"):
        secondary(state="running")


def test_secondary_cannot_hide_blocker_or_wake_condition():
    with pytest.raises(PortfolioStateError, match="cannot carry blockers"):
        secondary(blockers=(blocker(),))
    with pytest.raises(PortfolioStateError, match="cannot carry wake condition"):
        secondary(wake_condition=wake())


def test_passive_requires_explicit_blocker_and_wake_condition():
    with pytest.raises(PortfolioStateError, match="requires at least one blocker"):
        passive(blockers=())
    with pytest.raises(PortfolioStateError, match="explicit wake condition"):
        passive(wake_condition=None)


def test_passive_entries_are_sorted_for_one_canonical_representation():
    with pytest.raises(PortfolioStateError, match="sorted by work_id"):
        portfolio(
            passive=(
                passive("ZZZ"),
                passive("AAA"),
            )
        )


def test_active_waiting_external_requires_blocker():
    with pytest.raises(PortfolioStateError, match="requires a blocker"):
        active(state="waiting_external", blockers=(), wake_condition=wake())


def test_active_wake_condition_is_limited_to_waiting_external():
    with pytest.raises(PortfolioStateError, match="valid only while waiting_external"):
        active(wake_condition=wake())


def test_human_gate_requires_explicit_authority_boundary_and_blocker():
    with pytest.raises(PortfolioStateError, match="requires authority_boundary"):
        active(
            state="human_gate",
            blockers=(blocker("authority", "human approval required"),),
        )
    with pytest.raises(PortfolioStateError, match="authorization/authority blocker"):
        active(
            state="human_gate",
            authority_boundary="release approval",
            blockers=(blocker("external_dependency", "waiting"),),
        )


def test_human_gate_is_representable_without_granting_authority():
    entry = active(
        state="human_gate",
        authority_boundary="spend above existing budget ceiling",
        blockers=(blocker("authority", "human approval required"),),
        next_action_ref="authority://request-human-decision",
    )
    assert entry.authority_ref is None
    assert entry.state == "human_gate"


def test_generation_zero_has_no_predecessor():
    with pytest.raises(PortfolioStateError, match="generation zero"):
        portfolio(previous_state_digest=D)


def test_later_generation_requires_valid_predecessor_digest():
    with pytest.raises(PortfolioStateError, match="requires previous_state_digest"):
        portfolio(generation=1)
    with pytest.raises(PortfolioStateError, match="sha256"):
        portfolio(generation=1, previous_state_digest="not-a-digest")

    state = portfolio(generation=1, previous_state_digest=D)
    assert state.generation == 1
    assert state.previous_state_digest == D


def test_unknown_schema_fields_fail_closed():
    data = portfolio_state_to_dict(portfolio())
    data["unexpected"] = True
    with pytest.raises(PortfolioStateError, match="fields mismatch"):
        portfolio_state_from_dict(data)


def test_nested_unknown_fields_fail_closed():
    data = portfolio_state_to_dict(portfolio())
    data["active"]["unexpected"] = True
    with pytest.raises(PortfolioStateError, match="portfolio entry fields mismatch"):
        portfolio_state_from_dict(data)


def test_schema_version_tampering_fails_closed():
    data = portfolio_state_to_dict(portfolio())
    data["schema_version"] = "ge.portfolio-state.v999"
    with pytest.raises(PortfolioStateError, match="unsupported portfolio state schema"):
        portfolio_state_from_dict(data)


def test_malformed_json_fails_closed():
    with pytest.raises(PortfolioStateError, match="not valid JSON"):
        deserialize_portfolio_state("{broken")


def test_duplicate_evidence_requirements_are_rejected():
    with pytest.raises(PortfolioStateError, match="must not contain duplicates"):
        active(evidence_required=("commit_sha", "commit_sha"))


def test_duplicate_blockers_are_rejected():
    item = blocker()
    with pytest.raises(PortfolioStateError, match="blockers must not contain duplicates"):
        active(blockers=(item, item))
