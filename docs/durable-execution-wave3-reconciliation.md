# Durable Execution Wave 3 — Candidate Reconciliation

## Why reconciliation was required

While Wave 3 Candidate A was being implemented on:

```text
feature/durable-asp-checkpoint-transition-policy
```

the F1 branch independently advanced with another Wave 3 implementation (Candidate B):

```text
feature/durable-asp-portfolio-state
7f760b32043aa344e3d0b56b77f536fd9dfa39d4
```

No concurrent work was overwritten. Candidate B remains preserved in its original history.

This reconciliation branch starts from Candidate B's completed F1 head and then applies the selected Wave 3 contract:

```text
feature/durable-asp-wave3-reconciled
```

## Candidate B strengths

Candidate B independently reproduced several important invariants:

- canonical checkpoint serialization;
- evidence required before checkpoint status;
- explicit authority-stop representation;
- fail-closed transition matching;
- explicit portfolio effects such as promotion, parking, wake, DI request, and human stop;
- canonical rule ordering and ambiguity rejection.

This provides useful independent confirmation that the Wave 3 decomposition is directionally sound.

## Candidate B gaps against the frozen F1 contract

Two issues make Candidate B unsuitable as the canonical Wave 3 contract without revision.

### 1. Role/state transitions are not bound together

Candidate B matches transitions only by state/event and models effects separately.

That allows constructs such as:

```text
passive -> ready
```

without an atomic role change.

F1 explicitly requires:

```text
role=passive => state=passive
role=secondary => state=ready
```

Therefore a wake/promotion/parking policy must represent both role and state when portfolio membership changes.

Candidate A does this directly with:

- `from_role`
- `from_state`
- `target_role`
- `target_state`

### 2. Checkpoint transition references are not cryptographically bound enough

Candidate B records:

- `canonical_refs: tuple[str]`
- `next_transition_refs: tuple[str]`

Those references are useful, but do not by themselves prove the exact:

- portfolio entry;
- transition policy;
- transition request;
- policy rule;
- evidence admissions;
- authority reference.

Candidate A binds these through exact digests and reproducible `TransitionDecision` objects.

## Canonical reconciliation choice

The reconciled Wave 3 uses Candidate A's stronger evidence-bound contract while preserving Candidate B as independent reproduction evidence.

Selected properties:

- transition matching includes role + state + signal;
- target includes role + state;
- admitted evidence carries immutable content digest;
- policy requires declared evidence kinds;
- authority-consuming transitions require immutable admitted authority reference;
- `TransitionDecision` binds policy, rule, request, entry, signal, evidence, target, and action;
- decision verification recomputes from policy + request;
- checkpoint binds exact portfolio state digest and exact entry digest;
- checkpoint preserves all evidence used by its decision;
- checkpoint names exact canonical transition policy digest;
- checkpoint contains exactly one of:
  - next transition decision; or
  - fail-closed stop reason.

## Intentionally not adopted from Candidate B yet

The following are useful ideas but are not required in the Wave 3 MVP:

- wall-clock `observed_at` inside checkpoint identity;
- a separate `effect` enum duplicating target role/state semantics;
- DI-specific transition events before DI integration is admitted;
- provider/scheduler behavior.

They can be reconsidered if later evidence demonstrates a need.

## Verification evidence

Candidate A's contract logic passed the focused isolated Wave 3 behavioral bank:

```text
24 / 24 PASS
```

The reconciliation changes only move that selected contract onto the latest F1 ancestry. Candidate B remains available for independent comparison.

The current environment still does not permit a full repository clone from `github.com`, so full-suite promotion evidence remains outstanding.

## Status

```text
F1_CURRENT_ANCESTRY = PRESERVED
CANDIDATE_B = PRESERVED_AS_INDEPENDENT_REPRODUCTION
CANDIDATE_A = SELECTED_FOR_RECONCILED_WAVE3
WAVE3_FOCUSED_VERIFICATION = PASS
FULL_REPOSITORY_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
```
