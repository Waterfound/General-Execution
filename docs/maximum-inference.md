# Maximum Inference

Maximum Inference is a **pre-empirical discipline under Robust Premise**. It is not a new execution owner, scheduler, assurance authority, or replacement for physical evidence.

Its job begins only after Robust Premise has concluded that a physical test still appears necessary.

```text
Robust Premise
  -> residual uncertainty survives
  -> Maximum Inference
       -> stress models, assumptions, counterfactuals and predictions
       -> precommit interpretation and measurements
       -> reassess expected physical information gain
  -> Robust Premise re-entry when information gain collapses
  -> Physical Test only when a material reality gap remains
```

## Composition with Predictive & Sovereign Execution

Maximum Inference consumes existing Predictive & Sovereign Execution primitives rather than duplicating them.

PSE supplies side-effect-free predictive precomputation, gate forecasting, independent verification twins and capability substitution. Maximum Inference adds a stricter physical-test-oriented evidence contract around those primitives.

The distinction is:

- **PSE** prepares and verifies hypothetical future work broadly.
- **Maximum Inference** saturates the inference available for one proposed empirical/physical test and decides whether that test still has enough residual information gain to justify reality being queried.

## Required package

A strict Maximum Inference envelope binds:

- the exact target uncertainty and evidence predicate;
- at least two distinct model paths;
- explicit assumptions;
- quantitative prediction bands;
- sensitivity factors;
- counterfactuals;
- failure signatures;
- discriminating measurements;
- the irreducible reality gap;
- precommitted interpretation rules;
- the PSE or equivalent inference substrate references.

A package that omits model diversity, counterfactuals, failure signatures, discriminating measurements or precommitted interpretation is **INFERENCE_INSUFFICIENT**.

## Physical-test dispositions

`assess_maximum_inference` emits one of three dispositions:

- `INFERENCE_INSUFFICIENT` — the pre-empirical package is not yet strong enough to justify a physical decision.
- `RETURN_TO_ROBUST_PREMISE_REVIEW` — inference has reduced the reality gap or expected information gain enough that physical necessity must be reconsidered.
- `PHYSICAL_TEST_REMAINS_JUSTIFIED` — a material reality gap remains and expected information gain meets the precommitted threshold.

None of these dispositions dispatches physical work.

## Authority boundary

Maximum Inference hard-codes:

```text
simulation_evidence_only = true
empirical_validation_claimed = false
authority_created = false
execution_triggered = false
```

**Inference predicts reality; it does not certify reality.**

Simulated evidence cannot silently inherit empirical authority. A physical test remains an independent observation and must travel through the existing General Execution physical-attempt semantics.

## Feedback loop

The intended loop is deliberately bidirectional:

```text
Robust Premise -> Maximum Inference -> Robust Premise -> Physical Test
                          ^                    |
                          +--------------------+
```

If Maximum Inference reduces expected information gain below the configured threshold, the test is returned to Robust Premise rather than executed by inertia.

## Failure modes explicitly prevented

- simulation laundering into empirical claims;
- post-hoc reinterpretation after seeing physical results;
- repeated physical tests whose information gain has already collapsed;
- single-model confidence masquerading as inference saturation;
- physical dispatch hidden inside planning;
- authority creation through predicted future state.
