# Work-Sparse Unattended Execution

Status: candidate extension to General Execution, stacked on EAC-01. It is not a new meta-system.

## Purpose

Keep regular ChatGPT conversations as the human control room while allowing bounded execution to continue between user messages without making Work the default execution substrate.

The controller solves only one problem:

```text
durable state + existing authority + current work
    -> cheapest admissible executor
    -> existing launch/admission path
```

It does not itself execute work.

## Executor preference

The deterministic ordering is:

1. non-Work before Work;
2. free before paid;
3. lower declared cost rank;
4. lower estimated monetary cost;
5. stable executor id tie-break.

This intentionally makes Work a scarce capability executor rather than a routine reasoning backend.

```text
scheduled ChatGPT wake
  -> read durable state
  -> existing execution? observe only
  -> cheap API/GitHub/Build Colony route available? prefer it
  -> only Work has required capability?
       -> use Work only if explicit Work budget remains
  -> authority boundary? HUMAN_GATE
  -> no capability/current availability? CONDITION_WAIT
```

## Authority envelope

`UnattendedAuthorityEnvelope` binds:

- exact authority reference;
- repositories that may be considered;
- explicitly allowed actions;
- explicitly forbidden actions;
- maximum Work invocations;
- maximum paid spend.

Unknown actions fail to `HUMAN_GATE`. The controller never treats silence as authorization.

Every decision fixes:

```text
authority_created = false
execution_triggered = false
```

A `DISPATCH` decision means only that an executor is the preferred **next admission target**. EAC-01 / existing execution admission remains responsible for real activation.

## Work avoidance

Work is selected only when:

1. it matches the required capability;
2. no admissible non-Work executor is preferable;
3. the explicit Work invocation budget has not been exhausted.

With `max_work_invocations=0`, a Work-only task becomes `CONDITION_WAIT`; it is not silently escalated into Work.

This allows a regular-chat / scheduled-task controller to perform most wakes, GitHub/Build Colony/API operations to perform most execution, and Work to remain available for true browser/UI/cloud-computer capability gaps.

## Persistent runtime

General Execution already has a real provider-triggered unattended pilot and a persistent runtime branch. This candidate composes with those existing primitives; it does not replace their state machine, authority-stop behavior, or restart safety.

## Stacked dependency

This candidate is stacked on EAC-01 because the preferred-executor result should eventually feed the existing receipt-bound executor activation lineage. It does not merge or modify PR #16.

## Acceptance criteria

The candidate is GREEN when:

- a non-Work executor is selected over Work when both can satisfy the task;
- Work is selected only for a Work-only capability and an explicit positive Work budget;
- zero Work budget fails closed;
- paid execution cannot exceed the explicit spend envelope;
- existing native execution is observed instead of redispatched;
- forbidden/unknown actions and authority/repository mismatches stop at `HUMAN_GATE`;
- unavailable/missing capabilities become `CONDITION_WAIT`;
- replay detects executor/authority/execution-claim tampering;
- full General Execution regression remains green;
- EAC-01 remains unchanged and green.
