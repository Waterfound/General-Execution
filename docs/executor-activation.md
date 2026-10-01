# EAC-01 — Receipt-Bound Executor Activation Handoff

EAC-01 closes one narrow boundary left intentionally open by ELG-01:

```text
explicit order
  -> ELG-01 ADMITTED receipt
  -> durable activation_unknown checkpoint
  -> executor-specific idempotent adapter
  -> native executor evidence
  -> EXECUTOR_ACCEPTED / CONDITION_WAIT / FAILED_ACTIVATION
```

It does **not** create a new global coordinator. General Execution owns only the provider-neutral activation lineage and crash/replay semantics. Build Colony, Project Assurance, or another executor keeps its native run/session/artifact semantics.

## Authority boundary

EAC-01 consumes only an existing `ADMITTED` ELG-01 receipt. It does not accept `HUMAN_GATE`, `REJECTED`, or `FAILED_BEFORE_LAUNCH`, and every EAC-01 artifact fixes `authority_created=false`.

`ADMITTED != EXECUTING`.

`EXECUTOR_ACCEPTED` requires a native execution reference bound to the exact `dispatch_identity`.

## Crash safety and idempotency

The durable store commits `activation_unknown` **before** invoking the native adapter. A process crash can therefore leave ambiguity about whether the executor side effect occurred. EAC-01 resolves that ambiguity by making idempotent replay by `dispatch_identity` a mandatory executor-adapter capability.

A compliant adapter must return the same native execution lineage when the same `dispatch_identity` is replayed. It may reconcile an already-created run; it must not launch a second run.

## Outcomes

- `EXECUTOR_ACCEPTED` — native executor evidence exists; a native run/session reference is mandatory.
- `CONDITION_WAIT` — the executor cannot currently accept work; no native execution is claimed.
- `FAILED_ACTIVATION` — an explicit activation failure was observed; no native execution is claimed.

An adapter exception after `activation_unknown` is deliberately left recoverable rather than converted into a fabricated terminal outcome. The next process may replay the same idempotent activation.

## Experiment boundary

The first EAC-01 implementation is a bounded contract experiment. It proves:

- one native launch for one `dispatch_identity`;
- exact replay does not create another native launch;
- crash before or after the native side effect can recover the same identity;
- non-ADMITTED receipts never invoke an executor;
- executor unavailability becomes explicit `CONDITION_WAIT`;
- authority cannot be created by the handoff.

A production Build Colony or Project Assurance adapter remains executor-owned and must independently prove the same idempotency/evidence contract before live activation is admitted.
