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
  -> provider reconciliation / idempotent submission
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

## v0.0.7 invariants

`SUBMISSION_UNKNOWN` can no longer collapse into retry merely because a coordinator restarted or time passed. Provider reconciliation is keyed by the exact existing `invocation_id` and request digest.

A provider reports one of four states:

```text
ABSENT | ACCEPTED | TERMINAL | UNKNOWN
```

The core enforces:

- reconciliation only from a durable `SUBMISSION_UNKNOWN` state;
- the physical authorization must reproduce the dispatch intent exactly;
- provider / adapter / adapter-version contract binding;
- query binding to dispatch state, dispatch permit, authorization, invocation and request digest;
- provider observations are revalidated at decision time, even when wrapped in an Evidence object;
- same idempotency key with a different request must be rejected by contract;
- `may_duplicate` providers are reconciliation-capable but never eligible for automatic resubmission;
- `ABSENT` permits same-invocation resubmission only under strong idempotency **and** a fresh `LiveDispatchPermit` bound to the current durable capacity head;
- stale live permits after revocation/capacity changes fail closed;
- `ACCEPTED` means poll the existing operation, never resubmit;
- `TERMINAL` routes to evidence admission only when terminal evidence is retrievable;
- `UNKNOWN` remains hold even when the provider claims strong idempotency;
- reconciliation resubmission preserves the same physical invocation identity and is distinct from native retry.

No concrete remote provider transport is enabled by v0.0.7.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and capacity; Build Colony keeps evidence-verification and integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current v0.0.7 evidence

The branch adds a 14-scenario focused reconciliation bank spanning contract identity binding, unsafe-provider discrimination, ABSENT resubmission gates, stale live permits, ACCEPTED/TERMINAL/UNKNOWN routing, terminal-evidence capability, observation mismatch rejection and decision-time evidence revalidation.

As with v0.0.6, the current environment does not provide a repository execution runtime without using GitHub Actions or creating external infrastructure. The implementation therefore records static API/boundary review and the committed conformance bank, but does not claim that external pytest ran here.

## Next ceiling

The next highest-value boundary is **provider reconciliation conformance & attestation**.

A provider adapter must not become transport-eligible merely by declaring strong idempotency. General Execution should independently exercise the exact adapter revision and prove:

- same `invocation_id` + same request never creates a second operation;
- same `invocation_id` + different request is rejected;
- lookup is bound to invocation + request identity;
- ABSENT semantics are stable and do not hide accepted work;
- ACCEPTED resolves to one stable provider operation;
- TERMINAL evidence can be retrieved and bound back to the invocation when claimed.

The resulting attestation should bind the provider contract digest, adapter revision and conformance evidence digest. Concrete remote transport should remain disabled until that gate exists.

## Status

**v0.0.7 Provider Idempotency & Reconciliation: implementation candidate complete in branch; focused conformance bank and static boundary review recorded; external pytest remains unclaimed.**
