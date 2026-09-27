# Durable Execution CORE-1 Rehearsal Fixture

## Purpose

This fixture freezes the first empirical rehearsal that must pass before broader Durable Execution integration.

It is deliberately **not** a scheduler, provider adapter, or activation mechanism.

Its job is to answer one question:

> Can the minimum 1 Active + 1 Secondary + N Passive core progress, recover, rotate, stop, and replay safely without chat history?

## Prerequisite gate

CORE-1 must remain closed until an exact-source Vercel Sandbox conformance run for:

```text
04a47cd7031b608368de15ec2c99ccc715eb6cbf
```

is admitted through `CoreVerificationManifest -> CoreVerificationReceipt`.

This repaired target supersedes `8f6494eca2c730de49b2e6ebfeb085cad1f33744`,
which failed local full regression. The Vercel requirement is unchanged; see
`durable-execution-work-resumption-2026-09-26.md` for the failure and repair evidence.

Required verifier contract:

```text
suite_ref:
  tests://durable-execution/wave5-asp/full-repository

focused source:
  tests/test_asp_transition.py

minimum Wave 5 focused cases:
  18

verifier:
  verifier://vercel-sandbox-conformance/v1

full repository pytest:
  required
```

A generic PASS, different revision, different suite, different verifier, failed shutdown, or incomplete command sequence does not open the gate.

## Rehearsal execution model

Each scenario uses short-lived invocations only.

Between relevant steps, the harness must discard the initiating store/session object and reconstruct state from the durable database again.

No scenario may use chat history as input.

### Scenario A — cold resume + checkpoint reconstruction

1. Initialize generation 0.
2. Admit one exact tick observation.
3. Commit generation 1.
4. Destroy the initiating store/session object.
5. Create a new `SqlitePortfolioHeadStore` from the same durable path.
6. Run `recover_portfolio_after_restart`.
7. Prove exact state/checkpoint digests.

Required assertions:

- `cold_resume`
- `checkpoint_reconstruction`
- `no_chat_dependency`

### Scenario B — verified Secondary promotion

Start with:

```text
Active      = VERIFYING
Secondary   = READY
Passive A   = wake-eligible
Passive B   = dormant
```

Then:

1. Admit wake evidence for Passive A.
2. Admit `verification_passed + verifier_pass`.
3. Rotate.

Expected:

```text
old Secondary -> Active READY
Passive A     -> Secondary READY
Passive B     -> remains Passive
old Active    -> completed evidence, not silently re-enqueued
```

External arbitrary Secondary selection remains forbidden.

### Scenario C — externally blocked Active

Start with Active `WAITING_EXTERNAL` carrying a blocker and explicit wake condition.

Require:

- `external_blocker`
- `no_internal_work`
- one valid Passive wake admission.

Expected:

```text
blocked Active -> Passive
old Secondary  -> Active
woken Passive  -> Secondary
```

The parked Active must retain its wake condition.

### Scenario D — bounded retry

Exercise:

- network timeout ceiling;
- throttle backoff ceiling;
- deterministic assertion -> diagnose;
- unknown failure -> exactly one independent reproduction -> diagnose;
- cost boundary -> stop;
- security/authority boundary -> human gate.

No loop is allowed.

### Scenario E — stale and duplicate invocations

Race two identical tick observations from the same head.

Expected:

- exactly one generation commit;
- duplicate loser -> `already_applied`;
- no double execution.

Then submit a different observation bound to the old head.

Expected:

- `stale_observation`;
- no durable mutation.

### Scenario F — human authority stop

Drive Active to `human_gate`.

The committed checkpoint must contain:

```text
authority_stop = true
next_transition_refs = ()
```

A later no-observation tick must return:

```text
external_input_required
human_required = true
```

No authority artifact may be fabricated.

## Closed assertion set

CORE-1 cannot claim PASS unless every one of these assertions has durable evidence:

```text
bounded_retry
checkpoint_reconstruction
cold_resume
cost_security_authority_stop
duplicate_tick_idempotent
external_blocker_parking
human_gate_stop
no_chat_dependency
no_hidden_authority
passive_wake_admission
stale_write_rejected
unknown_failure_single_reproduction
verified_secondary_promotion
```

The `CoreRehearsalReport` rejects a missing assertion, duplicate assertion, fabricated GREEN, chat dependency, or any attempt to enable unattended runtime from the report itself.

## Promotion boundary

Passing CORE-1 proves the **minimum durable core only**.

It still does not authorize:

- merge to `main`;
- provider trigger activation;
- Build Colony/DI/Red Team broad integration;
- spending;
- release;
- mainnet;
- consensus/economics changes;
- credential-sensitive actions;
- unattended production runtime.

Those remain later explicit gates.
