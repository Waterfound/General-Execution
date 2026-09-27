# Durable Execution F0 — Canonical Baseline Audit

## Scope

This audit freezes the implementation baseline for the first Durable Execution frontier:

```text
1 Active + 1 Secondary + N Passive
```

The goal is to replace chat-coordinated continuation with durable, restart-safe, evidence-bound execution while preserving General Execution's existing authority model.

## Canonical source baseline

General Execution baseline:

```text
Waterfound/General-Execution
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

Build Colony planning baseline:

```text
Waterfound/Build-Colony
17979869a85c9f5adf2cef2ceb589a07fcef6239
```

The Build Colony planning run is recorded separately as `general-execution-durable-asp-001`.

## Existing primitives that MUST be reused

The canonical General Execution baseline already provides:

- deterministic canonical JSON and SHA-256 identities;
- immutable `ExecutionSpec`, `DispatchPlan`, and logical Session identities;
- durable SQLite capacity heads;
- transactional compare-and-swap state commits;
- restart recovery without fabricated outcomes;
- durable dispatch intent and provider reconciliation;
- durable observed outcomes;
- deterministic Session recovery projection;
- a bounded mechanical recovery driver;
- explicit separation between execution mechanics and verification/integration/release authority.

These are substrate, not reasons to build another orchestration system.

## Existing authority invariant

The repository's governing rule remains:

> Execution consumes authority. It does not create authority.

Durable Execution therefore MAY persist and mechanically apply already-authorized transition rules, but MUST NOT create:

- verification authority;
- integration authority;
- release authority;
- spending authority;
- credential authority;
- consensus or economics authority;
- destructive infrastructure authority;
- unbounded retry authority.

## Divergent branches

Existing experimental branches named `v0.0.14*` and `v0.0.15*` are not silently canonicalized by this work. They may later provide evidence or implementation ideas, but adoption requires explicit evidence admission against the current canonical line.

This frontier starts from `ccc616ea...` only.

## Minimum Durable Execution objects

The implementation sequence is frozen as:

1. `portfolio_state`
2. `execution_checkpoint`
3. `transition_policy`

The first object is intentionally descriptive only. It does not itself schedule, wake, retry, diagnose, verify, integrate, or execute.

## F1 portfolio-state boundary

The first contract MUST:

- represent exactly one Active entry;
- represent exactly one Secondary entry;
- represent zero or more Passive entries;
- give every entry a stable work identity;
- preserve objective, active gate, source revision, evidence requirements, authority boundary, blockers, next action reference, and checkpoint reference;
- require explicit wake semantics for Passive entries;
- reject duplicate work identities;
- reject role/state contradictions;
- carry a monotonic generation and predecessor digest;
- have canonical serialization and deterministic digest;
- fail closed on unknown or malformed schema fields.

The contract MUST NOT yet:

- decide whether a wake condition is satisfied;
- promote Secondary;
- demote Active;
- execute work;
- verify results;
- invoke DI;
- retry provider calls;
- persist its own SQLite head;
- interact with Render, GitHub, Vercel, AWS, ChatGPT, or any other provider.

Those capabilities belong to later frontiers.

## F0 verdict

```text
CANONICAL_BASELINE = FROZEN
MEGA_ORCHESTRATOR = REJECTED
EXISTING_DURABLE_SUBSTRATE = REUSE
FIRST_EXECUTABLE_FRONTIER = portfolio_state
AUTHORITY_CREATED = false
```
