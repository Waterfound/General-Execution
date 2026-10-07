# Governed Operator Plane V1

The Governed Operator Plane is a **read-only derived projection** over state and evidence already owned by Build Colony, General Execution, Continuity Check and other canonical systems.

It is not a new scheduler, durable runtime, evidence bus, authority service or global state database.

## Contract

V1 accepts a normalized snapshot containing exact immutable source bindings and operator lanes. Every lane must bind its repository and exact 40-hex revision to at least one declared source artifact.

The projection is deterministic and emits:

- source bindings and provenance;
- ordered lanes/workstreams;
- current state/frontier;
- executor and dispatch identity when observed;
- blocking gate when observed;
- a deterministic timeline and state summary.

The output hard-codes:

```text
authority_created = false
execution_triggered = false
mutable_state_owned = false
```

Unknown control/action fields fail closed. V1 has no dispatch, retry, merge, provider mutation, credential, release or authority action.

## Ownership

- Build Colony continues to own engineering scheduling and serialized integration structure.
- General Execution continues to own launch admission, durable execution and recovery mechanics.
- Continuity Check continues to classify operational continuity.
- System Interoperability Envelope continues to bind consequential cross-system artifacts.
- The Operator Plane only projects evidence supplied by those owners.

A future action-capable surface, if ever justified, must compile actions into existing owner contracts rather than execute directly.
