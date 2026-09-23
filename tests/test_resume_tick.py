from dataclasses import replace

import pytest

from general_execution import (
    CheckpointEvidence,
    CoreVerificationReceipt,
    CoreVerificationRequirement,
    PortfolioEntry,
    PortfolioPersistenceError,
    PortfolioState,
    ResumeTickError,
    ResumeTickObservation,
    SqlitePortfolioHeadStore,
    TransitionPolicy,
    TransitionRule,
    resume_tick,
)

WAVE5_REVISION = "8f6494eca2c730de49b2e6ebfeb085cad1f33744"
D = "sha256:" + "d" * 64


def evidence(kind):
    return CheckpointEvidence(
        kind=kind,
        locator=f"artifact://{kind}",
        digest=D,
    )


def active(state="ready"):
    return PortfolioEntry(
        work_id="ACTIVE",
        role="active",
        state=state,
        objective="Advance active frontier",
        active_gate="ACTIVE_GATE",
        next_action_ref="action://active",
        source_revision="src-active",
        evidence_required=("result",),
    )


def secondary():
    return PortfolioEntry(
        work_id="SECONDARY",
        role="secondary",
        state="ready",
        objective="Prepare secondary frontier",
        active_gate="SECONDARY_GATE",
        next_action_ref="action://secondary",
        source_revision="src-secondary",
    )


def portfolio(state="ready"):
    return PortfolioState(
        portfolio_id="durable-asp",
        generation=0,
        active=active(state),
        secondary=secondary(),
        passive=(),
    )


def policy():
    return TransitionPolicy(
        policy_id="durable-tick-v1",
        revision="1",
        rules=(
            TransitionRule(
                rule_id="01-start",
                from_state="ready",
                event="execution_started",
                to_state="running",
                next_action_ref="action://observe-run",
                required_evidence=("dispatch_admitted",),
            ),
            TransitionRule(
                rule_id="02-human",
                from_state="running",
                event="authority_required",
                to_state="human_gate",
                next_action_ref="authority://human-decision",
                effect="stop_human_gate",
                required_evidence=("authority_boundary_reached",),
                authority_mode="human_required",
                authority_boundary="release approval",
            ),
        ),
    )


def requirement(**changes):
    values = dict(
        required_revision=WAVE5_REVISION,
        required_suite_ref="tests://wave5-executable-regression",
        required_verifier_ref="verifier://independent-python-runtime",
        minimum_test_count=18,
    )
    values.update(changes)
    return CoreVerificationRequirement(**values)


def receipt(**changes):
    values = dict(
        target_revision=WAVE5_REVISION,
        suite_ref="tests://wave5-executable-regression",
        evidence_ref="artifact://wave5-test-report",
        evidence_digest=D,
        verifier_ref="verifier://independent-python-runtime",
        executed_at="2026-09-23T16:30:00Z",
        passed=True,
        test_count=18,
    )
    values.update(changes)
    return CoreVerificationReceipt(**values)


def observation(state, p=None, **changes):
    p = p or policy()
    values = dict(
        portfolio_id=state.portfolio_id,
        expected_generation=state.generation,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event="execution_started",
        evidence=(evidence("dispatch_admitted"),),
        action_ref="action://dispatch-observed",
        observed_at="2026-09-23T16:31:00Z",
        summary="Dispatch was independently admitted",
        canonical_refs=("artifact://dispatch",),
    )
    values.update(changes)
    return ResumeTickObservation(**values)


def initialized_store(tmp_path, state):
    store = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    store.initialize(state)
    return store


def test_verification_receipt_must_record_real_pass():
    with pytest.raises(ResumeTickError, match="must record PASS"):
        receipt(passed=False)
    with pytest.raises(ResumeTickError, match="test_count must be >= 1"):
        receipt(test_count=0)
    with pytest.raises(ResumeTickError, match="40-character commit SHA"):
        receipt(target_revision="not-a-sha")


def test_closed_core_gate_cannot_mutate_even_without_observation(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)

    result = resume_tick(
        store,
        state.portfolio_id,
        policy(),
        None,
        core_requirement=requirement(),
        core_verification=None,
    )

    reloaded, _ = store.load(state.portfolio_id)
    assert result.disposition == "verification_gate_closed"
    assert result.observation_digest is None
    assert reloaded == state
    assert result.pre_generation == result.post_generation == 0


