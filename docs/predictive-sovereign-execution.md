# Predictive & Sovereign Execution

This candidate adds five side-effect-free planning and verification primitives to General Execution:

- predictive precomputation;
- sovereign recovery capsule construction;
- gate forecasting;
- independent verification twin reconciliation;
- capability substitution.

The module does not dispatch work, merge state, mutate providers, create credentials or authorize spend.

## Authority rule

Every primitive is advisory or preparatory. A predicted future branch is not an observed fact. A verification twin cannot promote canonical state. A substitute method must satisfy the exact same evidence predicate inside the current authority envelope.

## Recovery rule

Recovery capsules contain references, digests and reconstruction steps only. Secret material is rejected.

## Substitution rule

The selector may prefer a cheaper execution/proof method only if:

- it covers the same evidence predicate;
- its authority refs are already active;
- it meets minimum evidence quality;
- it fits the paid-spend ceiling;
- it is currently available.

Unknown or weaker equivalence defers fail-closed.
