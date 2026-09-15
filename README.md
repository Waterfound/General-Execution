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
- **v0.0.12 — Cold Coordinator Reconstruction Rehearsal** (`context_mode=cold_reconstructed`). See [`docs/v0.0.12-cold-restart-rehearsal.md`](docs/v0.0.12-cold-restart-rehearsal.md).

## v0.0.12 boundary

v0.0.12 separates preparation and recovery into different APIs.

```text
prepare_reference_cold_restart(paths...)
  -> recovery context durable first
  -> capacity head committed second
  -> provider identity registered third
  -> returns only a preparation receipt

resume_reference_cold_restart(paths...)
  -> receives only three store paths
  -> reconstructs runner + Spec + registry + plan + Session + authorization
  -> queries provider state
  -> admits terminal physical outcome
  -> reconciles capacity
```

No protocol object from the preparation phase is an argument to `resume_reference_cold_restart(...)`.

The recovered report freezes:

```text
context_mode = cold_reconstructed
```

This is deliberately stronger than v0.0.10's caller-retained store reopen.

## Recovery ordering

The safe preparation order is:

```text
recovery context
  -> capacity head
  -> provider identity
```

If the coordinator stops after context persistence but before the capacity commit, the result is an orphan context and no active lease. Once an active recoverable capacity head exists, its execution context was already durable.

Provider `running` remains `keep_running`; it creates no outcome and releases no capacity. A terminal state is admitted through the existing v0.0.8 physical protocol and released only through v0.0.7 reconciliation.

## Authority boundary

Even a reconstructed completed physical attempt does not submit the logical Session result automatically:

```text
physical completion != logical result submission
```

`submit_result(...)` remains a separate explicit step. Cold recovery does not authorize retry, domain verification, integration, or release.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.12 conformance bank

The repository includes tests for cold timeout reconstruction, cold completion with explicit later result submission, preparation receipts spanning context/capacity/provider durability, deterministic replay across fresh stores, three-store separation, invalid terminal-mode handling, and rejection of a second resume after canonical reconciliation.

## Evidence and admission state

v0.0.12 proves a protocol-level cold reconstruction boundary because the resume API receives only durable store paths. It is not yet an operating-system process-separation test and does not replace the still-pending full historical repository regression.

The v0.0.5-v0.0.12 line therefore remains stacked. Canonical `main` remains at v0.0.4.

## Next ceiling

The next highest-value milestone is a **restart cut-point matrix** over the three durable layers: context-only, context+capacity, provider-running, terminal persistence, and reconciliation CAS. Each cut point must converge to one explicit safe state without duplicate canonical execution.

## Status

**v0.0.12 Cold Coordinator Reconstruction Rehearsal: stacked implementation candidate under validation.**
