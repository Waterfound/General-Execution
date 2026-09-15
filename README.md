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
  -> process-separated cold recovery
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
- **v0.0.10 — Canonical Cold Coordinator Bootstrap** — durable execution context, fail-safe ordering, lost-ack replay, strict cold reconstruction. See [`docs/v0.0.10-canonical-cold-bootstrap.md`](docs/v0.0.10-canonical-cold-bootstrap.md).
- **v0.0.11 — Process-Separated Canonical Cold Recovery** — preparation and recovery in different Python interpreters with only SQLite paths crossing the restart boundary. See [`docs/v0.0.11-canonical-process-separated-recovery.md`](docs/v0.0.11-canonical-process-separated-recovery.md).

## v0.0.11 boundary

The preparation process persists:

```text
coordinator context
  -> dispatch PREPARED
  -> canonical capacity reservation CAS
  -> dispatch SUBMISSION_UNKNOWN
  -> process exits
```

A second interpreter receives only:

```text
capacity.db
context.db
dispatch.db
```

It reconstructs the exact execution identity and must recover:

```text
context_mode = cold_reconstructed
recovery_action = reconcile_provider
blind_resubmissions_authorized = 0
provider_outcomes_inferred = 0
```

Process PID/token evidence is intentionally separate from canonical protocol identity: fresh runs produce the same semantic digest but different execution-evidence digests.

The existing authority boundaries remain:

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

These runs used an offline reconstructed local workspace because the container cannot resolve GitHub hosts. Canonical base modules were verified against their Git blob identities; some newly added files/test drivers were reconstructed with equivalent logic. This is targeted evidence, not a complete historical byte-for-byte checkout regression. No GitHub Actions were consumed.

## Next ceiling

Provider-neutral restart/recovery is now at diminishing returns. The next material gates are:

1. complete historical repository regression on the canonical stacked line;
2. provider-specific execution of the v0.0.9 conformance harness with trustworthy run provenance;
3. only after those gates, consideration of concrete remote transport.

## Status

**v0.0.11 Process-Separated Canonical Cold Recovery: targeted local conformance green; full historical regression and provider-specific provenance remain pending.**
