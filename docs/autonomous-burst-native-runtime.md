# Native Persistent Runtime Adoption Candidate

Status: **candidate only — not active on the persistent runtime**

AB-NRA-001 wires the canonical Autonomous Burst primitive into a persistent
runtime host without changing the semantics of the atomic runtime core.

## Native host contract

A burst trigger is one immutable manifest. The manifest contains an ordered list
of immutable event references. Each reference binds:

- `burst-events/<event-id>.json`;
- the exact SHA-256 digest of that file.

The host validates the manifest's exact starting generation and state digest,
then processes each referenced event through the existing
`process_persistent_runtime_event()` function. After every committed event the
host performs a fresh durable recovery before considering the next event.

The host never creates the next event. It never manufactures evidence and it
never carries a human-authority grant.

## Why this is not batching

A burst can contain several events, but the existing runtime still sees them as:

```text
event 1 -> one atomic transition -> commit -> recover
event 2 -> one atomic transition -> commit -> recover
event 3 -> one atomic transition -> commit -> recover
...
```

The manifest is an orchestration envelope, not a multi-transition transaction.

## Fail-closed stops

The candidate stops immediately on:

- start generation/state mismatch;
- content-digest mismatch;
- unsafe event path;
- credential-shaped event data;
- bootstrap or other non-transition operation;
- portfolio mismatch;
- duplicate event identity;
- any non-committed event result;
- human gate;
- external/passive wait;
- DI/failure/terminal state;
- manifest exhaustion without fresh successor evidence;
- transition-count bound.

A partial burst is therefore durable and inspectable. A later continuation
requires a fresh manifest bound to the newly recovered state.

## Candidate GitHub host

The eventual host is designed to keep the existing
`durable-asp-persistent-runtime` concurrency group and Waterfound actor
boundary. It materializes the exact burst manifest and referenced event bytes
from the trigger commit before switching to the latest runtime-state head.

The candidate workflow is deliberately stored under `runtime-candidates/`, not
`.github/workflows/`, so this development wave cannot activate it.

## Activation boundary

This candidate does **not** authorize:

- copying the host workflow into the live runtime path;
- changing `PERSISTENT_RUNTIME_REVISION`;
- changing the runtime branch;
- adding provider credentials/resources;
- new paid spend.

Those remain the final promotion/repin gate.
