# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> capacity lease
  -> durable recovery context
  -> durable capacity head
  -> provider identity / status
  -> restart recovery
  -> provider reattachment
  -> reconciliation
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger.
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate.
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit.
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering.
- **v0.0.5 — Durable Head & Restart Recovery:** replayable capacity snapshots and conservative `in_flight_unknown` recovery.
- **v0.0.6 — SQLite Durable Head Persistence:** filesystem-backed canonical-head CAS.
- **v0.0.7 — Post-Restart Provider Reconciliation:** explicit source-to-target recovery plans and atomic reconciliation.
- **v0.0.8 — Provider Reattachment Semantics:** deterministic pre-dispatch reattachment keys and conservative status probes.
- **v0.0.9 — Reattachable Reference Provider:** durable provider identity/status control plane.
- **v0.0.10 — Durable Store Reopen Rehearsal:** two-store reopen QA with execution context explicitly caller-retained.
- **v0.0.11 — Durable Recovery Context:** immutable reconstruction of Spec, registry, plan, Session, physical authorization, runner definition, and the lease anchor required for a true cold coordinator bootstrap. See [`docs/v0.0.11-durable-recovery-context.md`](docs/v0.0.11-durable-recovery-context.md).

## v0.0.11 invariants

`DurableRecoveryContext` contains the complete typed execution identity needed to re-enter the existing recovery protocols after volatile coordinator memory is gone.

The context binds:

- exact `ExecutionSpec`;
- exact `RunnerRegistry` and selected `RunnerCapabilities`;
- deterministic `DispatchPlan`;
- running `ExecutionSession`;
- exact `PhysicalAttemptAuthorization`, including retry predecessor bindings;
- an anchor `DurableCapacitySnapshot` containing the active lease;
- exact recovered lease ID and digest.

The serialized form is canonical JSON with strict nested schema versions. Loading reconstructs typed objects and re-runs existing plan, dispatch-request, capacity replay, authorization, and lease bindings.

### Anchor, not frozen head

The recovery context is anchored to the snapshot at which the attempt became recoverable. A later current capacity head may contain unrelated transitions from other slots while the same lease stays active.

The context remains valid only when the current capacity history extends the full anchor transition prefix and the exact lease is still active and unchanged. This keeps long-running work recoverable under `max_parallelism > 1` without weakening replay guarantees.

### Safe persistence order

The intended order is:

```text
reserve candidate in memory
  -> build anchor snapshot + recovery context
  -> persist recovery context
  -> commit durable capacity head
  -> register provider identity
```

A crash after context persistence but before capacity commit leaves an **orphan context**, which cold bootstrap ignores. Once a recoverable active capacity head exists, its context was already durable.

### Cold bootstrap

`bootstrap_active_recovery_contexts(...)` starts from only the recovery-context store and durable capacity-head store. It can rediscover runner definitions from self-contained anchor contexts, load the current canonical capacity head, and reconstruct active bindings.

Contexts for already-released leases are historical and ignored. A context that still maps to an active authorization must verify completely or bootstrap fails closed.

## Authority boundary

Recovery context preserves identity; it does not create permission to retry, release capacity, submit a logical result, verify application evidence, integrate changes, or approve release.

The existing boundary remains:

```text
physical completion != logical result submission
```

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.11 conformance bank

The repository includes tests for canonical round-trip, exact reconstruction, validity across unrelated capacity-head advancement, lease-removal rejection, strict schema handling, Session-binding changes, context persistence/reopen, idempotent replay, re-anchor conflict, bootstrap reconstruction from stores only, metadata/schema corruption, filesystem-only storage, unknown authorization lookup, safe orphan contexts, and historical released contexts.

## Admission state

v0.0.11 remains stacked above the v0.0.5-v0.0.10 candidate line. Canonical `main` remains at v0.0.4 until the full historical regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The next milestone is a **true cold coordinator restart rehearsal**: persist context first, commit capacity/provider state, discard every original Spec/registry/plan/Session/authorization object, reconstruct exclusively through durable bootstrap, then perform provider status admission and reconciliation.

## Status

**v0.0.11 Durable Recovery Context: stacked implementation candidate under validation.**
