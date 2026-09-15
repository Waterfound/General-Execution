# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable capacity lease
  -> durable dispatch intent
  -> live dispatch permit
  -> external provider
  -> observation / receipt
  -> durable capacity release
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger. See [`docs/v0.0.1-kernel.md`](docs/v0.0.1-kernel.md).
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate. See [`docs/v0.0.2-reference-adapter.md`](docs/v0.0.2-reference-adapter.md).
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit. See [`docs/v0.0.3-physical-failure-semantics.md`](docs/v0.0.3-physical-failure-semantics.md).
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering. See [`docs/v0.0.4-capacity-lease-semantics.md`](docs/v0.0.4-capacity-lease-semantics.md).
- **v0.0.5 — Durable Head & Restart Recovery:** SQLite-backed canonical capacity heads, transactional CAS, replay-verified snapshots, and unresolved in-flight lease recovery. See [`docs/v0.0.5-durable-restart-recovery.md`](docs/v0.0.5-durable-restart-recovery.md).
- **v0.0.6 — Durable Dispatch Intent & Ambiguity Recovery:** durable outbox state, crash-safe submission ambiguity, live capacity-bound transport permits, and fail-closed restart reconciliation. See [`docs/v0.0.6-durable-dispatch-intent.md`](docs/v0.0.6-durable-dispatch-intent.md).

## v0.0.6 invariants

An active physical authorization is not enough to justify remote submission after a crash. General Execution now durably distinguishes:

```text
PREPARED -> SUBMISSION_UNKNOWN -> OBSERVED
```

`PREPARED` means the intent exists durably but transport has not begun. `SUBMISSION_UNKNOWN` is persisted before a future provider side effect is allowed and survives restart as ambiguity. `OBSERVED` means native provider evidence has been admitted and bound to the exact authorization.

The core enforces:

- one durable dispatch intent per active capacity lease;
- immutable runner / lease / Session / authorization / invocation lineage;
- transactional compare-and-swap intent transitions;
- persisted `intent_id`, `runner_id`, `lease_id`, state digest and revision must reconcile with canonical state;
- restart recovery scans and validates all durable rows so metadata corruption cannot hide an ambiguous invocation;
- `SUBMISSION_UNKNOWN` recovers as `reconcile_provider`, never blind re-submission;
- recovery fabricates zero provider outcomes;
- `DispatchPermit` explicitly has `transport_authority = false`;
- only `LiveDispatchPermit` is eligible for a future transport boundary;
- a live permit binds the exact current capacity-state digest and generation;
- Session revocation / capacity release invalidates an earlier live permit;
- even unrelated capacity-generation change makes a live permit stale and requires revalidation;
- late provider evidence may still be recorded because observation is evidence, not new execution authority.

There is still no wall-clock lease expiry and no concrete remote transport in the core.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.6 evidence

The branch adds a 14-scenario focused conformance bank spanning prepared/ambiguous/observed restart states, no-blind-resubmit recovery, live-permit binding, revocation invalidation, generation refresh, stale CAS, provider-outcome closure, serialized-state tampering, row-metadata reconciliation, hidden-row recovery, and explicit non-authority of the durable dispatch permit.

The implementation has also received static API/import review in-chat without consuming GitHub Actions. A full external pytest execution has not been claimed for v0.0.6 in this environment.

## Next ceiling

The next highest-value boundary is **provider idempotency & reconciliation**.

A local SQLite transaction cannot be atomic with an arbitrary remote provider side effect. Before adding a real remote adapter, General Execution should define and prove a provider-neutral reconciliation contract keyed by the stable invocation identity that can distinguish at least:

- definitively absent / never accepted;
- accepted or currently running;
- terminal with retrievable evidence;
- provider state still unknown.

Any re-submission path must be explicitly idempotent or supported by provider evidence that proves absence. `SUBMISSION_UNKNOWN` must never degrade into blind retry merely because time passed or the coordinator restarted.

## Status

**v0.0.6 Durable Dispatch Intent & Ambiguity Recovery: implementation candidate complete in branch; static boundary review complete; full external pytest execution remains unclaimed.**
