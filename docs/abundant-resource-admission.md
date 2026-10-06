# Abundant Resource Admission

Status: candidate extension to General Execution. No authority expansion.

## Purpose

Classify resource capacity before executor routing:

```text
existing authority
 + resource economics evidence
 + declared capability/capacity
 -> abundant-resource admission
 -> existing execution/scheduling layers
```

An admitted resource has **zero incremental monetary cost**, no automatic paid fallback, explicit evidence, declared capacity, and identity/capabilities already inside the authority envelope.

The admission is side-effect free:

- `authority_created=false`
- `execution_triggered=false`
- `incremental_paid_spend_cents=0`

It does not replace Work-Sparse. Work-Sparse remains responsible for conservative executor preference when resources are scarce. This contract simply lets later layers know which resources may be treated as abundant rather than compute-minimized.

## Fail-closed boundaries

The following are never abundant automatically:

- paid execution;
- unknown billing state;
- included allowance with automatic paid fallback;
- unavailable capacity;
- resources outside the authority envelope;
- capabilities outside the authority envelope;
- capacity that would exceed the global declared parallelism envelope.

The contract does not mutate provider declarations to squeeze them into remaining capacity; it rejects partial admission and requires an explicit bounded offer instead.
