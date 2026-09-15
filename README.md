# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable recovery / provider state
  -> cold bootstrap
  -> provider reattachment
  -> capacity reconciliation
  -> explicit durable logical Session settlement
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger.
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate.
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit.
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering.
- **v0.0.5 — Durable Head & Restart Recovery:** replayable capacity snapshots and conservative `in_flight_unknown` recovery.
- **v0.0.6 — SQLite Durable Head Persistence:** filesystem-backed canonical-head CAS.
- **v0.0.7 — Post-Restart Provider Reconciliation:** explicit source-to-target recovery plans and atomic reconciliation.
- **v0.0.8 — Provider Reattachment Semantics:** deterministic pre-dispatch reattachment keys and conservative status probes.
- **v0.0.9 — Reattachable Reference Provider:** durable provider identity/status control plane.
- **v0.0.10 — Durable Store Reopen Rehearsal:** store reopen QA with execution context explicitly caller-retained.
- **v0.0.11 — Durable Recovery Context + Cold Bootstrap:** stores-only reconstruction of runner, Spec, registry, plan, Session and physical authorization followed by true cold recovery.
- **v0.0.12 — Cross-Store Cut-Point Failure Matrix:** exact durable-state reconstruction across context, capacity, provider-terminal and reconciliation boundaries, including lost post-CAS acknowledgement.
- **v0.0.13 — Durable Logical Session Settlement:** filesystem-backed, idempotent `running -> result_submitted | revoked` settlement with exact result persistence and lost-ack recovery. See [`docs/v0.0.13-durable-session-settlement.md`](docs/v0.0.13-durable-session-settlement.md).

## v0.0.13 logical state machine

The logical Session now has a durable one-way state graph:

```text
running -> result_submitted
       \-> revoked
```

`SQLiteSessionSettlementStore` first registers the exact running Session. Terminal settlement is then an explicit caller operation using the existing `submit_result(...)` or `revoke_session(...)` semantics.

The store never turns provider completion into logical submission automatically.

```text
physical completion != logical result submission
```

### Result settlement

A result settlement persists both the exact terminal `ExecutionSession` and the complete `ResultEnvelope`.

The store rejects:

- submission without prior durable running registration;
- a result that is not bound to the exact source Session;
- a different result after `result_submitted` became canonical;
- result submission after durable revocation;
- a forged source binding even when it produces the same `session_id`.

### Revocation settlement

Explicit revocation is also durable. Once `revoked` is canonical, later result submission conflicts; once `result_submitted` is canonical, later revocation conflicts.

### Lost acknowledgement and concurrency

Settlement uses a filesystem-backed SQLite `BEGIN IMMEDIATE` transaction and exact record-digest comparison.

If a terminal commit succeeded but its acknowledgement was lost, exact replay returns an idempotent receipt. Concurrent identical result submissions converge on one canonical record; competing result-versus-revocation writers produce at most one terminal winner.

### Integrity

Records use canonical JSON with strict nested Session/result schemas. Row metadata binds the Session ID, source/current Session digests, terminal state and complete record digest. Metadata/payload disagreement is rejected.

## Authority boundary

Durable settlement stores an explicit logical decision; it does not decide whether application evidence is correct, verified, integrable, releasable, or otherwise approved.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.13 conformance bank

The repository includes running registration/reopen, idempotent registration, durable result submission, lost-ack replay, conflicting result rejection, durable revocation, result/revocation mutual exclusion, concurrent identical-result convergence, concurrent result-versus-revocation single-winner behavior, missing-source rejection, same-session-ID binding substitution rejection, canonical round-trip, strict nested schemas, store metadata corruption, row digest corruption, and filesystem-only persistence.

## Admission state

v0.0.13 remains stacked above the v0.0.5-v0.0.12 candidate line. Canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The next highest-value boundary is **full cold lifecycle settlement integration**: persist the running Session before physical work becomes recoverable, reconstruct it after cold restart, reconcile a recovered completed physical outcome, and then explicitly persist `result_submitted`. Cut points immediately before and after logical settlement must remain distinguishable and idempotently recoverable.

## Status

**v0.0.13 Durable Logical Session Settlement: stacked implementation candidate under validation.**
