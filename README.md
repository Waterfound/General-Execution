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

## v0.0.8 invariants

A provider's idempotency declaration is no longer sufficient to elevate a v0.0.7 reconciliation decision into transport eligibility.

Two independent evidence lineages are preserved:

```text
invocation-specific reconciliation evidence
        +
provider/adapter conformance evidence
```

The core enforces:

- conformance evidence binds the exact reconciliation-contract digest and immutable adapter revision;
- required conformance cases are unique and fail closed when missing;
- contracts claiming terminal evidence lookup must prove `terminal_evidence_binding`;
- sandbox evidence can establish logical conformance but can never certify safe production resubmission;
- `safe_resubmission_certified` requires all required cases passing in `production_equivalent` scope and a contract with strong idempotency semantics;
- `ProviderContractAttestation.authority = NONE`;
- manually altered attestations fail deterministic re-verification;
- a provisional `resubmit_same_invocation` decision still requires a fresh current `LiveDispatchPermit` at the attestation gate;
- `AttestedResubmissionPermit` binds the decision digest, reconciliation-evidence digest, conformance-evidence digest, contract, attestation, live permit and immutable adapter revision;
- attested permit authority is only `IDEMPOTENT_RESUBMIT_ONLY`;
- attested resubmission preserves the exact invocation ID and request digest;
- attested resubmission can never authorize a new physical-attempt ordinal;
- revocation or durable capacity change invalidates a stale live permit even when provider conformance remains valid.

No concrete remote provider transport is enabled by v0.0.8.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.8 evidence

The candidate adds a focused 15-scenario attestation bank covering production-equivalent certification, sandbox non-certification, required/missing/duplicate/failed cases, unsafe-provider contracts, conditional terminal-evidence requirements, contract/revision/attestation mismatch, stale live permits, same-invocation-only permit issuance, permit tampering, and explicit separation of reconciliation versus conformance evidence.

The current environment still does not provide a repository execution runtime without consuming GitHub Actions or creating external infrastructure. The implementation therefore records static API/boundary review and a committed test bank; it does **not** claim an external pytest execution here.

## Next ceiling

The next highest-value boundary is an **executable provider conformance harness**.

`production_equivalent` is currently a property of supplied evidence. Before any concrete remote transport exists, General Execution should make the conformance suite itself executable against a reference adapter/provider and generate the evidence artifacts mechanically.

The harness should prove at minimum:

- same invocation + same request has the declared duplicate semantics;
- same invocation + different request is rejected;
- lookup remains bound to invocation + request identity;
- an accepted operation cannot later be falsely reported as absent;
- terminal evidence, when claimed, is retrievable and bound to the same invocation;
- repeated clean-room runs produce the same semantic verdict.

A provider-specific adapter should become eligible for transport integration only after the executable harness produces evidence bound to its exact immutable revision.

## Status

**v0.0.8 Provider Reconciliation Conformance & Attestation: implementation candidate complete in branch; focused attestation bank and static boundary review recorded; executable conformance harness remains the next gate.**
