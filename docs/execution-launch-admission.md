# ELG-01 — Explicit Execution Order -> Launch Admission Receipt

ELG-01 is a narrow General Execution contract at the boundary immediately before an executor-native launch.

## Canonical constitutional precondition

ELG-01 remains the low-level authority/executor admission primitive. The **system-level canonical launch path** is constitutionally governed before ELG-01.

For consequential autonomous work, `admit_constitutionally_governed_launch` requires a `ConstitutionalAssessment` bound to the exact `ExecutionLaunchOrder.digest` and to the canonical Catechism constitutional revision in `Waterfound/Systems`.

- `OUT_OF_SCOPE` and `COMPATIBLE` may continue to ELG-01.
- `INTERPRETATION_REQUIRED` stops before launch.
- `INCOMPATIBLE` is rejected before launch and is not converted into an ordinary human authority override.

See [Canonical Constitution Gate](canonical-constitution.md).

It exists to make one state transition observable:

```text
explicit execution order
    -> persistent launch order
    -> immutable launch admission receipt
    -> executor-native launch / first substantive artifact
```

It does not listen to conversations, decide project policy, create authority, dispatch a provider, run Build Colony, run Project Assurance, or mutate Continuity Check state.

## Ownership

The contract lives in General Execution because General Execution already owns provider-neutral execution identity, execution mechanics and crash/recovery semantics after authority exists.

It does not live in:

- Build Colony: its Run Manifest starts after a Profile + immutable source revision exists, and its Envelope AdmissionReceipt explicitly does not authorize execution.
- Project Assurance / Red Team: domain-specific executor.
- Durable Execution: downstream consumer of already-materialized events.
- Continuity Check: read-only observer.
- CII / DI: advisory and diagnostic systems.
- System Interoperability Envelope / ECL: stateless cross-system binder with no scheduler, retry ledger or native execution state.

The Envelope/ECL may remain useful provenance input. It is not the ELG-01 state owner.

## Contract

An `ExecutionLaunchOrder` binds:

- workstream identity;
- owner;
- repository;
- intended executor;
- objective and immutable order reference;
- optional source revision;
- required authority scopes;
- a bound authority statement when scopes are required;
- an executor availability/evidence binding;
- an already-known first artifact when one exists.

The host must authenticate the exact order bytes/digest and actor before calling admission. ELG-01 does not infer authority from conversation memory.

The immutable `ExecutionLaunchReceipt` has exactly one disposition:

- `ADMITTED`
- `HUMAN_GATE`
- `REJECTED`
- `FAILED_BEFORE_LAUNCH`

`ADMITTED` always contains:

- `workstream_id`;
- owner/repository/executor binding;
- deterministic `launch_id`;
- deterministic `dispatch_identity`;
- exact first artifact reference when already available;
- authority and executor evidence digests where applicable.

If no first artifact exists yet, `recovery_required=true`. This is an explicit resumable checkpoint, not a claim that the executor started.

Every receipt fixes:

```text
authority_created = false
execution_triggered = false
```

The executor remains responsible for consuming the admitted dispatch identity and producing its own native run/session/artifact evidence.

## Fail-closed rules

A structurally authentic order is handled as follows:

| Condition | Disposition |
| --- | --- |
| Complete identity + sufficient existing authority + executor available | ADMITTED |
| Required authority absent or insufficient | HUMAN_GATE |
| Owner/repository/executor identity missing or substituted | REJECTED |
| Executor unavailable or no executor capability evidence | FAILED_BEFORE_LAUNCH |

An unauthenticated/tampered order is not an admissible order and is rejected by the host before a receipt is accepted.

## Idempotency and recovery

The identity is content-derived.

Exact replay of the same order reproduces the same receipt. If the exact receipt is already present, replay returns `ALREADY_RECORDED`.

A different order for an already-bound `workstream_id` fails closed. Retrying cannot silently create a second workstream or raise authority.

The canonical Git host uses an append-only order as the durable input boundary:

1. the order commit is persistent before admission;
2. if the host crashes before the receipt commit, replay regenerates the same receipt;
3. if the host crashes after the receipt commit, replay observes the existing receipt and does not duplicate it;
4. downstream executor failure cannot erase the launch receipt;
5. conversation termination cannot erase the launch receipt.

## Continuity Check

Continuity Check remains read-only.

A validated launch receipt is an evidence source, not an execution command:

- `ADMITTED` with no stronger execution evidence -> `CHECKPOINTED_RESUMABLE`;
- `ADMITTED` with exhausted bounded recovery -> `DEVELOPMENT_STALLED`;
- `HUMAN_GATE` -> `HUMAN_GATE`;
- `REJECTED` / `FAILED_BEFORE_LAUNCH` -> `FAILED`.

Stronger repository, Durable, Build Colony or provider evidence continues to take precedence. If no launch or other execution evidence exists, `INSUFFICIENT_EVIDENCE` remains valid.

Therefore Continuity Check can diagnose an admitted launch that has not produced its first substantive artifact without inventing progress or becoming an executor.

## Residual caller boundary

ELG-01 cannot make the ChatGPT conversation product itself emit a repository artifact. A caller that accepts an executable human order must materialize the normalized immutable `launch-orders/*.json` input (or an equivalent authenticated transport) before describing the work as launched.

This is intentionally a caller-integration requirement rather than a new global coordinator. Once the order is materialized, launch admission and recovery no longer depend on conversation continuity.
