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
  -> durable logical result handoff
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
- **v0.0.8 — Durable Logical Result Handoff:** atomically retain a reconciled `ResultEnvelope`, explicitly apply `submit_result`, and persist the resulting logical Session across later restarts. See [`docs/v0.0.8-durable-result-handoff.md`](docs/v0.0.8-durable-result-handoff.md).

## v0.0.8 invariants

A completed physical reconciliation cannot become canonical without preserving the complete logical `ResultEnvelope` in the same transaction.

The protocol enforces:

- `PendingLogicalResult` stores the complete reconciled result, not only its digest;
- pending result and reconciliation are mutually bound by runner, Session, attempt, spec, authorization, reconciliation digest, and result digest;
- a transport failure with no `ResultEnvelope` creates no pending logical result;
- `submit_result` remains the existing explicit Session transition and is not replaced by persistence;
- `LogicalResultSubmission` binds the source running Session and the exact `result_submitted` Session returned by `submit_result`;
- submission persistence is append-only and exact lost-ack replay is idempotent;
- pending and submitted logical state survive separate coordinator restarts;
- missing or inconsistent reconciliation/pending/submission state fails closed;
- SQLite store schema v3 adds durable pending-result and submission registries;
- v2 completed reconciliations without their original full `ResultEnvelope` cannot migrate by digest alone;
- v2 failure-only reconciliations can migrate safely.

The handoff persists protocol state. It does not grant domain verification, integration, approval, or release authority.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and durable lifecycle state; Build Colony keeps engineering evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.8 conformance bank

The repository includes 16 targeted handoff tests covering atomic pending creation, failure-without-pending behavior, restart recovery, exact Session submission, wrong-Session rejection, durable submission recovery, lost-ack replay, absent and inconsistent pending state, metadata consistency, logical failed-result preservation, orphan-pending rejection, fail-closed completed v2 migration, and safe failure-only v2 migration.

## Admission state

v0.0.8 is intentionally stacked on the v0.0.5-v0.0.7 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression can be executed in a complete runner environment.

## Next ceiling

The next high-value milestone is a **durable logical Session registry** covering the complete lifecycle `bound -> running -> revoked/result_submitted`, so clients no longer need to reconstruct the pre-result logical Session after coordinator restart.

## Status

**v0.0.8 durable logical result handoff: stacked implementation candidate under validation.**
