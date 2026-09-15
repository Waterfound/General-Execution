# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
Authorized ExecutionSpec
        -> Runner Registry
        -> Deterministic Dispatch Plan
        -> Retry-safe Execution Session
        -> Adapter Dispatch Request
        -> Provider Observation
        -> Bound Receipt + Result
        -> Verifiable Execution Ledger
```

> **Execution consumes authority. It does not create authority.**

## Why it exists

Build Colony evolved strong execution mechanics while solving a narrower engineering-coordination problem. General Execution separates the reusable execution substrate from Build Colony's project intelligence.

Build Colony retains ownership of ceiling mapping, work decomposition, dependency semantics, engineering evidence gates, independent verification, serialized integration, and ceiling assessment. General Execution owns only the provider-neutral mechanics needed to express an already bounded execution request and verify returned provenance-bound evidence.

The same boundary permits DI, CII, Project Assurance, or future systems to use the substrate without inheriting Build Colony's engineering semantics.

## Non-goals

General Execution is not a project manager, architecture authority, domain verifier, integration controller, release/consensus authority, translator that invents missing semantics, or unrestricted command runner.

Result status is deliberately limited to `completed` or `failed`. A provider cannot return `verified`, `integrated`, `approved`, `released`, or an equivalent authority claim through the core protocol.

## v0.0.1 — Execution kernel

The first kernel froze immutable request identity, deterministic capability matching, fail-closed dispatch, retry-safe logical attempts, exact result binding, and an append-only deterministic ledger.

## v0.0.2 — Provider-neutral Adapter Contract

v0.0.2 separates **authorization**, **transport**, and **evidence admission**.

```text
ExecutionSpec + Plan + running Session
              -> AdapterDispatchRequest
              -> external provider / transport
              -> ProviderObservation
              -> coordinator-side admission
              -> AdapterReceipt + InvocationBundle
              -> ledger provenance
```

General Execution does not launch an operating-system process or remote job itself. A provider may be local, remote, hosted, agent-backed, or otherwise external to the kernel. The kernel only binds what was authorized to what the provider claims happened and rejects observations that do not reproduce exactly.

The reference contract accepts one harmless conformance workload:

- provider: `reference-provider`;
- adapter: `reference-adapter`;
- mode: `read_only`;
- capability: `reference.probe`;
- task kind: `reference-probe`;
- evidence: `reference-probe-digest`.

Logical Session identity and provider invocation identity are separate namespaces. This allows future replicas, retries, and provider changes without corrupting logical-attempt semantics.

A successful invocation is recorded as:

```text
ADAPTER_DISPATCH
  -> PROVIDER_OBSERVATION
  -> ADAPTER_RECEIPT
  -> ADAPTER_RESULT
```

`InvocationRecord` binds the exact bundle to those ledger indices and the resulting ledger head.

## First client: Build Colony

The first conformance pilot uses `build-colony` as producer identity while keeping translation outside General Execution:

```text
Build Colony Work Package
        -> client-side translation
        -> ExecutionSpec
        -> General Execution request
        -> provider observation
        -> InvocationBundle
        -> Build Colony evidence admission
        -> independent verification/integration outside General Execution
```

General Execution therefore executes for Build Colony without importing Build Colony or acquiring Build Colony authority.

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
```

The core has no non-stdlib runtime dependencies.

## Current local evidence

- 36/36 tests GREEN;
- compileall GREEN;
- deterministic request reconstruction GREEN;
- registry substitution rejection GREEN;
- provider-observation tamper rejection GREEN;
- Build Colony first-client contract pilot GREEN;
- invocation ledger record verification GREEN;
- result accepted only by the exact active Session.

## Next ceiling

The next highest-value milestone is **v0.0.3 — Physical Failure Semantics**: provider rejection, timeout, cancellation, transport failure, duplicate physical attempts, and retry must become explicit auditable observations/receipts instead of exceptional or implicit control flow. Only after that boundary is frozen should General Execution add concrete remote provider transports.

## Status

**v0.0.2 provider-neutral adapter contract: implemented and locally validated.**
