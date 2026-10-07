# Autonomous Burst — Event-Driven Unattended Continuation

Status: **candidate implementation**  
Owner: **General Execution / Durable Execution**  
Diagnostic basis: **DE-DI-001**

## Purpose

Remove the hourly scheduler from the critical path of already-admissible continuation without weakening the existing atomic Durable Execution runtime.

The model is:

```text
hourly watchdog / provider completion event / bounded heartbeat
    -> fresh evidence
    -> Autonomous Burst
        -> one exact existing-style atomic transition
        -> persist
        -> fresh evidence
        -> next exact atomic transition
        -> ...
    -> stop at gate / wait / ceiling / safety bound
```

The hourly wake remains a recovery watchdog. It is no longer treated as the maximum engine speed.

## What remains unchanged

Autonomous Burst does not modify the safety meaning of `resume_tick` or the persistent runtime:

- one state-changing step = one exact admitted transition;
- one committed transition advances exactly one generation;
- stale state is rejected;
- duplicate evidence remains replay-safe;
- authority is consumed, never created;
- no paid spend is created;
- constitutional, credential, provider and target-owned gates remain binding.

The burst driver sits **above** the atomic runtime. It must not turn one tick into a multi-transition transaction.

## Continuity Check

Continuity Check remains read-only.

A `CHECKPOINTED_RESUMABLE` verdict may be normalized into an admissible burst observation. A progressing/wait/gate/done/failure verdict stops or parks the burst. The burst owns no Continuity Check mutation path and Continuity Check owns no dispatch path.

## Event vs heartbeat

For asynchronous work:

1. provider-native completion event is preferred;
2. if no reliable completion event exists and the operation is genuinely long-running, a bounded heartbeat may re-observe;
3. the reference fallback heartbeat is 900 seconds;
4. heartbeat never becomes an authority source and never justifies duplicate dispatch.

The ChatGPT hourly automation limit is therefore not a reason to force 15-minute chat scheduling. Sub-hour observation belongs in an already-authorized native execution/provider layer when such a layer exists.

## Safety bounds

Candidate policy defaults:

- maximum 32 state-changing transitions per burst;
- maximum 900 seconds wall-clock burst lease;
- minimum 900 seconds heartbeat fallback.

Reaching a bound forces a full external reconciliation. It does not grant permission to continue.

## Stop reasons

The candidate fails closed at:

- active execution already observed;
- human authority gate;
- constitutional gate;
- paid-spend gate;
- credential gate;
- external-evidence gate;
- condition/scheduled wait;
- development stalled / failed / insufficient evidence;
- technical/canonical ceiling;
- burst transition or wall-clock bound.

## Authority

This candidate creates no merge, runtime repin, provider, credential, spend, release, consensus/economics or mainnet authority.
