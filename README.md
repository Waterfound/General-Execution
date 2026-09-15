# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> capacity lease
  -> durable recovery context
  -> durable capacity head
  -> provider identity / status
  -> cold bootstrap
  -> provider reattachment
  -> reconciliation
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
- **v0.0.10 — Durable Store Reopen Rehearsal:** two-store reopen QA with execution context explicitly caller-retained.
- **v0.0.11 — Durable Recovery Context + Cold Bootstrap:** immutable reconstruction of Spec, registry, plan, Session, physical authorization, runner definition and lease anchor, followed by a stores-only cold coordinator rehearsal. See [`docs/v0.0.11-durable-recovery-context.md`](docs/v0.0.11-durable-recovery-context.md).

## v0.0.11 invariants

`DurableRecoveryContext` contains the complete typed execution identity needed to re-enter the existing recovery protocols after volatile coordinator memory is gone.

The context binds:

- exact `ExecutionSpec`;
- exact `RunnerRegistry` and selected `RunnerCapabilities`;
- deterministic `DispatchPlan`;
- running `ExecutionSession`;
- exact `PhysicalAttemptAuthorization`, including retry predecessor bindings;
- an anchor `DurableCapacitySnapshot` containing the active lease;
- exact recovered lease ID and digest.

The serialized form is canonical JSON. Loading reconstructs typed objects and re-runs existing plan, dispatch-request, capacity replay, authorization, and lease bindings.

### Anchor, not frozen head

The recovery context is anchored to the snapshot at which the attempt became recoverable. A later current capacity head may contain unrelated transitions from other slots while the same lease stays active.

The context remains valid only when the current capacity history extends the full anchor transition prefix and the exact lease is still active and unchanged.

### Safe persistence order

```text
reserve candidate in memory
  -> build anchor snapshot + recovery context
  -> persist recovery context
  -> commit durable capacity head
  -> register provider identity
```

A crash after context persistence but before capacity commit leaves an orphan context, which cold bootstrap ignores. Once a recoverable active capacity head exists, its recovery context was already durable.

### True cold bootstrap and resume

`bootstrap_active_recovery_contexts(...)` starts from only the recovery-context store and durable capacity-head store and reconstructs active execution bindings.

The reference rehearsal is deliberately split:

```text
prepare_reference_cold_restart(...)
  -> persist recovery context
  -> persist capacity head
  -> persist provider identity

[cold coordinator boundary]

resume_reference_cold_restart(paths only)
  -> reconstruct runner / Spec / registry / plan / Session / authorization
  -> recover in_flight_unknown lease
  -> provider running => keep_running
  -> terminal provider status
  -> physical outcome admission
  -> reconciliation CAS
```

The resume API receives no live execution objects from preparation. Its report marks `context_mode="cold_reconstructed"`.

A completed physical outcome still leaves the reconstructed Session `running`; logical submission remains a separate explicit `submit_result(...)` operation.

## Authority boundary

Recovery context preserves identity; it does not create permission to retry, release capacity without terminal/revocation evidence, submit a logical result automatically, verify application evidence, integrate changes, or approve release.

```text
physical completion != logical result submission
```

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.11 conformance bank

The repository includes context round-trip and exact reconstruction, unrelated-head advancement, lease-removal rejection, schema/binding checks, context persistence and idempotency, re-anchor conflict, cold bootstrap from stores only, corruption rejection, orphan/historical context handling, stores-only cold resume, completed cold recovery without automatic logical submission, provider identity reconstruction, deterministic replay across fresh files, invalid-mode preservation, distinct-store enforcement, and final report binding.

## Admission state

v0.0.11 remains stacked above the v0.0.5-v0.0.10 candidate line. Canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The next highest-value milestone is a **cross-store cut-point failure matrix** around recovery-context persistence, capacity-head commit, provider registration, terminal-state persistence, and reconciliation CAS. Each cut point must prove the exact safe recovery state without timing assumptions.

## Status

**v0.0.11 Durable Recovery Context + true cold coordinator rehearsal: stacked implementation candidate under validation.**
