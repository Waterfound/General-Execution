# Durable Execution Wave 4 — Portfolio Persistence and Bounded Retry Authority Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 4 candidate head before this evidence commit:

```text
7893d18ce6bfbecf13a5551ad3816a38a052971a
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

## Implemented contracts

### portfolio-persistence

`src/general_execution/portfolio_persistence.py` adds a dedicated durable head for the machine-readable portfolio.

The store:

- persists the exact canonical `PortfolioState` snapshot;
- binds state digest, generation, snapshot digest, and portfolio identity;
- uses SQLite `BEGIN IMMEDIATE` plus compare-and-swap;
- requires initialization at generation zero;
- requires every commit to advance exactly one generation;
- requires `previous_state_digest` to equal the current canonical state digest;
- rejects stale writers;
- rejects cross-portfolio commits;
- detects snapshot and metadata tampering;
- can be reopened by a fresh process without chat history.

This is persistence only. It does not select or apply Active/Secondary/Passive transitions.

### bounded-retry-authority

`src/general_execution/retry_authority.py` introduces a deterministic retry policy bound to an external authority artifact.

Initial policy semantics:

- `network_timeout`: bounded automatic retry, default ceiling 2;
- `provider_throttled`: bounded automatic retry with capped exponential backoff;
- `deterministic_assertion`: no retry, diagnose;
- `unknown_failure`: one independently authorized reproduction, then diagnose;
- `cost_boundary`: human gate;
- `security_boundary`: human gate;
- `authority_boundary`: human gate.

A retry decision:

- is bound to the exact policy digest and failure observation digest;
- cannot grant transport authority;
- cannot mix retry, independent-reproduction, diagnosis, and human-gate authority flags;
- cannot smuggle an authority boundary into an ordinary transient failure;
- fails closed when the retry/reproduction budget is exhausted.

The policy does not itself execute a retry, sleep, call a provider, invoke DI, or mutate portfolio state.

## Independent focused reproduction

A local isolated verification environment was constructed from the exact committed Wave 4 modules plus the exact F1 canonical/portfolio-state dependencies.

Commands:

```text
python -m compileall -q general_execution tests
python -m pytest -q tests/test_portfolio_persistence.py tests/test_retry_authority.py
```

Observed results:

```text
compileall: PASS
27 passed in 0.12s
```

The Python runtime emitted an unrelated artifact-tool spreadsheet warmup warning on stderr before test execution. Both compileall and pytest returned exit code 0, and the warning did not originate from or affect General Execution code.

## Public API verification

The actual branch `general_execution/__init__.py` was inspected after implementation.

All 11 Wave 4 public symbols are exported:

- `DurablePortfolioHead`
- `PortfolioPersistenceError`
- `SqlitePortfolioHeadStore`
- `deserialize_portfolio_snapshot`
- `portfolio_snapshot`
- `serialize_portfolio_snapshot`
- `FailureObservation`
- `RetryAuthorityError`
- `RetryDecision`
- `RetryPolicy`
- `decide_retry`

## Verification boundary

Current evidence supports:

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = FOCUSED_PASS
F2_EXECUTION_CHECKPOINT = FOCUSED_PASS
F3_TRANSITION_POLICY = FOCUSED_PASS
F4_PORTFOLIO_PERSISTENCE = FOCUSED_PASS
F5_BOUNDED_RETRY_AUTHORITY = FOCUSED_PASS
WAVE_4_FOCUSED_TESTS = 27/27 PASS
FULL_REPOSITORY_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
AUTHORITY_CREATED = false
```

The full General Execution regression bank remains a separate promotion gate. This evidence does not authorize merge to `main`.

## Next frontier

The next Build Colony wave is:

```text
asp-transition-engine
```

That is the first frontier allowed to construct a new `PortfolioState` from:

- current durable portfolio state;
- an exact matched transition-policy rule;
- admitted evidence/checkpoint state;
- bounded retry/human-stop decisions.

It must not yet add the external scheduler/wake runtime; that remains the following wave.
