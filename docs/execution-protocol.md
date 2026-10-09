# Execution Protocol

Execution Protocol is the canonical **Total Systems Steward decision protocol** for deciding whether a system should be invoked, which system composition is appropriate, whether the invocation is advisory or a real run, and which currently admissible executor may satisfy the exact evidence predicate.

It is a protocol, not a new system or execution owner.

## Decision pipeline

```text
Intent
  -> Evidence Predicate
  -> System Selection
  -> Execution Mode
  -> Resource Cause Resolution
  -> Executor Selection
  -> PSE Capability Substitution
  -> Provider Portability when provider-bound
  -> Existing Launch / Admission
  -> Durable Execution
```

The protocol never skips directly from “preferred executor failed to start” to “provider failure” when a stronger resource cause is already observable.

## Invocation modes

The protocol emits exactly one invocation mode:

- `NO_SYSTEM` — the requested result does not require a formal system.
- `ADVISORY` — one or more systems guide the decision without claiming a real execution or newly observed evidence.
- `REAL_RUN` — one execution-capable owner is required to produce observed evidence or state change.
- `COMPOSED_REAL_RUN` — multiple system capabilities are required and at least one selected owner is execution-capable.

“Advisory” is not a weaker synonym for “run.” It is a different epistemic mode.

## System selection

The Steward supplies current system capabilities. Execution Protocol chooses the smallest deterministic capability-covering set, breaking ties by declared cost rank and stable system id.

No coverage means `CONDITION_WAIT`; it does not invent another system or silently widen an owner’s mandate.

## Resource cause resolution

An executor that is unavailable must have a resolved resource observation before the protocol may use that fact to block or reroute.

Recognized classes include:

- capacity;
- credential / reauthentication;
- provider availability;
- paid-resource boundary;
- time;
- external evidence;
- unknown.

An executor declared unavailable without a cause is invalid protocol input.

This makes the following distinction mechanical:

```text
runner_id=0 + zero steps
    + known included-minutes exhaustion
    -> CAPACITY
    -> attempt admissible substitution
    -> CONDITION_WAIT only if no equivalent method remains
```

A known capacity exhaustion must not be downgraded to an unexplained workload or provider failure.

## Executor substitution

Execution Protocol composes existing owners rather than replacing them:

1. **Work-Sparse** preserves cheapest-admissible-executor preference.
2. **PSE Capability Substitution** requires the same evidence predicate and minimum evidence quality.
3. **Provider Portability** selects only already-authorized available provider resources when a provider route is required.
4. **General Execution** remains the execution composition/admission surface.
5. **Durable Execution** persists the admitted execution and its receipts.

General Execution is not itself compute. If GitHub Actions is unavailable, General Execution may route through another already-authorized executor only when that executor can satisfy the same evidence predicate.

## Terminal dispositions

Execution Protocol may return:

- `NO_SYSTEM_REQUIRED`;
- `ADVISORY_READY`;
- `READY_FOR_EXISTING_ADMISSION`;
- `OBSERVE_EXISTING`;
- `CONDITION_WAIT`;
- `HUMAN_GATE`.

A ready route still does not mean execution occurred.

The protocol hard-codes:

```text
authority_created = false
execution_triggered = false
```

The existing launch/admission owner remains responsible for real activation.

## GitHub Actions exhaustion example

Suppose the evidence predicate is “run the deterministic verification suite with equivalent inputs, environment requirements and output assertions.”

If GitHub Actions is known to be exhausted:

```text
github_actions
  resource = UNAVAILABLE
  cause = CAPACITY
  cause_code = included_minutes_exhausted

connector/local/provider-neutral candidate
  resource = AVAILABLE
  same evidence predicate = YES
  authority = already active
  paid spend = 0

=> substitute and continue through General Execution admission
```

If the candidate method proves a weaker proposition, lacks required environment semantics, needs new credentials, or introduces unauthorized spend:

```text
=> substitution rejected
=> CONDITION_WAIT / HUMAN_GATE as appropriate
```

## Relationship to other systems

Execution Protocol does not change ownership:

- Total Systems Steward owns protocol invocation and portfolio-level choice.
- Build Colony structures bounded engineering work.
- Work-Sparse owns executor preference.
- PSE owns evidence-equivalent capability substitution.
- Provider Portability owns provider-resource routing.
- General Execution owns bounded execution composition/admission.
- Durable Execution owns persistent execution state.
- Project Assurance independently challenges high-value claims.
- Continuity Check remains read-only.

## Core invariant

> **Before declaring execution unavailable, resolve the cause of unavailability and attempt every evidence-equivalent admissible executor.**

This rule never permits weakening the evidence predicate, widening authority, creating paid spend, changing credentials, bypassing provider controls, or treating an advisory result as observed execution.
