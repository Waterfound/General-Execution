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

- **v0.0.1 — Execution Kernel**
- **v0.0.2 — Provider-neutral Adapter Contract**
- **v0.0.3 — Physical Failure Semantics**
- **v0.0.4 — Capacity & Lease Semantics**
- **v0.0.5 — Durable Head & Restart Recovery**
- **v0.0.6 — SQLite Durable Head Persistence**
- **v0.0.7 — Post-Restart Provider Reconciliation**
- **v0.0.8 — Provider Reattachment Semantics**
- **v0.0.9 — Reattachable Reference Provider**
- **v0.0.10 — Durable Store Reopen Rehearsal** (`context_mode=caller_retained`)
- **v0.0.11 — Durable Recovery Context**
- **v0.0.12 — Cold Coordinator Reconstruction Rehearsal** (`context_mode=cold_reconstructed`)
- **v0.0.13 — Restart Cut-Point Matrix**: deterministic safe-state classification across context-only, capacity-without-provider, provider-running, terminal persistence, volatile reconciliation planning, and final reconciliation CAS. See [`docs/v0.0.13-restart-cutpoint-matrix.md`](docs/v0.0.13-restart-cutpoint-matrix.md).

## v0.0.13 recovery matrix

The matrix freezes six durable cut points:

```text
context_only
  -> capacity_committed
  -> provider_running
  -> terminal_persisted
  -> reconciliation_planned
  -> reconciled
```

Their required safe dispositions are:

```text
orphan_context
  -> remain_unknown
  -> keep_running
  -> terminal_pending_reconciliation
  -> terminal_plan_reproducible
  -> reconciled
```

The important boundaries are explicit:

- context without a capacity head is an inert orphan;
- active capacity with missing provider identity remains occupied and unknown;
- provider `running` cannot create an outcome or retry opportunity;
- terminal provider persistence does not release capacity;
- reconciliation planning does not mutate durable state;
- a lost volatile reconciliation plan must rederive with the same digest;
- only canonical reconciliation CAS removes the active lease.

Therefore:

```text
provider not_found != failure
terminal persistence != capacity release
reconciliation planning != capacity release
only reconciliation CAS releases canonical capacity
```

## Authority boundary

Recovery and restart handling preserve identity and occupancy. They do not create permission to execute again, verify domain correctness, integrate outputs, approve releases, or automatically submit logical results.

The existing result boundary remains:

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

## Current v0.0.13 conformance bank

The repository includes cut-point tests for canonical safe-state ordering, orphan context behavior, provider-missing conservative recovery, running occupancy preservation, terminal persistence without release, deterministic reconciliation-plan reproduction after volatile loss, reconciliation-only capacity release, and report determinism across fresh directories.

## Evidence and admission state

The v0.0.5-v0.0.13 line remains stacked. Canonical `main` remains at v0.0.4 because the complete historical repository regression has not yet been executed in a complete runner environment.

v0.0.13 closes the major local **restart semantics** gaps, but one high-value local evidence boundary remains: process-separated cold recovery, where preparation occurs in one Python process and resume occurs in a different process that receives only durable paths.

## Next ceiling

The next milestone is **process-separated cold recovery**. After that, further confidence should come primarily from complete regression and real provider/host evidence rather than more restart-state semantics.

## Status

**v0.0.13 Restart Cut-Point Matrix: stacked implementation candidate under validation.**
