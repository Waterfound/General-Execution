# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> durable logical Session lifecycle
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
  -> cross-layer coherence
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
- **v0.0.9 — Durable Logical Session Registry:** append-only persistence and replay of the complete `bound -> running -> revoked/result_submitted` Session lifecycle. See [`docs/v0.0.9-durable-session-registry.md`](docs/v0.0.9-durable-session-registry.md).
- **v0.0.10 — Cross-Layer Coherence:** classify and guard consistency between logical Session, capacity history, durable head, reconciliation, pending result, and result submission. See [`docs/v0.0.10-cross-layer-coherence.md`](docs/v0.0.10-cross-layer-coherence.md).

## v0.0.10 invariants

`ExecutionCoherenceReport` distinguishes `coherent`, `recovery_required`, `legacy_untracked`, and `inconsistent` state instead of treating every restart mismatch as corruption.

The protocol enforces:

- `bound + physical history` is a recoverable missed durable `start`, including reserve/release history with no active lease;
- a missing Session registry over pre-existing execution history remains legacy state and receives no synthetic history;
- `running + session_revoked capacity release` requires a durable revoke catch-up;
- a completed physical release without the complete durable logical-result handoff fails closed;
- `running + pending result` and `running + persisted submission` expose the exact next mechanical recovery action;
- `revoked + active lease`, `result_submitted + active lease`, orphan result state, and contradictory handoff state are inconsistent;
- `CoherentSQLiteSessionRegistry` adds atomic cross-layer guards inside the same SQLite write transaction;
- a fresh Session registration cannot be placed over existing physical capacity history;
- exact lost-ack replay of an already-canonical transition remains idempotent even after later physical work appears.

Cross-layer coherence remains execution-state consistency. It does not acquire evidence-verification, integration, approval, or release authority.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and durable lifecycle state; Build Colony keeps engineering evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.10 conformance bank

The repository contains 17 targeted coherence tests covering physical-history recovery, atomic registration guards, legacy non-synthesis, revocation ordering, result-handoff recovery, coherent final submission, inconsistent combinations, idempotent replay, deterministic reports, revocation-release catch-up, and completed-release-without-handoff fail-closed behavior.

The 17-case bank is present in the candidate branch; it is not described as 17/17 executed evidence until the complete stacked branch is materialized in a runnable environment.

## Admission state

v0.0.10 is intentionally stacked on the v0.0.5-v0.0.9 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression can be executed in a complete runner environment.

## Next ceiling

After the stacked line receives its complete regression, the next useful boundary is a bounded recovery driver that consumes only `recovery_required` reports and applies one explicitly named mechanical catch-up action at a time. It must refuse `legacy_untracked` and `inconsistent` state.

## Status

**v0.0.10 cross-layer coherence: stacked implementation candidate under validation.**
