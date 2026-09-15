# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> logical Session
  -> physical authorization + capacity
  -> durable recovery context / provider identity
  -> cold bootstrap + reattachment
  -> physical reconciliation
  -> explicit durable logical Session settlement
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel**
- **v0.0.2 — Provider-neutral Adapter Contract**
- **v0.0.3 — Physical Failure Semantics**
- **v0.0.4 — Capacity & Lease Semantics**
- **v0.0.5 — Durable Head & Restart Recovery**
- **v0.0.6 — SQLite Durable Head Persistence**
- **v0.0.7 — Post-Restart Provider Reconciliation**
- **v0.0.8 — Provider Reattachment Semantics**
- **v0.0.9 — Reattachable Reference Provider**
- **v0.0.10 — Durable Store Reopen Rehearsal**
- **v0.0.11 — Durable Recovery Context + Cold Bootstrap**
- **v0.0.12 — Cross-Store Cut-Point Failure Matrix**
- **v0.0.13 — Durable Logical Session Settlement**
- **v0.0.14 — Cold Lifecycle Settlement Integration:** four-store cold recovery through physical reconciliation and separately authorized durable logical result submission. See [`docs/v0.0.14-cold-lifecycle-settlement.md`](docs/v0.0.14-cold-lifecycle-settlement.md).

## v0.0.14 lifecycle

The integrated reference lifecycle uses four distinct durable stores:

```text
running Session store
  -> recovery context store
  -> canonical capacity store
  -> provider identity/status store
```

`prepare_reference_cold_lifecycle(...)` makes the running logical Session durable before physical work becomes externally recoverable.

`resume_reference_completed_physical_settlement(...)` later receives only the four filesystem paths. It cold-bootstraps the execution context, reattaches the provider, admits a completed physical outcome and reconciles capacity.

At that cut point:

```text
physical = settled_terminal_reconciliation
logical Session = running
```

No logical submission has happened.

## Explicit post-reconciliation settlement

`settle_reference_reconciled_result(...)` is a separate caller-authorized operation. It reconstructs the completed result from durable evidence rather than trusting an in-memory result object:

```text
recovery-context anchor
  + durable terminal provider observation
  + canonical physical release
  -> re-admitted physical outcome
  -> exact ResultEnvelope
  -> v0.0.13 durable Session settlement
```

Exact replay after a lost logical-settlement acknowledgement is idempotent.

The core invariant remains:

```text
physical completion != logical result submission
```

## Lifecycle states

`assess_reference_logical_lifecycle(...)` derives the combined state from stores only:

- `physical_pending_session_running`
- `physical_settled_session_running`
- `logical_result_submitted`
- `logical_revoked`

A logical terminal state appearing before the integrated physical lifecycle is settled is treated as an integrity failure in the reference lifecycle.

When the logical state is `result_submitted`, the persisted result must equal the result reconstructed from the canonical reconciled physical outcome.

## Crash boundaries now covered

The candidate stack has explicit recovery semantics for:

- coordinator restart with in-flight work;
- provider `not_found` versus `running` versus terminal status;
- terminal provider state before capacity reconciliation;
- reconciliation CAS committed with acknowledgement lost;
- completed physical outcome with logical Session still running;
- logical result settlement committed with acknowledgement lost.

## Authority boundary

General Execution persists execution mechanics and explicitly authorized Session transitions. It does not validate application-domain correctness, choose whether a result should be accepted, integrate changes, or approve release.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.14 conformance bank

The repository includes durable running-Session preparation, cold completed physical reconciliation without logical submission, explicit durable post-reconciliation result settlement, lost-ack logical replay, premature settlement rejection, missing durable Session rejection, revocation winning over later result settlement, logical-row corruption detection, distinct four-store enforcement, and deterministic full lifecycle reproduction across fresh paths.

## Admission state

v0.0.14 remains stacked above the v0.0.5-v0.0.13 candidate line. Canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The remaining high-value protocol work is now narrower: **retry/cancellation cold-lifecycle integration and multi-session concurrency across the same stores**. After those gates, additional local protocol code is likely to have sharply diminishing returns; the next evidence step becomes a complete-runner full regression and a concrete external provider transport.

## Status

**v0.0.14 Cold Lifecycle Settlement Integration: stacked implementation candidate under validation.**
