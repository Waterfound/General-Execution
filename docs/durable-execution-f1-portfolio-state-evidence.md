# Durable Execution F1 — Portfolio State Contract Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Code candidate exercised by focused tests:

```text
05d71e9319bfec387b45da43f0032f7a39a4e24e
```

Canonical base:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

The candidate is strictly ahead of the frozen base and does not depend on the divergent experimental `v0.0.14*` or `v0.0.15*` lines.

## Implemented contract

`src/general_execution/portfolio_state.py` introduces:

- `PortfolioState`
- `PortfolioEntry`
- `PortfolioBlocker`
- `WakeCondition`
- canonical JSON serialization;
- strict schema reconstruction;
- deterministic SHA-256 identity;
- monotonic generation/predecessor representation.

The public package surface exports the new contract without changing the existing `0.0.13` release version.

## Frozen invariants

The contract enforces:

- exactly one structural Active slot;
- exactly one structural Secondary slot;
- zero or more canonical-order Passive slots;
- unique `work_id` values across the portfolio;
- Secondary remains `ready`;
- Passive remains `passive`;
- every Passive has at least one blocker and an explicit wake condition;
- Active wake conditions are limited to `waiting_external`;
- `human_gate` requires an explicit authority boundary plus an authorization/authority blocker;
- generation zero has no predecessor;
- later generations require a valid predecessor digest;
- unknown schema fields fail closed;
- duplicate evidence requirements and blockers are rejected.

The object does not grant execution, verification, integration, release, spending, retry, credential, consensus, economics, or destructive-infrastructure authority.

## Focused executable verification

Because the current local runtime cannot resolve `github.com`, a full clone/full-suite run was not available in this execution environment.

A focused isolated regression used the exact candidate:

- `portfolio_state.py`;
- canonical identity implementation from `canonical.py`;
- `tests/test_portfolio_state.py`;
- an API shim exposing exactly the new public names.

Command shape:

```text
python3 -m compileall -q general_execution tests
PYTHONPATH=. pytest -q tests/test_portfolio_state.py
```

Observed result:

```text
24 passed in 0.08s
```

Separately, the actual branch `general_execution/__init__.py` was inspected through GitHub and all nine required portfolio-state public API exports were present.

## Verification boundary

The evidence proves the new F1 contract in isolation and its declared API exposure.

It does **not** yet prove the complete General Execution regression bank against the branch. Therefore:

```text
F0_BASELINE_AUDIT = PASS
F1_CONTRACT_FOCUSED_TESTS = PASS
FULL_REPOSITORY_REGRESSION = NOT_RUN_IN_CURRENT_RUNTIME
MAIN_INTEGRATION = NOT_AUTHORIZED
```

The candidate remains suitable for continued frontier development on its isolated branch, but not for promotion to `main` solely on this focused evidence.

## Next dependency frontier

After this contract, Wave 3 may define independently:

1. `execution_checkpoint`
2. `transition_policy`

Neither may weaken the authority invariants frozen here.
