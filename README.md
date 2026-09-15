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
- **v0.0.9 — Reattachable Reference Provider:** a filesystem-backed reference job registry plus protocol bridge proving durable provider identity, restart lookup, immutable terminal status, and end-to-end handoff into v0.0.8/v0.0.7. See [`docs/v0.0.9-reattachable-reference-provider.md`](docs/v0.0.9-reattachable-reference-provider.md).

## v0.0.9 invariants

The v0.0.9 reference provider is a control-plane simulator, not a workload executor. It persists provider identity and status so the reattachment protocol can be exercised across real process/storage reopen boundaries.

The implementation enforces:

- one deterministic reference `job_id` for one v0.0.8 `provider_key`;
- repeated registration of the same exact provider key is idempotent;
- concurrent registration converges on one job identity;
- the durable registry survives close/reopen through filesystem-backed SQLite;
- absent provider keys report `not_found` rather than failure;
- running provider records remain running after coordinator restart;
- the first terminal payload is immutable and exact replay is idempotent;
- terminal payload integrity is checked before it becomes a `ProviderStatusObservation`;
- the terminal observation must carry the deterministic job ID and exact authorization/invocation identity;
- v0.0.8 still performs the strong physical-outcome admission before v0.0.7 reconciliation;
- repeated registration after terminal state cannot reset the provider job to running.

The registry deliberately does not decide whether the terminal physical observation is true or acceptable. It makes provider-side identity/status durable; protocol verification remains outside storage.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics, capacity, recovery state, persistence, reconciliation, and provider-status mechanics; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.9 conformance bank

The repository includes tests for registration/reopen, deterministic and idempotent job identity, absent-key `not_found`, persisted terminal state feeding v0.0.8 and v0.0.7, exact terminal replay, conflicting terminal rejection, wrong-job rejection, concurrent registration convergence, registry schema validation, filesystem-only persistence, capability gating, and terminal-state preservation across repeated registration.

## Admission state

v0.0.9 is intentionally stacked on the v0.0.5-v0.0.8 candidate line. The canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

After the stacked line is admitted, the next high-value milestone is an **end-to-end restart rehearsal** joining durable capacity head, provider registry, coordinator restart, provider reattachment, terminal observation, reconciliation, and optional explicit Session result submission in one deterministic scenario.

## Status

**v0.0.9 reattachable reference provider: stacked implementation candidate under validation.**
