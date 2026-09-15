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

## v0.0.8 invariants

A runner is reattachable only when it already advertised `provider.reattachment.v1` in the capability digest bound into the original physical authorization.

The core enforces:

- the reattachment key is deterministic before dispatch and reconstructable from the recovered lease after restart;
- reattachment cannot be retrofitted by changing runner capabilities after dispatch;
- a status probe contains recovery identity only and cannot start work;
- `running` preserves the existing in-flight lease;
- `not_found` remains inconclusive and does not release capacity, authorize retry, or fabricate failure;
- `terminal` must carry a v0.0.3 physical observation for the same recovered authorization/invocation;
- terminal observations are admitted through the existing physical-outcome protocol before v0.0.7 reconciliation;
- status polling does not gain execution, verification, integration, release, or consensus authority.

A reattachable adapter is expected to pass the deterministic `provider_key` to its provider as the original submit idempotency/lookup key. This removes the crash window between provider acceptance and local persistence of a provider-assigned job identifier.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, recovery state, persistence, reconciliation, and provider-status protocol; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.8 conformance bank

The repository includes tests for deterministic pre-dispatch/post-restart key reconstruction, capability gating, deterministic status probes, `running` and `not_found` preservation, terminal physical-outcome admission into v0.0.7, foreign-observation rejection, key/probe mismatch rejection, status-shape constraints, recovered-lease mismatch, no retroactive reattachment upgrade, and detail-digest validation.

## Admission state

v0.0.8 is intentionally stacked on the v0.0.5-v0.0.7 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

After the stacked line is admitted, the next high-value milestone is a **concrete reattachable provider adapter** that performs initial submit and later status lookup using the same client-generated provider key.

## Status

**v0.0.8 provider reattachment semantics: stacked implementation candidate under validation.**
