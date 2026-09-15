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
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger. See [`docs/v0.0.1-kernel.md`](docs/v0.0.1-kernel.md).
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate. See [`docs/v0.0.2-reference-adapter.md`](docs/v0.0.2-reference-adapter.md).
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit. See [`docs/v0.0.3-physical-failure-semantics.md`](docs/v0.0.3-physical-failure-semantics.md).
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering. See [`docs/v0.0.4-capacity-lease-semantics.md`](docs/v0.0.4-capacity-lease-semantics.md).
- **v0.0.5 — Durable Head & Restart Recovery:** canonical capacity snapshots, durable-head continuity, strict state decoding, and conservative recovery of in-flight leases. See [`docs/v0.0.5-durable-restart-recovery.md`](docs/v0.0.5-durable-restart-recovery.md).

## v0.0.5 invariants

A `DurableCapacitySnapshot` binds one exact replayable `RunnerCapacityState` to a durable head containing runner identity, generation, state digest, payload digest, and optional previous-head digest.

The core enforces:

- canonical JSON serialization of capacity state;
- strict schema versions during reconstruction;
- full capacity replay before a stored snapshot is admitted;
- optional exact-head matching through `expected_head_digest`;
- append-only durable-head continuity across later snapshots;
- no backward generation when a previous durable head is supplied;
- no automatic capacity release during restart recovery;
- active leases return as `in_flight_unknown` and retain their slots;
- clean recovery is possible only when no active leases remain.

The persistence backend is still responsible for atomically maintaining one canonical durable head. General Execution defines the protocol state and verification rules, not the storage engine.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, and recovery state; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.5 conformance bank

The repository includes recovery tests for deterministic round-trip, exact-head reload, in-flight lease preservation, clean restart after explicit release, outdated-head rejection, malformed payload rejection, schema-version rejection, wrong-runner rejection, durable successor continuity, backward-generation rejection, previous-head mismatch, deterministic serialization, and recovery-report consistency.

## Next ceiling

After the v0.0.5 recovery boundary is validated, the next highest-value milestone is a **concrete persistence adapter** that performs atomic canonical-head compare-and-swap and crash-safe replacement while preserving the durable protocol unchanged.

## Status

**v0.0.5 Durable Head & Restart Recovery: implementation candidate under final validation.**
