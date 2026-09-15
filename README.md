# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> capacity lease
  -> external provider
  -> observation / receipt
  -> capacity release
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger. See [`docs/v0.0.1-kernel.md`](docs/v0.0.1-kernel.md).
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate. See [`docs/v0.0.2-reference-adapter.md`](docs/v0.0.2-reference-adapter.md).
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit. See [`docs/v0.0.3-physical-failure-semantics.md`](docs/v0.0.3-physical-failure-semantics.md).
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering. See [`docs/v0.0.4-capacity-lease-semantics.md`](docs/v0.0.4-capacity-lease-semantics.md).

## v0.0.4 invariants

Each runner has a replayable `RunnerCapacityState`. Reserve/release proposals bind to one exact `expected_state_digest`; after one proposal commits, another proposal created from the older snapshot is stale.

A committed `CapacityLeaseGrant` binds the exact runner, slot, logical Session, physical authorization, invocation ID, physical-attempt ordinal, and capacity-state revision.

The core enforces:

- active canonical leases never exceed `RunnerCapabilities.max_parallelism`;
- one logical Session attempt has at most one active canonical physical lease;
- retry capacity is unavailable until the preceding physical attempt has been canonically released;
- a completed predecessor is not a retry source;
- terminal physical outcomes and explicit Session revocation release capacity through auditable transitions;
- capacity state can be replayed from runner genesis;
- capacity transitions can be recorded as `CAPACITY_RESERVED` / `CAPACITY_RELEASED` ledger events.

There is no wall-clock lease expiry in the core. A future durable store must maintain one canonical capacity head per runner and apply the expected-state-digest rule atomically.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.4 evidence

The capacity candidate passed 14 targeted local conformance tests covering capacity exhaustion, deterministic multi-slot allocation, stale reserve/release proposals, retry ordering, Session revocation, competing retry proposals, execution-context binding, state replay, and capacity-ledger recording.

## Next ceiling

The next highest-value boundary is **durable head & restart recovery**: serialize/reload canonical capacity state, replay it after coordinator restart, and reconcile an in-flight lease without fabricating a physical outcome. Concrete remote transport should depend on capacity only after this recovery boundary is proven.

## Status

**v0.0.4 Capacity & Lease Semantics: implementation candidate locally validated.**
