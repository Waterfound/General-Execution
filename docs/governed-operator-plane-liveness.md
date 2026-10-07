# Governed Operator Plane — liveness evidence hardening

This candidate adds a provider-neutral **preprocessing adapter** for liveness evidence consumed by Continuity Check.

It deliberately does not change the frozen Continuity Check decision core. The adapter converts explicit provider/runtime observations into the existing ProviderEvidence and DurableStateEvidence surfaces.

## Invariants

- no elapsed-time threshold can manufacture a stalled verdict;
- provider unavailability remains infrastructure evidence, not workload failure;
- recovery exhaustion can contribute to DEVELOPMENT_STALLED only when an already validated Durable frontier exists;
- exact workstream, repository and 40-hex source-revision bindings fail closed on mismatch;
- liveness never creates authority, dispatches work, retries a provider or mutates canonical state;
- a heartbeat/progress observation may prove active execution, but silence alone proves nothing.

This is observation hardening, not a health-manager service or new state owner.
