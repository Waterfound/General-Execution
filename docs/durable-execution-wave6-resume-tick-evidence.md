# Durable Execution Wave 6 — Resume/Tick Runtime Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 6 implementation head before this evidence commit:

```text
2d8b37b3b449edd7aa24f682b7c1c302103fe287
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

Wave 5 executable evidence remains pending. Wave 6 is therefore implemented behind an explicit fail-closed verification interlock and is not authorized for unattended execution.

## Runtime model

`src/general_execution/resume_tick.py` implements a deliberately short-lived invocation model:

```text
recover durable portfolio
-> verify Wave 5 execution gate
-> request next external work OR admit one exact observation
-> apply at most one authorized transition
-> atomically commit portfolio + checkpoint
-> cold-recover and verify exact committed state
-> terminate
```

The runtime does not maintain a long-lived model session, daemon identity, or chat dependency.

## Core verification interlock

Wave 6 cannot invoke the ASP transition engine unless a `CoreVerificationReceipt` satisfies an explicit `CoreVerificationRequirement`.

The requirement binds:

- exact Wave 5 target revision;
- exact regression suite reference;
- exact verifier reference;
- minimum test count.

The receipt binds:

- tested revision;
- suite reference;
- evidence artifact reference + digest;
- verifier;
- execution time;
- PASS status;
- test count.

A generic or unrelated PASS is insufficient.

Current intended Wave 5 frozen target:

```text
8f6494eca2c730de49b2e6ebfeb085cad1f33744
```

This preserves:

```text
unexecuted transition core
!=
runtime execution authority
```

## Observation contract

A `ResumeTickObservation` is bound to:

- exact portfolio id;
- exact expected generation;
- exact expected state digest;
- exact transition policy digest;
- event;
- admitted checkpoint evidence;
- action reference;
- observed time;
- summary;
- canonical references;
- optional uncertainty set;
- optional Passive wake admission;
- optional bounded transition authority grant.

The observation has a deterministic digest, stable id, and checkpoint reference.

A stale observation cannot mutate a newer durable head.

## No-input behavior

When the verification gate is open but no observation is available, the runtime returns:

```text
external_input_required
requested_work_id=<current Active>
requested_action_ref=<current Active next_action_ref>
```

This is the provider-neutral bridge between durable state and a future executor/trigger adapter.

The core does not embed Render, GitHub, AWS, Vercel, ChatGPT, or other provider-specific execution logic.

## Human authority behavior

If the current Active is at `human_gate`, a no-observation tick returns:

```text
external_input_required
human_required=true
requested_work_id=<Active>
requested_action_ref=<authority action>
```

It does not auto-continue.

## Idempotency

Each admitted observation is injected into the checkpoint canonical refs as:

```text
tick-observation:<observation-digest>
```

Immediate replay of the same observation returns:

```text
already_applied
```

with no generation advance.

The runtime is also hardened for concurrent duplicate invocation:

1. two identical ticks race from the same durable head;
2. one writer commits first;
3. the second writer loses CAS;
4. the second recovers the new head;
5. if the recovered checkpoint contains the same tick observation ref, the second returns `already_applied`, not a false divergence.

A competing *different* observation returns `stale_observation`.

## Durable commit

A successful tick must:

- advance exactly one generation;
- produce a different state digest;
- atomically persist portfolio + checkpoint through the Wave 4 store;
- cold-recover the state;
- recover the exact same checkpoint;
- verify the recovered state equals the transition result.

The returned `ResumeTickResult` binds:

- pre/post generation;
- pre/post state digest;
- checkpoint digest;
- transition result digest;
- recovery report digest.

## Regression bank

`tests/test_resume_tick.py` contains 13 focused cases covering:

1. verification receipt rejects FAIL/zero-test/malformed revision;
2. closed gate cannot mutate even with no observation;
3. wrong tested revision keeps gate closed;
4. suite/verifier/minimum-test requirement binding;
5. open gate with no observation requests explicit next work;
6. observation is bound to transition policy digest;
7. one tick advances exactly one generation and cold-recovers;
8. immediate replay is idempotent;
9. concurrent duplicate commit resolves as `already_applied`;
10. stale observation cannot mutate current head;
11. human-gate transition commits an authority stop;
12. post-human-gate tick requests human input instead of continuing;
13. observation identity is deterministic and state-bound.

## Static audit

The actual branch was inspected after Wave 6 hardening.

Required structures were present:

```text
CoreVerificationRequirement                  PRESENT
CoreVerificationReceipt                      PRESENT
ResumeTickObservation                        PRESENT
ResumeTickResult                             PRESENT
resume_tick                                  PRESENT
explicit requested_work_id                   PRESENT
explicit requested_action_ref                PRESENT
human_required stop                          PRESENT
immediate replay idempotency                 PRESENT
concurrent replay idempotency                PRESENT
stale observation stop                       PRESENT
policy binding                               PRESENT
core requirement provenance                  PRESENT
core verification provenance                 PRESENT
```

Public API exports are present for all Wave 6 types/functions.

## Execution boundary

No executable PASS is claimed for Wave 6.

The same infrastructure limitation that blocks exact Wave 5 execution also prevents legitimate Wave 6 execution evidence:

- the local runtime cannot resolve/materialize the private GitHub repository;
- the alternate Python sandbox rejects ordinary source/module features before General Execution code executes.

Because Wave 6 explicitly depends on Wave 5 executable evidence, bypassing this limitation would violate the frozen evidence-first gate.

## Correct status

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = FOCUSED_PASS
F2_EXECUTION_CHECKPOINT = FOCUSED_PASS
F3_TRANSITION_POLICY = FOCUSED_PASS
F4_PORTFOLIO_PERSISTENCE = FOCUSED_PASS
F5_BOUNDED_RETRY_AUTHORITY = FOCUSED_PASS

F6_ASP_TRANSITION_ENGINE = IMPLEMENTED
F6_STATIC_AUDIT = PASS
F6_EXECUTABLE_REGRESSION = PENDING_COMPATIBLE_PYTHON_RUNTIME

F7_RESUME_TICK_RUNTIME = IMPLEMENTED_BEHIND_INTERLOCK
F7_STATIC_AUDIT = PASS
F7_REGRESSION_BANK = 13 CASES WRITTEN
F7_EXECUTABLE_REGRESSION = BLOCKED_BY_F6_EXECUTION_GATE

FULL_REPOSITORY_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
UNATTENDED_RUNTIME = NOT_ENABLED
AUTHORITY_CREATED = false
```

## Next admissible work

The Build Colony sequence names `core-rehearsal` after the resume/tick runtime.

A real CORE-1 rehearsal MUST NOT start until the Wave 5 executable gate is green.

Useful development may continue only in forms that do not bypass that gate, such as:

- preparing a compatible exact-source execution harness;
- preparing the CORE-1 rehearsal fixture and expected evidence ledger;
- preparing provider-neutral trigger adapter contracts in a disabled/non-operational state only after CORE-1 design review.

The runtime itself must remain closed until exact executable evidence is admitted.
