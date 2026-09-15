# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

> **Execution consumes authority. It does not create authority.**

## Protocol line

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable coordinator context
  -> durable dispatch PREPARED
  -> canonical capacity lease
  -> SUBMISSION_UNKNOWN
  -> cold coordinator recovery
  -> provider reconciliation
  -> executable provider conformance
  -> provider contract attestation
  -> attested same-invocation resubmission permit
  -> observation / receipt
  -> durable capacity release
  -> execution ledger
```

## Milestones

- **v0.0.1 — Execution Kernel** — deterministic identity, planning, Sessions, result binding, ledger.
- **v0.0.2 — Provider-neutral Adapter Contract** — authorization, transport, and evidence admission separation.
- **v0.0.3 — Physical Failure Semantics** — logical versus physical attempts and explicit retry lineage.
- **v0.0.4 — Capacity & Lease Semantics** — bounded parallelism, deterministic slots, CAS capacity state.
- **v0.0.5 — Durable Head & Restart Recovery** — SQLite canonical capacity head and conservative unresolved recovery.
- **v0.0.6 — Durable Dispatch Intent & Ambiguity Recovery** — `PREPARED -> SUBMISSION_UNKNOWN -> OBSERVED` and live dispatch permits.
- **v0.0.7 — Provider Idempotency & Reconciliation** — stable invocation reconciliation without blind retry.
- **v0.0.8 — Provider Conformance & Attestation** — independent evidence bound to exact adapter revisions.
- **v0.0.9 — Executable Provider Conformance Harness** — mechanically generated provider-contract evidence.
- **v0.0.10 — Canonical Cold Coordinator Bootstrap** — durable coordinator context, fail-safe ordering, replay-safe preparation, and cold reconstruction into the existing dispatch/reconciliation stack. See [`docs/v0.0.10-canonical-cold-bootstrap.md`](docs/v0.0.10-canonical-cold-bootstrap.md).

## v0.0.10 invariants

`DurableCoordinatorContext` binds the exact Spec, Registry, Plan, running Session, Physical Authorization, active Capacity Lease identity, and canonical Dispatch Intent.

The fail-safe persistence order is:

```text
coordinator context
  -> dispatch PREPARED
  -> canonical capacity reservation CAS
  -> dispatch SUBMISSION_UNKNOWN
```

Consequences:

- context-only or context+PREPARED material is inert before canonical capacity activation;
- once capacity is active, its context and dispatch identity must already be durable;
- an active lease without a matching dispatch intent is an integrity failure;
- `SUBMISSION_UNKNOWN` cold-recovers as `reconcile_provider`, never as blind retry;
- cold recovery infers zero provider outcomes;
- lost-ack replay returns the same preparation receipt without advancing capacity or dispatch state;
- corrupt capacity/context metadata and schema drift fail closed.

The provider-neutral boundary remains:

```text
restart != failure
restart != completion
SUBMISSION_UNKNOWN != retry
provider not_found != failure
```

## First client

Build Colony remains the first client. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution owns execution mechanics, capacity, durable execution identity, restart recovery, reconciliation, and provider conformance; Build Colony retains evidence-verification and integration authority.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## v0.0.10 targeted evidence

The focused 12-case canonical-cold bank passed locally: **12 passed in 0.51 s**. `compileall` also passed.

The offline harness used byte-identical Git blobs for the canonical base modules plus `context_codec.py`, `cold_guard.py`, and `canonical_cold.py`. `coordinator_context.py` and the test driver were reconstructed locally with equivalent logic to make execution possible without network access. This is therefore strong targeted evidence, but it is **not** claimed as the complete historical repository regression or a byte-for-byte checkout execution.

No GitHub Actions were consumed.

## Next ceiling

The next local evidence boundary is **process-separated canonical cold recovery**: preparation and recovery in distinct Python interpreter processes with SQLite files as the only bridge.

After that, confidence should increasingly come from complete historical regression and provider-specific execution with trustworthy conformance-run provenance rather than more provider-neutral recovery abstractions.

## Status

**v0.0.10 Canonical Cold Coordinator Bootstrap: targeted local conformance green; full historical regression still pending.**
