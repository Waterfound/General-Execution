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
  -> deterministic Session recovery projection
  -> bounded mechanical recovery driver
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
- **v0.0.11 — Deterministic Session Recovery Projection:** reconstruct the logical Session from durable capacity/dispatch/outcome evidence instead of adding a second Session database. See [`docs/v0.0.11-session-recovery-projection.md`](docs/v0.0.11-session-recovery-projection.md).
- **v0.0.12 — Bounded Recovery Driver:** consume one exact recovery projection and execute at most one named mechanical catch-up action without acquiring transport or retry authority. See [`docs/v0.0.12-bounded-recovery-driver.md`](docs/v0.0.12-bounded-recovery-driver.md).

## v0.0.12 invariants

`apply_recovery_step()` accepts only an exact current `SessionRecoveryProjection`. It recomputes that projection from durable state before doing anything; stale projections fail closed.

The driver enforces:

- `coherent + none` -> no action;
- `start_session` -> deterministic in-memory `bound -> running` only;
- `prepare_dispatch_intent` -> reconstruct the exact first/retry physical authorization and persist only the deterministic dispatch intent;
- retry authorization must reproduce the exact durable predecessor invocation and receipt digest;
- `begin_submission` may advance the durable outbox and return a `DispatchPermit`, but that permit still has no transport authority;
- `reconcile_provider` returns `external_input_required` and does not contact or mutate provider state;
- `release_observed_capacity` uses the v0.0.10 durable full outcome path and existing capacity CAS/idempotency gates;
- `legacy_untracked` and `inconsistent` projections are refused;
- `retry_eligible=true` never becomes automatic retry policy;
- every `RecoveryDriverResult` has `transport_authority=false` and `automatic_retry_authorized=false`;
- after a durable mutation, the result Session comes from the freshly recomputed post-action projection, so concurrent terminal transitions cannot be reported as stale `running` state;
- a concurrent revocation can leave a conservative prepared intent, but the missing active lease prevents `begin_submission` and transport resurrection.

The driver applies recovery mechanics only. It never decides whether execution should be retried, whether provider evidence is trustworthy, whether a result is correct, or whether anything should be integrated or released.

## Recovery stack

The restart path is now deliberately layered:

```text
canonical durable evidence
        -> v0.0.11 Session projection
        -> v0.0.12 one-step bounded driver
        -> fresh projection
```

Provider ambiguity stays outside this automatic path. A `submission_unknown` state stops at `external_input_required`; provider-specific reconciliation/conformance must provide the next evidence.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and recovery state; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current candidate evidence

The stacked candidate line contains:

- v0.0.10: 14 focused durable-observed-outcome tests;
- v0.0.11: 10 focused deterministic Session-projection tests;
- v0.0.12: 12 focused bounded-driver tests, including stale projections, exact retry reconstruction, external provider-reconciliation boundary, terminal outcome recovery, no automatic retry, and revocation races.

The complete branch still cannot be materialized in the local runner without external infrastructure or GitHub Actions, so these banks are **present but not claimed as executed 14/14, 10/10, or 12/12 evidence**.

## Remaining trust boundary

Provider-specific production evidence remains separate. Local durable state, projection, and recovery do not prove that a real provider fulfilled its conformance contract.

Production-equivalent provider integration still requires trustworthy run provenance binding the exact harness revision, adapter revision, provider/environment identity, conformance-run digest, generated evidence digest, and execution mechanism.

## Next ceiling

Pure provider-neutral/local recovery modeling is now near diminishing returns. After executable regression, the next material development gate is **provider-specific sandbox execution with trustworthy conformance-run provenance**, exercised end-to-end through the v0.0.10–v0.0.12 recovery path before any real remote transport is enabled.

## Status

**v0.0.12 Bounded Recovery Driver is stacked on the canonical-mainline candidate. `main` remains on v0.0.9 until executable regression evidence is available.**
