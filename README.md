# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
Authorized ExecutionSpec
        -> Runner Registry
        -> Deterministic Dispatch Plan
        -> Retry-safe Logical Session
        -> Physical Attempt Authorization
        -> External Provider / Transport
        -> Physical Observation
        -> Bound Receipt / Result-or-Failure
        -> Verifiable Execution Ledger
```

> **Execution consumes authority. It does not create authority.**

## Why it exists

Build Colony evolved strong execution mechanics while solving a narrower engineering-coordination problem. General Execution separates the reusable execution substrate from Build Colony's project intelligence.

Build Colony retains ownership of ceiling mapping, work decomposition, dependency semantics, engineering evidence gates, independent verification, serialized integration, and ceiling assessment. General Execution owns only the provider-neutral mechanics needed to express an already bounded execution request and verify returned provenance-bound evidence.

The same boundary permits DI, CII, Project Assurance, or future systems to use the substrate without inheriting Build Colony's engineering semantics.

## Non-goals

General Execution is not a project manager, architecture authority, domain verifier, integration controller, release/consensus authority, translator that invents missing semantics, or unrestricted command runner.

A runner/provider cannot grant itself `verified`, `integrated`, `approved`, `released`, or equivalent authority through the core protocol.

## v0.0.1 — Execution Kernel

The first kernel froze immutable request identity, deterministic capability matching, fail-closed dispatch, retry-safe logical attempts, exact result binding, and an append-only deterministic ledger.

## v0.0.2 — Provider-neutral Adapter Contract

v0.0.2 separated **authorization**, **transport**, and **evidence admission**.

```text
ExecutionSpec + Plan + running Session
              -> AdapterDispatchRequest
              -> external provider / transport
              -> ProviderObservation
              -> coordinator-side admission
              -> AdapterReceipt + InvocationBundle
```

General Execution does not need to launch an operating-system process or remote job itself. A provider may be local, remote, hosted, agent-backed, or otherwise external to the kernel.

## v0.0.3 — Physical Failure Semantics

v0.0.3 separates a **logical Session attempt** from the physical attempts used to realize it.

```text
Logical Session attempt 1
        |
        +-> physical attempt 1 -> timed_out
        |                         |
        |                         +-> receipt digest
        |
        +-> physical attempt 2 -> transport_failed
        |                         |
        |                         +-> receipt digest
        |
        +-> physical attempt 3 -> completed -> ResultEnvelope
```

The following terminal transport outcomes are explicit protocol data rather than exceptional or forgotten control flow:

- `completed`
- `rejected`
- `timed_out`
- `cancelled`
- `transport_failed`

A physical failure does **not** silently fail or advance the logical Session. The Session remains `running` until the caller either submits a valid result or explicitly revokes it.

### Retry lineage

A retry gets:

- a new `invocation_id`;
- an incremented `physical_attempt` ordinal;
- the same logical `session_id` and logical attempt;
- `previous_invocation_id` bound to the prior physical attempt;
- `previous_receipt_digest` bound to the exact prior receipt.

A completed physical attempt cannot be retried. A retry chain cannot jump over, rewrite, or substitute an earlier receipt without failing verification.

### Duplicate physical execution

Two distinct provider invocations that execute the same physical authorization are represented as explicit `DuplicatePhysicalAttempt` evidence. Duplicate evidence cannot replace the canonical attempt or become a second admissible result by accident.

### Provenance

Every physical attempt records four deterministic ledger events:

```text
PHYSICAL_DISPATCH
  -> PHYSICAL_OBSERVATION
  -> PHYSICAL_RECEIPT
  -> PHYSICAL_RESULT
```

or, for a terminal transport failure:

```text
PHYSICAL_DISPATCH
  -> PHYSICAL_OBSERVATION
  -> PHYSICAL_RECEIPT
  -> PHYSICAL_TERMINAL_FAILURE
```

Re-recording the same physical authorization is rejected rather than overwriting or duplicating canonical history.

## First client: Build Colony

Build Colony remains the first client identity:

```text
Build Colony Work Package
        -> client-side translation
        -> ExecutionSpec
        -> General Execution logical Session
        -> one or more physical attempts
        -> ResultEnvelope or auditable terminal failure
        -> Build Colony evidence admission
        -> independent verification/integration outside General Execution
```

General Execution therefore executes for Build Colony without importing Build Colony or acquiring Build Colony authority.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies.

## Current evidence

- 39/39 full local conformance tests GREEN;
- 33 public regression/conformance tests included in the repository after v0.0.3;
- `compileall` GREEN;
- editable offline install GREEN;
- all four failure transport statuses admitted without fabricating a result;
- physical failure leaves the logical Session active;
- retry predecessor binding GREEN;
- completed-attempt retry rejection GREEN;
- changed observation/result/retry-lineage rejection GREEN;
- duplicate physical execution represented explicitly;
- physical attempt ledger record verification GREEN;
- v0.0.1 and v0.0.2 compatibility tests remain GREEN.

## Next ceiling

The next highest-value milestone is **v0.0.4 — Capacity & Lease Semantics**. `RunnerCapabilities.max_parallelism` already exists, but runtime physical-attempt capacity is not yet enforced by General Execution. Before adding a concrete remote transport, the core should prove that concurrent dispatch, capacity reservation, release, cancellation, retry, and duplicate-delivery races cannot oversubscribe a runner or silently create two canonical attempts.

## Status

**v0.0.3 Physical Failure Semantics: implemented and locally validated.**
