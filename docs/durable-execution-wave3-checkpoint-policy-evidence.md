# Durable Execution Wave 3 — Checkpoint and Transition Policy Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 3 candidate head:

```text
96152732f15f3df5e8a53ed1c2b192bd21134c6d
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

The candidate is strictly ahead of the canonical base and remains independent of the divergent experimental `v0.0.14*` and `v0.0.15*` lines.

## Implemented contracts

### execution_checkpoint

`src/general_execution/execution_checkpoint.py` makes execution evidence first-class.

A checkpoint now binds:

- portfolio identity and generation;
- exact portfolio-state digest;
- work identity and role;
- state before and state after;
- exact action reference and source revision;
- explicit observation timestamp supplied by the caller;
- summary of what happened;
- admitted evidence with SHA-256 identity;
- canonical references;
- remaining uncertainties;
- next admissible transition references;
- explicit authority-stop state and authority boundary.

The contract fails closed when evidence is absent, schema fields are unknown, digests are malformed, a nonterminal checkpoint omits the next transition, or an authority stop attempts to declare an automatic continuation.

### transition_policy

`src/general_execution/transition_policy.py` makes transition admissibility deterministic without applying transitions.

A policy contains canonical, uniquely matched rules over:

```text
(current_state, event)
    -> target_state
    -> next_action_ref
    -> declared effect
    -> required evidence
    -> authority mode/boundary
```

The default disposition is fixed to:

```text
STOP
```

Unknown states/events and unmatched transitions fail closed.

The contract constrains sensitive effects:

- `promote_secondary` only after `verification_passed -> complete`;
- `park_active` only for `external_blocker -> passive`;
- `wake_passive` only for `passive + wake_satisfied -> ready`;
- `request_di` must target `di_required`;
- `human_required` must stop at `human_gate`;
- human authority rules cannot masquerade as ordinary automatic transitions.

`match_transition_rule` performs deterministic lookup only. It does not mutate portfolio state, execute work, verify results, invoke DI, promote work, wake work, or grant authority.

## Executable verification

Focused isolated execution compiled the exact Wave 3 modules and ran the exact new test banks.

First run:

```text
52 passed
1 failed
```

The only failure was a test-regex defect: the literal `+` in the expected error text was interpreted as a regular-expression metacharacter. The implementation had raised the intended fail-closed error.

Only the test matcher was corrected by escaping `+`; transition logic was unchanged.

Second run:

```text
compileall: PASS
53 passed in 0.07s
```

The branch's actual public API surface was then inspected through GitHub. All 15 new checkpoint/policy symbols required by the Wave 3 contract are exported.

## Preserved earlier evidence

The prior F1 `portfolio_state` contract remains unchanged by Wave 3 and retains its recorded focused result:

```text
24/24 PASS
```

That result was not reclassified as a new full-repository regression.

## Verification boundary

The current execution environment still cannot resolve `github.com` from the local container, so the complete General Execution repository regression bank has not been executed against this branch.

Therefore the evidence supports:

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = FOCUSED_PASS
F2_EXECUTION_CHECKPOINT = FOCUSED_PASS
F3_TRANSITION_POLICY = FOCUSED_PASS
WAVE_3_FOCUSED_TESTS = 53/53 PASS
FULL_REPOSITORY_REGRESSION = NOT_RUN_IN_CURRENT_RUNTIME
MAIN_INTEGRATION = NOT_AUTHORIZED
AUTHORITY_CREATED = false
```

## Next frontier

The next Build Colony wave is:

1. `portfolio-persistence`
2. `bounded-retry-authority`

These may proceed in parallel because their write surfaces are independent, but neither may apply the Active/Secondary/Passive transition engine yet.

Wave 5 remains the first point where the policy may be used to construct a new portfolio state.
