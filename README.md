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
  -> durable capacity head
  -> restart recovery
  -> SQLite canonical-head persistence
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger. See [`docs/v0.0.1-kernel.md`](docs/v0.0.1-kernel.md).
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate. See [`docs/v0.0.2-reference-adapter.md`](docs/v0.0.2-reference-adapter.md).
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit. See [`docs/v0.0.3-physical-failure-semantics.md`](docs/v0.0.3-physical-failure-semantics.md).
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering. See [`docs/v0.0.4-capacity-lease-semantics.md`](docs/v0.0.4-capacity-lease-semantics.md).
- **v0.0.5 — Durable Head & Restart Recovery:** canonical capacity snapshots, durable-head continuity, strict state decoding, and conservative recovery of in-flight leases. See [`docs/v0.0.5-durable-restart-recovery.md`](docs/v0.0.5-durable-restart-recovery.md).
- **v0.0.6 — SQLite Durable Head Persistence:** filesystem-backed SQLite storage, atomic canonical-head compare-and-swap, exact in-transaction verification, and idempotent replay after lost acknowledgement. See [`docs/v0.0.6-sqlite-persistence.md`](docs/v0.0.6-sqlite-persistence.md).

## v0.0.6 invariants

`SQLiteDurableHeadStore` persists one canonical durable snapshot per runner while preserving the v0.0.5 protocol as the source of truth.

The adapter enforces:

- one canonical row per `runner_id`;
- `BEGIN IMMEDIATE` write serialization plus exact expected-head comparison;
- full v0.0.5 snapshot verification before storage;
- exact candidate verification inside the same SQLite transaction before commit;
- stale writers cannot replace a later canonical head;
- exact replay of an already-committed snapshot is idempotent;
- stored metadata must reproduce the serialized snapshot;
- runner capability changes cannot silently adopt an existing head;
- WAL journaling and `synchronous=FULL` for the reference file-backed adapter;
- `:memory:` is rejected because this milestone is specifically about restart durability.

SQLite supplies durable atomic storage. It does not gain authority over execution, evidence, verification, integration, or release decisions.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, recovery state, and persistence protocol; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.6 evidence

The repository includes persistence tests for restart reload, successor commit, concurrent two-writer CAS, idempotent replay, stale-head rejection, predecessor requirements, rollback rejection, runner-capability binding, independent runner heads, stored metadata consistency, store-schema checks, initial expected-head handling, and receipt schema validation.

A separate local SQLite harness confirmed one-winner concurrent CAS, stale-writer rejection, idempotent replay, and persistence after close/reopen without GitHub Actions.

## Admission state

v0.0.6 is intentionally stacked on the v0.0.5 candidate branch. The canonical `main` remains at v0.0.4 until the full historical repository regression for v0.0.5 can be executed in a complete runner environment.

## Next ceiling

After v0.0.5 and the stacked v0.0.6 persistence adapter are admitted, the next high-value boundary is **post-restart provider reconciliation**: match a persisted `in_flight_unknown` lease with later provider evidence without creating duplicate canonical execution.

## Status

**v0.0.6 SQLite persistence: stacked implementation candidate under validation.**