def test_wrong_core_revision_keeps_gate_closed(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)
    obs = observation(state)

    result = resume_tick(
        store,
        state.portfolio_id,
        policy(),
        obs,
        core_requirement=requirement(required_revision="1" * 40),
        core_verification=receipt(),
    )

    assert result.disposition == "verification_gate_closed"
    reloaded, _ = store.load(state.portfolio_id)
    assert reloaded == state




def test_core_requirement_binds_suite_verifier_and_minimum_count(tmp_path):
    state = portfolio()
    obs = observation(state)
    variants = (
        requirement(required_suite_ref="tests://other-suite"),
        requirement(required_verifier_ref="verifier://other"),
        requirement(minimum_test_count=19),
    )

    for index, gate in enumerate(variants):
        store = SqlitePortfolioHeadStore(tmp_path / f"portfolio-{index}.db")
        store.initialize(state)
        result = resume_tick(
            store,
            state.portfolio_id,
            policy(),
            obs,
            core_requirement=gate,
            core_verification=receipt(),
        )
        assert result.disposition == "verification_gate_closed"
        reloaded, _ = store.load(state.portfolio_id)
        assert reloaded == state


def test_open_gate_without_observation_requests_external_input(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)

    result = resume_tick(
        store,
        state.portfolio_id,
        policy(),
        None,
        core_requirement=requirement(),
        core_verification=receipt(),
    )

    assert result.disposition == "external_input_required"
    assert result.observation_digest is None
    reloaded, _ = store.load(state.portfolio_id)
    assert reloaded == state


def test_tick_observation_is_bound_to_transition_policy(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)
    p = policy()
    wrong = replace(observation(state, p), policy_digest="sha256:" + "a" * 64)

    with pytest.raises(ResumeTickError, match="transition policy mismatch"):
        resume_tick(
            store,
            state.portfolio_id,
            p,
            wrong,
            required_core_revision=WAVE5_REVISION,
            core_verification=receipt(),
        )

    reloaded, _ = store.load(state.portfolio_id)
    assert reloaded == state


def test_one_tick_commits_exactly_one_generation_and_cold_recovers(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)
    p = policy()
    obs = observation(state, p)

    result = resume_tick(
        store,
        state.portfolio_id,
        p,
        obs,
        core_requirement=requirement(),
        core_verification=receipt(),
    )

    assert result.disposition == "committed"
    assert result.pre_generation == 0
    assert result.post_generation == 1
    assert result.pre_state_digest == state.digest
    assert result.post_state_digest != state.digest
    assert result.checkpoint_digest is not None
    assert result.transition_result_digest is not None
    assert result.recovery_report_digest is not None

    restarted = SqlitePortfolioHeadStore(tmp_path / "portfolio.db")
    reloaded, _ = restarted.load(state.portfolio_id)
    checkpoint = restarted.latest_checkpoint(state.portfolio_id)
    assert reloaded.generation == 1
    assert reloaded.active.state == "running"
    assert checkpoint is not None
    assert obs.checkpoint_ref in checkpoint.canonical_refs
    assert f"core-requirement:{requirement().digest}" in checkpoint.canonical_refs
    assert f"core-verification:{receipt().digest}" in checkpoint.canonical_refs


def test_immediate_replay_is_idempotent_and_does_not_advance_generation(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)
    p = policy()
    obs = observation(state, p)
    verification = receipt()

    first = resume_tick(
        store,
        state.portfolio_id,
        p,
        obs,
        core_requirement=requirement(),
        core_verification=verification,
    )
    replay = resume_tick(
        store,
        state.portfolio_id,
        p,
        obs,
        core_requirement=requirement(),
        core_verification=verification,
    )

    reloaded, _ = store.load(state.portfolio_id)
    assert first.disposition == "committed"
    assert replay.disposition == "already_applied"
    assert replay.pre_generation == replay.post_generation == 1
    assert reloaded.generation == 1
    assert replay.checkpoint_digest == first.checkpoint_digest




