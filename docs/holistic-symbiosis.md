# Holistic Symbiosis Composition

This module composes existing General Execution contracts without replacing their ownership.

Flow:

```text
Steward predictive bundle
  -> Work-Sparse executor selection
  -> PSE evidence-preserving capability substitution
  -> Provider Portability resource routing when required
  -> existing execution admission / EAC path
  -> Durable receipts / Continuity Check
```

The composition layer is side-effect free. It never launches an executor, creates provider authority, widens budgets, changes credentials, merges canonical state or promotes an independent-verification result by itself.

## Agreement rule

A dispatch-ready result requires the Work-Sparse executor and the PSE substitution method to identify the same method. If that method is provider-bound, Provider Portability must also select an existing allowed and available resource. No eligible provider resource means fail-closed defer.

## Steward support

The same module exposes a predictive bundle that composes:

- safe precomputation;
- future-gate forecasting;
- secret-free recovery-capsule construction.

Independent assurance uses the existing PSE verification-twin reconciliation contract.

This is a binder/composition surface, not another scheduler or state owner.
