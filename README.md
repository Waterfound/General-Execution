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
- **v0.0.13 — Restart Cut-Point Matrix**
- **v0.0.14 — Process-Separated Cold Recovery**: preparation and resume execute in distinct Python interpreter processes connected only by the three durable stores. See [`docs/v0.0.14-process-separated-recovery.md`](docs/v0.0.14-process-separated-recovery.md).

## v0.0.14 process boundary

The QA harness launches two fixed worker processes:

```text
Python process A
  -> prepare_reference_cold_restart(...)
  -> exits completely

Python process B
  -> receives only capacity/context/provider paths
  -> resume_reference_cold_restart(...)
```

The workers are launched with `sys.executable -m general_execution.process_worker` and `shell=False`. The worker module exposes only bounded `prepare` and `resume` rehearsal phases; it is not a general command runner.

Each worker returns canonical JSON with a process token, PID/PPID, bounded payload and payload digest. The final process report requires both workers to be distinct direct children of the harness and different from the harness process.

## Deterministic protocol vs process evidence

Process identifiers and process tokens are execution-specific. They are deliberately not part of the deterministic recovery protocol identity.

With identical protocol inputs in fresh stores, the underlying cold-recovery evidence must still reproduce the same:

```text
cold report digest
recovery context digest
physical outcome digest
```

while the worker process tokens differ.

This separates:

```text
process evidence = run-specific
protocol evidence = deterministic
```

## Authority boundary

The process harness adds evidence about memory separation only. It does not grant arbitrary process execution to General Execution and does not change execution, verification, integration, release, or result-submission authority.

The result boundary remains:

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

## Current v0.0.14 conformance bank

The repository includes tests for distinct prepare/resume interpreter identities, direct-child process binding, recovery-context identity across the process boundary, completed physical result with logical Session still running, timeout without logical result, and deterministic protocol digests despite non-deterministic process evidence.

## Evidence and admission state

The v0.0.5-v0.0.14 line remains stacked. Canonical `main` remains at v0.0.4 because the complete historical regression has not yet been executed in a complete runner environment.

The v0.0.14 process harness and tests are implemented, but process separation should be described as **observed evidence only after this conformance bank is actually executed**. Until then it is an implemented evidence mechanism, not a passed gate.

## Ceiling

At v0.0.14, the local restart/recovery architecture is effectively at its **semantic ceiling**. Further restart-specific semantics should not be added without evidence revealing a concrete gap.

The next material progress is evidence-driven:

1. execute the v0.0.14 process-separated conformance bank;
2. execute the complete historical regression for the stacked line;
3. exercise a real provider/host implementation of the reattachment contract;
4. add contention/multi-host evidence where it materially changes confidence.

## Status

**v0.0.14 Process-Separated Cold Recovery: implementation candidate; execution evidence pending.**
