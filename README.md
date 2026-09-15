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
  -> durable capacity release
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

## v0.0.9 invariants

Conformance evidence no longer needs to be assembled manually to exercise the protocol. `run_provider_conformance()` executes the target behavior and generates the case evidence from observed transcripts.

The harness enforces:

- target provider / adapter / adapter-version identity must match the reconciliation contract before tests run;
- target adapter revision must be immutable lowercase hex;
- request and evidence digests are validated at the target boundary;
- each case runs from a reset target state;
- same-invocation/same-request behavior is measured against the exact declared semantics;
- same invocation with a different request must be explicitly rejected;
- lookup must remain bound to both invocation and request identity;
- an accepted invocation cannot subsequently be reported as absent;
- terminal evidence, when claimed, must resolve to the same provider operation and exact terminal-evidence digest;
- each case evidence digest binds the harness version, case identity, and observed transcript;
- `ProviderConformanceRun` binds the exact contract, adapter revision, environment scope, case results, generated evidence digest, and all-pass verdict;
- conforming `may_duplicate` behavior remains correctly measurable while still being unsafe for automatic resubmission under the v0.0.7/v0.0.8 policy gates.

The included `ReferenceConformanceTarget` is an in-memory sandbox target for validating the harness mechanism. It is not a production-equivalent provider and does not enable remote transport.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.9 evidence

The candidate adds a focused executable-harness bank covering mechanically generated sandbox evidence, deterministic repeated runs, false same-request declarations, matching duplicate-rejected semantics, conformant-but-unsafe `may_duplicate`, identity mismatch, malformed adapter revision, lookup identity failure, absence failure, terminal-evidence failure, conditional terminal-case execution, and distinct request identities.

The repository execution environment remains unavailable here without consuming GitHub Actions or introducing external infrastructure, so no full external pytest run is claimed. The new harness itself is implementation code plus a committed test bank; its reference target remains sandbox-only in intended use.

## Remaining trust boundary

An executable harness materially improves evidence quality, but an ordinary in-process evidence object is still not cryptographic proof that an external provider test actually ran. No concrete remote transport consumes the artifacts yet.

Production-equivalent provider integration therefore still requires trustworthy run provenance binding at least:

- exact harness revision;
- exact adapter revision;
- provider/environment identity;
- conformance-run digest;
- generated conformance-evidence digest;
- the execution mechanism that produced them.

The system should not equate a self-asserted `production_equivalent` field with proof of execution.

## Next ceiling

The next evidence capable of materially changing the verdict is **provider-specific sandbox execution with trustworthy conformance-run provenance**.

Purely local provider-neutral modeling is now approaching diminishing returns. A concrete provider adapter should first implement the v0.0.9 target contract and run the harness in an independently identifiable sandbox/equivalent environment. Only after that evidence is bound to the exact adapter revision should General Execution consider enabling real remote transport.

## Status

**v0.0.9 Executable Provider Conformance Harness: implementation candidate complete in branch; reference sandbox harness and adversarial test bank recorded; provider-specific execution/provenance is the next material gate.**
