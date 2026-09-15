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

## v0.0.9 invariants

The Session registry does not invent a new lifecycle. It persists and reproduces the existing immutable Session transitions.

The protocol enforces:

- a new Session registry history begins with exactly one `bound` registration;
- every later transition binds the exact predecessor Session digest and monotonically increasing revision;
- `start` reproduces only `bound -> running`;
- `revoke` reproduces only `bound/running -> revoked`;
- `submit_result` is accepted only from a running Session and only when backed by the exact persisted v0.0.8 result handoff;
- `revoked` and `result_submitted` are terminal;
- the current Session head must reproduce from the complete append-only transition history;
- stale competing transitions from the same Session head cannot both commit;
- exact lost-ack replay remains idempotent even after later valid Session transitions;
- changed runner capabilities cannot adopt an existing Session history;
- corrupted head, transition, pending-result, submission, or reconciliation metadata fails closed;
- legacy stores are preserved but are not assigned synthetic historical Session transitions.

The Session registry persists protocol state only. It does not acquire domain verification, integration, approval, or release authority.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and durable lifecycle state; Build Colony keeps engineering evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.9 conformance bank

The repository includes 15 targeted Session-registry tests covering registration and restart recovery, start/revoke lifecycle, terminality, complete history replay, lost-ack idempotency, stale predecessor rejection, durable result-handoff binding, submitted-Session recovery, competing revoke-versus-submit transitions, head/history integrity, runner-capability binding, independent Session heads, and legacy non-synthesis.

## Admission state

v0.0.9 is intentionally stacked on the v0.0.5-v0.0.8 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression can be executed in a complete runner environment.

## Next ceiling

The next highest-value step is a **cross-layer coherence pass** rather than another persistence primitive: prove that logical Session state, capacity state, durable head, reconciliation, pending result, and result submission cannot disagree across arbitrary restart boundaries.

## Status

**v0.0.9 durable logical Session registry: stacked implementation candidate under validation.**
