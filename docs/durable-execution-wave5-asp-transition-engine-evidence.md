# Durable Execution Wave 5 — ASP Transition Engine Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 5 candidate head before this evidence commit:

```text
8f6494eca2c730de49b2e6ebfeb085cad1f33744
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

The candidate is strictly ahead of the canonical base and `main` remains untouched.

## F6 — ASP transition engine

`src/general_execution/asp_transition_engine.py` is the first Durable Execution frontier permitted to construct the next `PortfolioState`.

It remains a pure transition layer. It does not:

- persist state;
- call a provider;
- dispatch work;
- sleep or schedule;
- execute a retry;
- invoke DI;
- invoke Build Colony;
- verify external facts;
- merge, release, spend, or create authority.

Its only authority is to apply an already-admissible transition rule to already-admitted evidence.

## Frozen transition input

A transition application binds:

- current `PortfolioState`;
- exact `TransitionPolicy`;
- exact matched rule;
- event;
- admitted checkpoint evidence;
- explicit observation timestamp;
- canonical references;
- optional uncertainty statements;
- an optional preauthorized authority reference when the rule explicitly requires it.

Unknown/unmatched transitions remain STOP-by-default through `match_transition_rule`.

## Passive wake admission

Wave 5 introduces two narrow objects:

- `PassiveWakeSignal`
- `PassiveWakeAdmission`

The core intentionally does not interpret clocks, providers, Render state, GitHub state, or other external conditions.

A future adapter may assert that a wake condition is satisfied. The engine admits that assertion only when:

1. the signal targets the exact passive work item;
2. the signal binds the exact stored `wake_condition.digest`;
3. the signal binds an admitted evidence object;
4. the policy contains an exact `passive + wake_satisfied -> ready` rule;
5. all evidence required by that wake rule is present.

The result is a deterministic `secondary/ready` candidate. Wake admission itself does not mutate the portfolio.

## Slot-refill invariant

The existing portfolio contract requires exactly:

```text
1 Active
1 Secondary
N Passive
```

Therefore `Secondary -> Active` cannot simply leave the Secondary slot empty.

Wave 5 freezes the following fail-closed rule:

> promotion or parking that consumes the current Secondary MUST also provide an explicitly wake-admitted replacement Secondary from the durable Passive set.

No completed work is relabeled as Passive merely to fill a slot, and no new work item is invented from conversation context.

This gives a clean machine interpretation of Passive backlog items whose wake condition can include a lane-availability event such as `secondary_slot.available`.

## Verified completion

For `promote_secondary`:

- policy event must be `verification_passed`;
- the current Active must actually be `verifying`;
- required verifier evidence must be admitted;
- a replacement Secondary must already have a valid wake admission;
- current Secondary becomes the new Active in `ready`;
- wake-admitted Passive becomes the new Secondary in `ready`;
- completed Active leaves the live portfolio and remains durably represented by the checkpoint/history;
- remaining Passive items are preserved in canonical order.

The engine does not auto-start the promoted Active. That belongs to the later resume/tick runtime.

## External-blocker parking

For `park_active`:

- exact external-blocker rule must match;
- policy-required blocker evidence must be present;
- evidence that no admissible internal work remains can be required by policy;
- parked Active must receive explicit blockers;
- parked Active must receive an explicit wake condition;
- current Secondary becomes Active;
- a wake-admitted Passive refills Secondary;
- parked Active joins the Passive set in canonical order.

The engine cannot fabricate the blocker, wake condition, or replacement work.

## DI and human boundaries

`request_di` only constructs:

```text
active.state = di_required
next_action_ref = action://...
```

It does not invoke or repair DI.

`stop_human_gate` constructs a `human_gate` Active with an explicit authority blocker and produces a checkpoint with:

```text
authority_stop = true
next_transition_refs = ()
```

No automatic continuation is present.

## Preauthorized transitions

If a transition rule declares `preauthorized_required`, Wave 5 requires:

- an explicit authority reference supplied to the application;
- admitted evidence whose locator is exactly that authority reference.

The resulting Active may record the bounded authority reference and boundary, but the engine still receives no transport authority.

## Branch regression surface

The exact branch now contains 16 dedicated ASP engine tests covering:

- wake condition/evidence binding;
- deterministic wake candidate construction;
- normal state transition + checkpoint binding;
- missing-evidence fail-closed behavior;
- unmatched transition fail-closed behavior;
- DI request semantics;
- human-gate stop semantics;
- verified Secondary promotion;
- promotion without replacement rejection;
- verified-state invariant even under a looser policy;
- Active parking;
- blocker/wake requirements;
- cross-policy wake admission rejection;
- lane-input misuse rejection;
- deterministic application identity;
- evidence-bound preauthorized authority.

## Focused semantic reproduction

Because the local container still cannot materialize the GitHub branch directly, a focused semantic reproduction exercised the critical Wave 5 state-machine behavior.

Observed result:

```text
promotion = PASS
parking = PASS
passive wake admission = PASS
DI request = PASS
human gate = PASS
predecessor binding = PASS
3 explicit fail-closed checks = PASS
```

The reproduction specifically confirmed:

- verified Active completion promotes the existing Secondary;
- an admitted Passive refills Secondary;
- the consumed Passive is removed without disturbing the rest of Passive N;
- external-blocker parking preserves the parked task and its wake condition;
- DI remains a requested next action rather than a repair engine;
- human authority remains a stop;
- missing replacement, wrong wake condition, and missing required evidence fail closed.

## Public API verification

The actual branch package exports all Wave 5 public symbols:

- `AspTransitionApplication`
- `AspTransitionError`
- `PassiveWakeAdmission`
- `PassiveWakeSignal`
- `admit_passive_wake`
- `apply_asp_transition`

## Verification boundary

Current evidence supports:

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = FOCUSED_PASS
F2_EXECUTION_CHECKPOINT = FOCUSED_PASS
F3_TRANSITION_POLICY = FOCUSED_PASS
F4_PORTFOLIO_PERSISTENCE = FOCUSED_REPRODUCTION_PASS
F5_BOUNDED_RETRY_AUTHORITY = FOCUSED_REPRODUCTION_PASS
F6_ASP_TRANSITION_ENGINE = FOCUSED_REPRODUCTION_PASS
EXACT_BRANCH_ASP_TESTS_PRESENT = 16
FULL_EXACT_BRANCH_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
AUTHORITY_CREATED = false
```

This evidence does not authorize merge to `main`.

## Next frontier

The next Build Colony wave is:

```text
resume-tick-runtime
```

That frontier may combine existing pieces into one short-lived, idempotent invocation:

```text
load durable portfolio
-> recover checkpoint
-> admit one external event/result
-> choose exactly one policy-admissible transition
-> construct next state/checkpoint
-> commit atomically
-> terminate
```

It still must not add provider-specific scheduling or broad external trigger infrastructure. Those remain after the core rehearsal gate.
