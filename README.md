# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable capacity lease
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

## v0.0.5 invariants

Each runner has at most one durable canonical capacity head. A durable commit must extend that head by exactly one replayable transition and must match the current `expected_state_digest` inside the same SQLite write transaction.

A coordinator restart does not release capacity and does not imply any provider outcome. Active leases recover as `in_flight_unresolved` with the same slot, Session, authorization and invocation identity.

The core enforces:

- durable snapshot digest and native capacity-state digest both verify on reload;
- full capacity history replays against the exact `RunnerCapabilities`;
- persisted metadata must agree with reconstructed snapshot state;
- capability drift fails closed;
- stale competing writers cannot both advance one durable head;
- a commit cannot skip generations or replace canonical transition history;
- restart recovery fabricates zero physical outcomes and zero capacity releases;
- a recovered active lease remains capacity-consuming until real evidence or explicit Session revocation produces the native release transition.

There is still no wall-clock lease expiry in the core.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.5 evidence

The durable-recovery candidate adds 10 focused conformance scenarios covering snapshot round-trip, restart-stable reload, active-lease survival, post-restart capacity blocking, real outcome release after restart, stale CAS across independent store connections, generation-skip rejection, snapshot and metadata tamper detection, capability drift, and idempotent initialization.

An isolated local SQLite/CAS harness additionally exercised `genesis -> reserve -> restart -> stale-CAS rejection -> real release -> second restart` successfully without GitHub Actions.

## Next ceiling

The next highest-value boundary is **durable dispatch intent & ambiguity recovery**.

v0.0.5 can recover that a lease is still active, but after a crash it intentionally cannot infer whether the external provider actually received the invocation. Before adding concrete remote transport, General Execution should durably bind a dispatch intent to the active lease and distinguish at least:

- prepared but not submitted;
- submission attempted but provider acceptance unknown;
- provider identity/receipt observed.

Restart recovery must never blindly re-submit an ambiguous invocation. Concrete remote transport should be introduced only after this outbox/reconciliation boundary is proven.

## Status

**v0.0.5 Durable Head & Restart Recovery: implementation candidate locally validated at the SQLite/CAS boundary.**
