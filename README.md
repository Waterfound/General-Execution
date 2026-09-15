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
- **v0.0.7 — Post-Restart Provider Reconciliation:** deterministic source-to-target reconciliation plans for recovered leases, provider-outcome/revocation resolution, atomic CAS commit, and idempotent replay. See [`docs/v0.0.7-recovery-reconciliation.md`](docs/v0.0.7-recovery-reconciliation.md).

## v0.0.7 invariants

A recovered `in_flight_unknown` lease stays occupied until one explicit resolution is proven. Reconciliation never infers provider state from coordinator restart, silence, elapsed time, or local timeout.

The core enforces:

- the complete source durable snapshot is embedded in each reconciliation plan;
- the exact recovered lease must still be active in that source snapshot;
- provider outcomes must reproduce through the existing physical-outcome and capacity-release protocols;
- Session revocation must already be explicit and must own the exact recovered lease;
- a target snapshot is a direct durable successor adding exactly one release transition;
- source and target are re-verified even during idempotent lost-ack replay;
- the v0.0.6 SQLite CAS adapter admits only one canonical successor from a recovered head;
- competing provider-outcome and revocation plans cannot both become canonical;
- completed physical outcomes release occupancy but do not automatically submit the logical Session result.

Reconciliation resolves execution occupancy. It does not gain application-domain verification, integration, release, or consensus authority.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, recovery state, persistence, and reconciliation protocol; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.7 conformance bank

The repository includes reconciliation tests for provider-outcome resolution, durable-head advancement, idempotent replay, explicit revocation, unrevoked-Session rejection, recovered-lease mismatch, foreign physical outcomes, competing outcome/revocation plans, stale-plan rejection, completed-outcome capacity release without automatic Session submission, receipt consistency, and release-digest consistency.

## Admission state

v0.0.7 is intentionally stacked on the v0.0.5 and v0.0.6 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

After the stacked line is admitted, the next high-value milestone is **provider reattachment semantics**: allow a concrete provider to report the status of an already-dispatched `provider_invocation_id` after restart without turning status polling into execution authority.

## Status

**v0.0.7 recovery reconciliation: stacked implementation candidate under validation.**
