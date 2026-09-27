# Durable Execution Wave 4 — Portfolio Persistence and Bounded Retry Authority Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 4 code/test candidate head before this evidence update:

```text
27286d1c503505005dd8b01f6d1c0e0b7f0b6568
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

The candidate is strictly ahead of the canonical base and remains independent of the divergent experimental `v0.0.14*` and `v0.0.15*` lines.

## Reconciliation of the pre-existing Wave 4 candidate

A pre-existing Wave 4 candidate was found on the branch before finalization. It already contained:

- a SQLite portfolio head with generation/CAS semantics;
- a bounded retry policy with timeout/throttle/reproduction limits.

Evidence review found three contract gaps:

1. portfolio persistence did not atomically persist `execution_checkpoint` with the new state;
2. `cost_boundary` incorrectly escalated to a human gate instead of stopping immediately;
3. retry failure observations were not bound to an immutable evidence digest.

The final Wave 4 candidate corrects those gaps rather than replacing the existing design wholesale.

## F4 — portfolio-persistence

`src/general_execution/portfolio_persistence.py` now persists the portfolio head and checkpoint history as one transactional boundary.

The store:

- persists the exact canonical `PortfolioState` snapshot;
- binds portfolio identity, state digest, generation, and snapshot digest;
- stores one durable checkpoint per nonzero portfolio generation;
- binds every checkpoint to the exact resulting portfolio ID, generation, and state digest;
- atomically inserts the checkpoint and advances the portfolio head in the same SQLite transaction;
- uses `BEGIN IMMEDIATE` and compare-and-swap;
- requires initialization at generation zero;
- requires every commit to advance exactly one generation;
- requires `previous_state_digest` to equal the current canonical state digest;
- rejects stale writers and cross-portfolio commits;
- detects snapshot, head metadata, checkpoint ID, and checkpoint digest tampering;
- rolls back the head update when checkpoint insertion fails;
- reopens from a fresh process and reconstructs the latest state + checkpoint without chat history;
- supports additive schema migration for an older `portfolio_heads` table lacking `latest_checkpoint_digest`.

New recovery surface:

- `PortfolioRecoveryReport`
- `recover_portfolio_after_restart`
- `verify_portfolio_recovery`

Recovery is observational only. It cannot fabricate state or checkpoints and does not apply a transition.

## F5 — bounded-retry-authority

`src/general_execution/retry_authority.py` defines a deterministic bounded retry decision contract.

Every mechanical retry/reproduction is bound to:

- an explicit `RetryPolicy`;
- an external authority reference + SHA-256 digest;
- an exact `FailureObservation`;
- an immutable failure-evidence digest.

Frozen semantics:

- `network_timeout`: at most 2 automatic retries, then diagnosis;
- `provider_throttled`: at most 3 automatic retries with capped exponential backoff, then diagnosis;
- `deterministic_assertion`: no retry, diagnosis;
- `unknown_failure`: exactly one independent reproduction, then diagnosis;
- `cost_boundary`: immediate `stop`; no automatic retry and no human authority is invented;
- `security_boundary`: human gate;
- `authority_boundary`: human gate.

A `RetryDecision`:

- carries bounded authority evidence only when it actually authorizes retry/reproduction;
- cannot grant transport authority;
- cannot mix automatic retry, independent reproduction, diagnosis, stop, or human-gate authority;
- cannot carry retry authority into diagnosis/stop;
- cannot carry mechanical retry authority into a human gate;
- fails closed when counters exceed their declared budgets.

The policy does not execute a retry, sleep, call a provider, invoke DI, mutate portfolio state, or create human authority.

## Focused executable verification

The Wave 4 logic was reproduced in an isolated Python package using the same contract logic and the canonical F1/F2 dependencies.

Commands:

```text
python3 -m compileall -q general_execution tests
PYTHONPATH=. pytest -q tests/test_portfolio_persistence.py tests/test_retry_authority.py
```

Observed result:

```text
compileall: PASS
36 passed in 0.15s
```

Coverage includes:

- state snapshot round-trip;
- generation-zero restart;
- atomic state+checkpoint commit;
- latest checkpoint recovery after restart;
- stale CAS rejection;
- generation skip rejection;
- predecessor rejection;
- checkpoint identity/generation/state binding;
- transactional rollback on checkpoint conflict;
- snapshot/head/checkpoint tamper detection;
- exact two-retry network timeout ceiling;
- bounded/capped throttle backoff;
- deterministic assertion no-retry;
- single independent reproduction for unknown failure;
- evidence binding for failure observations;
- immediate cost-boundary stop;
- security/authority human gates;
- transport-authority prohibition;
- mechanical authority artifact requirement.

## Public API verification

The actual branch `general_execution/__init__.py` was inspected after implementation.

All required Wave 4 symbols are exported, including:

- `DurablePortfolioHead`
- `PortfolioPersistenceError`
- `PortfolioRecoveryReport`
- `SqlitePortfolioHeadStore`
- `deserialize_portfolio_snapshot`
- `portfolio_snapshot`
- `recover_portfolio_after_restart`
- `serialize_portfolio_snapshot`
- `verify_portfolio_recovery`
- `FailureObservation`
- `RetryAuthorityError`
- `RetryDecision`
- `RetryPolicy`
- `decide_retry`

## Verification boundary

The local verification package reproduces the candidate logic but is not a byte-for-byte materialization of the GitHub branch, because the current container still cannot resolve `github.com`.

Therefore the evidence supports:

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = FOCUSED_PASS
F2_EXECUTION_CHECKPOINT = FOCUSED_PASS
F3_TRANSITION_POLICY = FOCUSED_PASS
F4_PORTFOLIO_PERSISTENCE = FOCUSED_REPRODUCTION_PASS
F5_BOUNDED_RETRY_AUTHORITY = FOCUSED_REPRODUCTION_PASS
WAVE_4_FOCUSED_TESTS = 36/36 PASS
FULL_EXACT_BRANCH_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
AUTHORITY_CREATED = false
```

The full exact-branch General Execution regression bank remains a separate promotion gate. This evidence does not authorize merge to `main`.

## Next frontier

The next Build Colony wave is:

```text
asp-transition-engine
```

That is the first frontier allowed to construct a new `PortfolioState` from:

- current durable portfolio state;
- an exact matched transition-policy rule;
- admitted checkpoint/evidence state;
- bounded retry/human-stop decisions.

It must not yet add the external scheduler/wake runtime; that remains the following wave.
