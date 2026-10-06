# Receipt-Bound Work Escalation Bridge

Status: candidate extension stacked on Persistent Auth Lease (PR #18), Work-Sparse Unattended Execution (PR #17), and EAC-01 (PR #16).

## Purpose

Close the gap between:

```text
Work-Sparse selects Work
```

and:

```text
a real provider-native ChatGPT Work execution exists
```

without making Work the default executor and without inventing a Work launch when the platform has not produced one.

A real Build Colony frontier study selected the receipt-bound design over direct controller-to-Work triggering and a generic long-lived Work daemon.

Build Colony evidence:

- study branch: `research/work-escalation-bridge-001`;
- decision digest: `869a478b1f1a182640910d4578d54b4ad3e8779d5fb367b31d5f40510b052cf1`;
- selected candidate: `candidate-b-eac-work-bridge`;
- selected utility: 8790 bp;
- direct-trigger alternative: 4442 bp;
- generic-daemon alternative: 3530 bp;
- CI run `37496517834`: SUCCESS;
- remote-pool-ci run `37496517862`: SUCCESS.

The optimizer fixed `authority_created=false` and `execution_authorized=false`.

## Execution chain

```text
Work-Sparse DISPATCH(work)
  -> explicit WorkInvocationAuthority
  -> deterministic WorkEscalationRequest
  -> atomic durable budget reservation
  -> ELG-01 execution launch order
  -> ADMITTED receipt + dispatch_identity
  -> WorkPlatformActivationRequest
  -> provider/platform adapter
       PLATFORM_WAIT             -> bridge waits
       HUMAN_REAUTH_REQUIRED     -> auth://<provider>/reauthenticate
       PLATFORM_ACCEPTED         -> native Work execution ref
       FAILED_ACTIVATION         -> fail closed
  -> only terminal provider execution evidence enters EAC-01
  -> executor_accepted / failed_activation
```

The bridge does not itself call or emulate ChatGPT Work.

## Work authority and budget

A Work escalation requires two independent facts:

1. Work-Sparse selected `work` under an envelope with positive Work budget.
2. A `WorkInvocationAuthority` exists with explicit `work_invocation` and `executor_activation` scopes.

The usable budget is the smaller of the envelope budget and the explicit Work authority budget.

`SqliteWorkEscalationStore` reserves slots transactionally. One deterministic request replays to the same slot. A second concurrent request cannot exceed the durable limit even if a caller's in-memory usage snapshot was stale.

A reserved slot is conservative: it represents one admitted escalation lineage, not proof that the provider consumed a Work quota unit.

## Pre-launch identity

Before any provider side effect, the system has durable identities for:

- Work item;
- Work-Sparse routing decision;
- authority reference/digest;
- envelope digest;
- budget slot;
- ELG-01 launch receipt;
- EAC dispatch identity;
- Work platform activation request.

Every pre-launch artifact fixes:

```text
authority_created = false
execution_triggered = false
```

This is the crash/replay boundary that the direct-trigger alternative lacked.

## Platform capability boundary

The candidate intentionally distinguishes **the bridge** from **the platform activator**.

`WorkPlatformActivationRequest` is the exact artifact a future ChatGPT Work activation surface must consume. It binds the EAC dispatch identity and durable budget reservation.

Until the platform returns a provider-native observation, the system must not claim that Work ran.

If no callable Work activation primitive is available to the unattended controller, the honest terminal state is:

```text
PLATFORM_ACTIVATION_CAPABILITY_GATE
```

not a fabricated execution.

## Authentication composition

A provider/platform response can return:

```text
HUMAN_REAUTH_REQUIRED
condition_ref = auth://<provider>/reauthenticate
```

That stays in the Work bridge and composes with Persistent Auth Lease. It does not prematurely terminalize EAC-01.

After the user authenticates and the platform produces new evidence, the same Work request, budget slot, launch receipt, and dispatch identity continue.

No password, MFA value, cookie, bearer token, API key, or browser session payload is stored here.

## EAC-01 admission

Only `PLATFORM_ACCEPTED` or an actual `FAILED_ACTIVATION` observation is converted into terminal EAC evidence.

`PLATFORM_WAIT` and `HUMAN_REAUTH_REQUIRED` remain bridge-local so the same request can later resume. This avoids making EAC's terminal `condition_wait` state prevent later activation.

The `ExternalWorkExecutorActivationAdapter` never launches Work. It only binds an already-observed provider-native result to the exact EAC dispatch identity.

## Current activation status

This candidate proves the machine-side control plane and external adapter contract. It does **not** prove that this ChatGPT environment exposes a programmatic primitive capable of launching a Work task from the regular-chat scheduled controller.

Therefore a GREEN candidate can still end at:

```text
WORK_ESCALATION_BRIDGE_READY__REAL_WORK_PLATFORM_ACTIVATION_CAPABILITY_EXTERNAL_GATE
```

until such a platform action is available and evidence-bound.

No merge, release, paid spend, credential mutation, physical action, consensus/economics change, or mainnet authority is created by this candidate.
