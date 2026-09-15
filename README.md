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
  -> post-restart reconciliation
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
- **v0.0.7 — Post-Restart Provider Reconciliation:** exact recovered-lease/provider-outcome binding plus atomic reconciliation-record and durable-head commit. See [`docs/v0.0.7-restart-reconciliation.md`](docs/v0.0.7-restart-reconciliation.md).

## v0.0.7 invariants

A recovered `in_flight_unknown` lease can be resolved only by an admitted physical outcome that reproduces from the exact `ExecutionSpec`, registry, plan, Session, runner, authorization, and recovered lease.

The core enforces:

- reconciliation candidates rerun physical-outcome verification before persistence;
- recovered lease, authorization, outcome, receipt, release, and successor durable head are bound into one record;
- changing the Session context or provider outcome invalidates the candidate;
- SQLite stores the reconciliation record and successor durable head in one transaction;
- one physical authorization has at most one canonical reconciliation per runner;
- conflicting outcomes for one authorization cannot both become canonical;
- stale source heads are rejected unless the exact reconciliation was already committed;
- lost-ack replay is idempotent even after later durable heads advance;
- failed physical outcomes preserve retry lineage after capacity release;
- completed physical outcomes release capacity but do not implicitly submit the logical Session result;
- the v0.0.6 SQLite metadata store migrates transactionally from schema v1 to v2.

Persistence and reconciliation remain execution mechanics. They do not acquire evidence-verification, integration, or release authority.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, restart state, persistence, and reconciliation; Build Colony keeps engineering evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.7 conformance bank

The repository includes targeted reconciliation tests for failed and completed outcomes, retry lineage, foreign authorization rejection, record tamper detection, changed Session context, changed provider outcome, atomic record/head persistence, lost-ack idempotency, conflicting outcomes, stale source heads, replay after later head advancement, v1-to-v2 store migration, and persistence across reopen.

## Admission state

v0.0.7 is intentionally stacked on the v0.0.5 and v0.0.6 candidates. The canonical `main` remains at v0.0.4 until the full historical repository regression can be executed in a complete runner environment.

## Next ceiling

The next high-value boundary is **durable logical-session/result recovery**: a completed reconciled physical outcome must survive another coordinator restart before logical result submission without being forgotten or double-submitted.

## Status

**v0.0.7 restart reconciliation: stacked implementation candidate under validation.**