def test_concurrent_duplicate_commit_resolves_as_already_applied(tmp_path):
    class DuplicateRaceStore(SqlitePortfolioHeadStore):
        def __init__(self, path):
            super().__init__(path)
            self.inject_duplicate_race = True

        def commit(self, portfolio_id, expected_state_digest, new_state, checkpoint):
            if self.inject_duplicate_race:
                self.inject_duplicate_race = False
                super().commit(
                    portfolio_id,
                    expected_state_digest,
                    new_state,
                    checkpoint,
                )
                raise PortfolioPersistenceError("simulated duplicate writer")
            return super().commit(
                portfolio_id,
                expected_state_digest,
                new_state,
                checkpoint,
            )

    state = portfolio()
    store = DuplicateRaceStore(tmp_path / "portfolio.db")
    store.initialize(state)
    p = policy()
    obs = observation(state, p)

    result = resume_tick(
        store,
        state.portfolio_id,
        p,
        obs,
        core_requirement=requirement(),
        core_verification=receipt(),
    )

    reloaded, _ = store.load(state.portfolio_id)
    checkpoint = store.latest_checkpoint(state.portfolio_id)
    assert result.disposition == "already_applied"
    assert result.pre_generation == result.post_generation == 1
    assert reloaded.generation == 1
    assert checkpoint is not None
    assert obs.checkpoint_ref in checkpoint.canonical_refs
    assert result.checkpoint_digest == checkpoint.digest


def test_stale_observation_never_mutates_current_head(tmp_path):
    state = portfolio()
    store = initialized_store(tmp_path, state)
    p = policy()
    stale = observation(state, p)

    first = resume_tick(
        store,
        state.portfolio_id,
        p,
        stale,
        core_requirement=requirement(),
        core_verification=receipt(),
    )
    current, _ = store.load(state.portfolio_id)

    another = ResumeTickObservation(
        portfolio_id=current.portfolio_id,
        expected_generation=0,
        expected_state_digest=state.digest,
        policy_digest=p.digest,
        event="authority_required",
        evidence=(evidence("authority_boundary_reached"),),
        action_ref="authority://observed",
        observed_at="2026-09-23T16:32:00Z",
        summary="Authority boundary observed",
        canonical_refs=("artifact://authority-boundary",),
    )

    result = resume_tick(
        store,
        state.portfolio_id,
        p,
        another,
        core_requirement=requirement(),
        core_verification=receipt(),
    )

    reloaded, _ = store.load(state.portfolio_id)
    assert first.disposition == "committed"
    assert result.disposition == "stale_observation"
    assert reloaded == current
    assert reloaded.generation == 1


def test_human_gate_tick_commits_stop_and_never_auto_continues(tmp_path):
    base = portfolio()
    store = initialized_store(tmp_path, base)
    p = policy()
    verification = receipt()

    start = observation(base, p)
    first = resume_tick(
        store,
        base.portfolio_id,
        p,
        start,
        core_requirement=requirement(),
        core_verification=verification,
    )
    assert first.disposition == "committed"

    current, _ = store.load(base.portfolio_id)
    human = ResumeTickObservation(
        portfolio_id=current.portfolio_id,
        expected_generation=current.generation,
        expected_state_digest=current.digest,
        policy_digest=p.digest,
        event="authority_required",
        evidence=(evidence("authority_boundary_reached"),),
        action_ref="authority://boundary-observed",
        observed_at="2026-09-23T16:33:00Z",
        summary="Release approval boundary reached",
        canonical_refs=("artifact://authority-boundary",),
    )

    stopped = resume_tick(
        store,
        base.portfolio_id,
        p,
        human,
        core_requirement=requirement(),
        core_verification=verification,
    )

    final, _ = store.load(base.portfolio_id)
    checkpoint = store.latest_checkpoint(base.portfolio_id)
    assert stopped.disposition == "committed"
    assert final.active.state == "human_gate"
    assert final.active.authority_ref is None
    assert checkpoint is not None
    assert checkpoint.authority_stop
    assert checkpoint.next_transition_refs == ()


def test_observation_identity_is_deterministic_and_state_bound():
    state = portfolio()
    p = policy()
    left = observation(state, p)
    right = observation(state, p)
    assert left.digest == right.digest
    assert left.observation_id == right.observation_id
    assert left.checkpoint_ref == right.checkpoint_ref

    changed = replace(left, expected_generation=1)
    assert changed.digest != left.digest
    assert changed.checkpoint_ref != left.checkpoint_ref
