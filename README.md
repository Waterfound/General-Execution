# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
Authorized ExecutionSpec
        -> Runner Registry
        -> Deterministic Dispatch Plan
        -> Retry-safe Execution Session
        -> Bound Result Envelope
        -> Verifiable Execution Ledger
```

> **Execution consumes authority. It does not create authority.**

## Why it exists

Build Colony evolved strong execution mechanics while solving a narrower engineering-coordination problem. General Execution separates the reusable execution substrate from Build Colony's project intelligence.

Build Colony retains ownership of ceiling mapping, work decomposition, dependency semantics, engineering evidence gates, independent verification, serialized integration, and ceiling assessment. General Execution owns only the provider-neutral mechanics needed to execute an already bounded request and return provenance-bound evidence.

The same boundary permits DI, CII, Project Assurance, or future systems to use the execution substrate without inheriting Build Colony's engineering semantics.

## Non-goals

General Execution is not:

- a project manager;
- an architecture authority;
- a verifier of domain correctness;
- an integration controller;
- a release or consensus authority;
- a translator that invents missing domain semantics;
- an unrestricted shell executor.

Result status is deliberately limited to `completed` or `failed`. A runner cannot return `verified`, `integrated`, `approved`, `released`, or an equivalent authority claim through the core protocol.

## v0.0.1 — Execution kernel

The first kernel freezes six guarantees:

1. **Immutable request identity.** `ExecutionSpec` binds producer, producer revision, source revision, objective, inputs, capabilities, scopes, forbidden actions, evidence requirements, and an optional external authority reference.
2. **Deterministic capability matching.** A `RunnerRegistry` compiles to the same `DispatchPlan` regardless of registry ordering.
3. **Fail-closed dispatch.** If no runner satisfies the declared capability/mode contract, the plan is explicitly deferred.
4. **Retry-safe logical attempts.** Every attempt gets a distinct content-derived Session identity. A stale attempt cannot submit a result to a newer session.
5. **Exact result binding.** A result must match the active Session, spec, runner, and attempt exactly.
6. **Append-only provenance.** The execution ledger is a deterministic hash chain without wall-clock consensus.

The v0.0.1 kernel intentionally performs no provider invocation itself. Provider adapters and physical transports belong after the protocol boundary is proven locally.

## Relationship to Build Colony

```text
Build Colony
  Goal -> Ceiling Map -> Dependency Graph -> Work Package
                                      |
                                      v
                              General Execution
                         Spec -> Plan -> Session -> Result
                                      |
                                      v
Build Colony / independent verifier
  Evidence admission -> verification -> serialized integration
```

The important boundary is one-way: General Execution may return execution evidence, but it cannot promote its own output into Build Colony state.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```

The core is dependency-free; `pytest` is only a development dependency.

## Next ceiling

After v0.0.1 is frozen, the next highest-value milestone is a **reference adapter protocol** that proves a physical invocation can reproduce the exact `ExecutionSpec`/Session binding without gaining verification or integration authority. Build Colony can then become the first real client profile.

## Status

**v0.0.1 kernel: implemented and locally validated.**
