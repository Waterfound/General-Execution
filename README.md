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

## v0.0.11 invariants

`project_session_after_restart()` starts from the same immutable `ExecutionSpec`, registry, plan, runner and logical-attempt identity, loads the canonical capacity head and durable dispatch/outcome state, and derives what those durable facts prove about the Session.

The projection enforces:

- no physical history -> deterministic `bound` Session with a safe `start_session` replay action;
- active capacity lease with no durable dispatch intent -> `running`, action `prepare_dispatch_intent`;
- prepared dispatch -> `running`, action `begin_submission`;
- `submission_unknown` -> `running`, action `reconcile_provider` and no blind resubmission;
- observed outcome with active lease -> `running`, action `release_observed_capacity`;
- terminal physical failure with complete durable prior outcome -> `running`, `retry_eligible=true`, but no automatic retry authority;
- terminal completed outcome with complete durable result -> deterministic reproduction of `submit_result(running, result)` and projected `result_submitted`;
- canonical Session-revocation release -> deterministic reproduction of `revoke_session(running)` and projected `revoked`;
- physical retry ordinals remain separate from the logical Session attempt;
- terminal legacy releases that lack v0.0.10 complete outcome bytes never fabricate a result or retry source and remain `legacy_untracked`.

This removes the immediate need for the parallel prototype's additional Session-head database. Durable execution evidence remains the source of truth; the Session becomes a deterministic projection over that evidence.

## v0.0.10 durable outcome boundary

The v0.0.10 path remains the prerequisite for restart-complete terminal projection. `SqliteDurableObservedOutcomeStore` atomically stores the complete physical outcome with the `observed` dispatch transition and `release_observed_capacity_after_restart()` finishes the exact capacity release idempotently.

The older `SqliteDispatchIntentStore` remains available for compatibility, but a terminal release created without complete durable outcome bytes cannot be upgraded into a reconstructed result by v0.0.11.

## Relationship to provider conformance

v0.0.7–v0.0.9 govern provider ambiguity and provider-contract evidence. v0.0.10 retains an already-admitted outcome. v0.0.11 only projects local logical state from those durable facts.

None of these layers decide domain correctness, engineering verification, integration, or release approval.

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

The stacked candidate line contains the 14-case v0.0.10 durable-outcome bank plus 10 focused v0.0.11 Session-projection tests covering every restart phase from no physical history through active retry, terminal failure, revocation, completed result, and legacy incomplete evidence.

The complete branch cannot currently be materialized in the local runner without external infrastructure or GitHub Actions, so these banks are **present but not claimed as executed 14/14 or 10/10 evidence**.

## Remaining trust boundary

Provider-specific production evidence remains separate. A local deterministic projection does not prove that a real provider fulfilled its conformance contract; it only consumes provider outcomes that have already passed the relevant admission boundary.

## Next ceiling

After executable regression, the next highest-value component is a **bounded recovery driver**. It may consume a `recovery_required` projection and execute only the single named mechanical action. It must refuse `legacy_untracked` and `inconsistent` state, and it must never convert `retry_eligible` into automatic retry policy.

## Status

**v0.0.11 Session Recovery Projection is stacked on the v0.0.10 canonical-mainline candidate. `main` remains on v0.0.9 until executable regression evidence is available.**
