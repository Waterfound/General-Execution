# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable capacity lease
  -> durable dispatch intent
  -> live dispatch permit
  -> provider reconciliation
  -> executable provider conformance
  -> provider contract attestation
  -> attested same-invocation resubmission permit
  -> observation / receipt
  -> durable full observed outcome
  -> restart-safe capacity release
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger. See [`docs/v0.0.1-kernel.md`](docs/v0.0.1-kernel.md).
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate. See [`docs/v0.0.2-reference-adapter.md`](docs/v0.0.2-reference-adapter.md).
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit. See [`docs/v0.0.3-physical-failure-semantics.md`](docs/v0.0.3-physical-failure-semantics.md).
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering. See [`docs/v0.0.4-capacity-lease-semantics.md`](docs/v0.0.4-capacity-lease-semantics.md).
- **v0.0.5 — Durable Head & Restart Recovery:** SQLite-backed canonical capacity heads, transactional CAS, replay-verified snapshots, and unresolved in-flight lease recovery. See [`docs/v0.0.5-durable-restart-recovery.md`](docs/v0.0.5-durable-restart-recovery.md).
- **v0.0.6 — Durable Dispatch Intent & Ambiguity Recovery:** durable outbox state, crash-safe submission ambiguity, live capacity-bound transport permits, and fail-closed restart reconciliation. See [`docs/v0.0.6-durable-dispatch-intent.md`](docs/v0.0.6-durable-dispatch-intent.md).
- **v0.0.7 — Provider Idempotency & Reconciliation:** stable invocation-key reconciliation, explicit duplicate semantics, evidence-bound provider status, and conservative resubmission decisions. See [`docs/v0.0.7-provider-reconciliation.md`](docs/v0.0.7-provider-reconciliation.md).
- **v0.0.8 — Provider Reconciliation Conformance & Attestation:** contract/evidence separation, immutable adapter-revision attestation, production-equivalent certification, and attested same-invocation-only resubmission permits. See [`docs/v0.0.8-provider-conformance-attestation.md`](docs/v0.0.8-provider-conformance-attestation.md).
- **v0.0.9 — Executable Provider Conformance Harness:** provider-neutral executable cases, transcript-bound evidence generation, deterministic sandbox reference target, and false-contract detection. See [`docs/v0.0.9-executable-provider-conformance.md`](docs/v0.0.9-executable-provider-conformance.md).
- **v0.0.10 — Durable Observed Outcome:** atomically retain the complete admitted `PhysicalOutcomeBundle` with the `observed` dispatch transition and use it to finish canonical capacity release after restart. See [`docs/v0.0.10-durable-observed-outcome.md`](docs/v0.0.10-durable-observed-outcome.md).

## v0.0.10 invariants

The earlier durable outbox proved which physical outcome had been observed by storing hashes, but hashes alone cannot recreate the exact object required by `release_capacity_for_outcome()` after a process restart. v0.0.10 closes that gap without weakening any provider-reconciliation gate.

The canonical v0.0.10 path enforces:

- the complete physical authorization, observation, receipt, and optional `ResultEnvelope` have a canonical JSON representation;
- deserialization must pass the existing intrinsic physical-outcome verifier;
- `SqliteDurableObservedOutcomeStore.record_observed()` changes the dispatch state and inserts the complete outcome under one `BEGIN IMMEDIATE` transaction;
- observed-state metadata and stored outcome bytes must reproduce the same runner, lease, authorization, invocation, request, physical attempt, observation, receipt, outcome, and transport status;
- exact replay after a lost acknowledgement is idempotent;
- a conflicting second outcome for the same durable dispatch fails closed;
- an `observed` dispatch with missing or inconsistent outcome bytes fails closed;
- restart release reruns `verify_physical_outcome()` against the supplied execution context before touching capacity;
- recovery can release only the exact active lease bound to the durable outcome;
- replay after the exact release is already canonical is idempotent;
- concurrent recovery that loses the capacity CAS succeeds only if the winning state contains that same exact canonical release.

The legacy `SqliteDispatchIntentStore` remains available for compatibility with the v0.0.6–v0.0.9 surface. Restart-complete v0.0.10 observed-outcome durability requires `SqliteDurableObservedOutcomeStore`.

## Relationship to provider conformance

v0.0.7–v0.0.9 determine whether provider reconciliation and same-invocation behavior are trustworthy enough to admit or resubmit provider work. v0.0.10 begins only after a `PhysicalOutcomeBundle` has already been admitted.

It therefore complements, rather than replaces, the provider-specific evidence gate. Provider reconciliation remains responsible for ambiguity; durable outcome storage is responsible for not forgetting an admitted outcome before local capacity state is finished.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.10 conformance bank

The candidate branch contains 14 focused tests covering canonical failure/completed outcome round trips, complete-result preservation, nested tamper rejection, atomic observed-outcome persistence, lost-ack replay, conflicting outcomes, missing/corrupt outcome state, runner recovery, restart-driven capacity release, idempotent release replay, wrong-context rejection, and completed-outcome release.

The repository execution environment remains unavailable here without consuming GitHub Actions or introducing external infrastructure, so the 14-case bank is **not** described as an executed 14/14 result.

## Remaining trust boundary

The v0.0.9 provider-specific provenance requirement remains unchanged. A durable local copy of an admitted physical outcome is not proof that a provider-specific conformance run occurred correctly.

Production-equivalent provider integration still requires trustworthy run provenance binding the exact harness revision, adapter revision, provider/environment identity, conformance-run digest, generated evidence digest, and execution mechanism.

## Next ceiling

After v0.0.10 receives executable regression evidence, the next convergence step is a durable logical Session/result lifecycle adapted to the canonical dispatch/provider architecture. The parallel lifecycle prototype should be used as design evidence only, not merged wholesale, because its v0.0.5–v0.0.10 names and persistence modules evolved on a different branch from the canonical provider-conformance line.

## Status

**v0.0.10 Durable Observed Outcome is a canonical-mainline candidate branch. `main` remains on v0.0.9 until executable regression evidence is available.**
