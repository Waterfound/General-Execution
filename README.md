# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

> **Execution consumes authority. It does not create authority.**

## Protocol line

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable coordinator context
  -> dispatch PREPARED
  -> canonical capacity lease
  -> SUBMISSION_UNKNOWN
  -> process-separated / crash-safe cold recovery
  -> provider reconciliation
  -> executable provider conformance
  -> provider contract attestation
  -> attested same-invocation resubmission permit
  -> observation / receipt
  -> durable capacity release
  -> execution ledger
```

## Milestones

- **v0.0.1 — Execution Kernel**
- **v0.0.2 — Provider-neutral Adapter Contract**
- **v0.0.3 — Physical Failure Semantics**
- **v0.0.4 — Capacity & Lease Semantics**
- **v0.0.5 — Durable Head & Restart Recovery**
- **v0.0.6 — Durable Dispatch Intent & Ambiguity Recovery**
- **v0.0.7 — Provider Idempotency & Reconciliation**
- **v0.0.8 — Provider Conformance & Attestation**
- **v0.0.9 — Executable Provider Conformance Harness**
- **v0.0.10 — Canonical Cold Coordinator Bootstrap** — durable context, fail-safe ordering, lost-ack replay, strict cold reconstruction.
- **v0.0.11 — Process-Separated Canonical Cold Recovery** — different Python interpreters with only SQLite paths crossing the restart boundary.
- **v0.0.12 — Process Crash Cut-Point Matrix** — abrupt `os._exit(91)` after every pre-provider durable cut point followed by fresh-process recovery. See [`docs/v0.0.12-process-crash-cutpoint-matrix.md`](docs/v0.0.12-process-crash-cutpoint-matrix.md).

## v0.0.12 crash matrix

```text
context_only        -> inert_orphan
prepared            -> inert_orphan
capacity_committed  -> begin_submission
submission_unknown  -> reconcile_provider
```

The cut worker terminates abruptly after the selected durable stage. A separate recovery interpreter receives only:

```text
capacity.db
context.db
dispatch.db
```

The matrix therefore verifies that:

- pre-capacity context/dispatch material cannot create occupancy;
- once capacity is committed, recoverable context + dispatch identity already exist;
- `SUBMISSION_UNKNOWN` remains ambiguity, never retry;
- restart never fabricates provider outcomes;
- restart never silently releases capacity;
- PID/token evidence is run-specific and remains outside canonical semantic identity.

The authority boundaries remain:

```text
restart != failure
restart != completion
SUBMISSION_UNKNOWN != retry
provider not_found != failure
```

## First client

Build Colony remains the first client. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution owns execution mechanics, capacity, durable identity, restart recovery, reconciliation, and provider conformance; Build Colony retains evidence-verification and integration authority.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Targeted evidence

- **v0.0.10 canonical-cold bank:** 12 passed in 0.51 s; `compileall` green.
- **v0.0.11 process-separated bank:** 5 passed in 13.25 s; `compileall` green.
- **v0.0.12 process-crash matrix:** 5 passed in 14.34 s; `compileall` green.

These runs used an offline reconstructed local workspace because this container cannot reach GitHub directly. Canonical base modules were verified against their Git blob identities; some newly added files/test drivers were reconstructed with equivalent logic. This is targeted evidence, not a complete historical byte-for-byte checkout regression. No GitHub Actions were consumed.

## Ceiling

Provider-neutral restart/recovery is now at the **effective local ceiling**. The next material gates are evidence/external rather than additional restart abstractions:

1. complete historical repository regression on a full checkout;
2. provider-specific execution of the v0.0.9 conformance harness with trustworthy run provenance;
3. only after those gates, consideration of concrete remote transport.

## Status

**v0.0.12 Process Crash Cut-Point Matrix: targeted local conformance green; restart/recovery local ceiling reached.**
