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
  -> provider reattachment probe
  -> durable reference provider registry / bridge
  -> durable-store reopen rehearsal
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
- **v0.0.8 — Provider Reattachment Semantics:** deterministic client-generated reattachment keys, status-only probes, conservative `running` / `not_found` handling, and terminal physical-outcome admission. See [`docs/v0.0.8-provider-reattachment.md`](docs/v0.0.8-provider-reattachment.md).
- **v0.0.9 — Reattachable Reference Provider:** a filesystem-backed reference job registry plus protocol bridge proving durable provider identity, restart lookup, immutable terminal status, and handoff into v0.0.8/v0.0.7. See [`docs/v0.0.9-reattachable-reference-provider.md`](docs/v0.0.9-reattachable-reference-provider.md).
- **v0.0.10 — Durable Store Reopen Rehearsal:** a deterministic QA scenario reopening durable capacity/provider stores while the immutable execution context is explicitly caller-retained. See [`docs/v0.0.10-store-reopen-rehearsal.md`](docs/v0.0.10-store-reopen-rehearsal.md).

## v0.0.10 evidence boundary

v0.0.10 does **not** claim a cold coordinator restart. `ExecutionSpec`, runner registry, dispatch plan, logical Session, and physical authorization remain available from the caller during the store-reopen rehearsal. Every report therefore records:

```text
context_mode = caller_retained
```

Within that boundary, the rehearsal proves:

- the persisted capacity head reproduces exactly after reopen;
- one `in_flight_unknown` lease is reconstructed from durable capacity state;
- the same deterministic provider key/job identity survives provider-registry reopen;
- provider `running` is admitted as `keep_running` with no outcome and no capacity release;
- terminal provider state is persisted and admitted through v0.0.8 as a physical outcome;
- v0.0.7 reconciliation advances the durable capacity head and removes the recovered lease;
- a `timed_out` physical terminal does not create a logical result;
- a `completed` physical terminal exposes a `ResultEnvelope` but leaves the logical Session `running`;
- logical result submission remains a separate explicit `submit_result(...)` operation;
- fresh stores with identical protocol inputs reproduce the same report independent of filesystem path;
- capacity and provider stores are distinct;
- the final rehearsal object rebinds report, recovered lease, physical outcome, result, and reconciliation receipt.

The central authority boundary remains:

```text
physical completion != logical result submission
```

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, recovery state, persistence, reconciliation, provider-status mechanics, and reference rehearsals; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.10 conformance bank

Tests cover timeout reconciliation, completed physical outcome without automatic logical submission, provider terminal persistence, deterministic fresh-store replay, capacity-head reuse rejection, distinct-store enforcement, invalid-mode rejection before mutation, report/component binding, and explicit caller-retained context semantics.

An isolated two-store SQLite harness also confirmed reopen persistence, `keep_running` occupancy, terminal persistence, reconciliation-style CAS, and deterministic report identity. This is targeted evidence, not the full historical repository regression.

## Admission state

v0.0.10 is intentionally stacked on the v0.0.5-v0.0.9 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The next highest-value milestone is **v0.0.11 — Durable Recovery Context**: canonically serialize and reconstruct the `ExecutionSpec`, registry, dispatch plan, logical Session, and physical authorization so a rehearsal can discard all volatile protocol objects and perform a true cold coordinator restart.

## Status

**v0.0.10 durable store reopen rehearsal: stacked implementation candidate under validation.**
