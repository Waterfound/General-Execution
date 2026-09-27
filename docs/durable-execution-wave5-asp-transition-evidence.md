# Durable Execution Wave 5 — ASP Transition Engine Evidence

## Candidate

Branch:

```text
feature/durable-asp-portfolio-state
```

Wave 5 implementation head before this evidence commit:

```text
161f4222ca8bd21e1fc2bfa911db89ea7101e3d2
```

Canonical base remains:

```text
ccc616ea77e6345b6fa3c61448cf17958fefba3d
```

The branch is strictly ahead of the canonical base and remains unmerged.

## Implemented engine

`src/general_execution/asp_transition.py` is the first Durable Execution frontier allowed to construct a new `PortfolioState`.

It consumes:

- the exact current `PortfolioState`;
- an explicit `TransitionPolicy`;
- one uniquely matched `TransitionRule`;
- admitted `CheckpointEvidence`;
- an optional bounded `TransitionAuthorityGrant`;
- for rotating transitions, a current-portfolio `PassiveWakeAdmission`.

It produces:

- generation + 1 `PortfolioState`;
- exact predecessor digest binding;
- an `ExecutionCheckpoint` bound to the new state;
- a deterministic `PortfolioTransitionResult`.

It does not schedule future invocations, call providers, invoke DI, verify its own work, integrate code, release software, spend money, or create authority.

## Core ASP semantics

### Ordinary transition

A non-rotating rule may advance the Active lifecycle only when the exact state/event rule exists and all required evidence is present.

No rule match means STOP.

### Verified completion

```text
Active VERIFYING
+ verification_passed
+ verifier_pass evidence
+ valid current Passive wake admission
    ->
old Active leaves the live portfolio as completed evidence
old Secondary -> Active READY
woken Passive -> Secondary READY
remaining Passive entries preserved
```

The core does not invent a replacement Secondary.

### External blocker parking

```text
Active WAITING_EXTERNAL
+ external_blocker evidence
+ no_internal_work evidence
+ valid current Passive wake admission
    ->
old Active -> Passive
old Secondary -> Active READY
woken Passive -> Secondary READY
```

The parked Active must already carry a blocker and explicit wake condition.

### Passive wake

A Passive does not become selectable merely because a caller claims it is ready.

`admit_passive_wake` binds:

- exact portfolio id/generation/state digest;
- exact passive work id;
- exact current wake-condition digest;
- exact policy/rule digest;
- full admitted evidence;
- optional bounded authority grant.

The wake evidence and authority are revalidated again when a rotation consumes the admission.

A stale admission cannot be replayed after portfolio state changes.

### Human authority gate

A `human_required` rule transitions to `human_gate`, records an authority blocker, produces an authority-stop checkpoint, and declares no automatic next transition.

The engine explicitly rejects a grant supplied before the human gate is reached.

### Pre-authorized transitions

A `preauthorized_required` rule requires an externally supplied `TransitionAuthorityGrant` bound to the exact:

- policy digest;
- rule digest;
- authority boundary;
- authority artifact reference/digest.

The engine consumes that authority; it does not create it.

## Authority hardening discovered during Wave 5

The first implementation draft allowed a caller to supply an arbitrary new Secondary entry during a rotation.

That would have allowed the ASP core to accept work selection without the future Build Colony / Thin Envelope provenance boundary.

The design was therefore tightened before promotion:

```text
external Secondary selection in core = REJECTED
rotation source = current Passive + validated wake admission only
```

External candidate selection remains a later integration concern.

A second audit found that the first wake-admission draft retained only evidence digests. That proved identity but did not permit evidence-kind revalidation at consumption.

It was tightened to retain the full admitted evidence and bounded authority grant. The rotation engine now revalidates both.

## Regression bank

`tests/test_asp_transition.py` currently contains 18 focused regression cases covering:

- ordinary state advance + checkpoint binding;
- missing evidence fail-closed;
- unmatched transition fail-closed;
- verified Secondary promotion;
- no invented Secondary;
- rejection of external Secondary selection;
- Active parking only with `no_internal_work` evidence;
- missing parking evidence rejection;
- human authority stop;
- rejection of premature authority grant;
- exact bounded preauthorization;
- explicit Passive wake proof;
- woken Passive filling the Secondary slot;
- wake evidence revalidation at consumption;
- wake authority revalidation at consumption;
- stale wake admission rejection;
- atomic portfolio/checkpoint commit + cold recovery;
- input-state immutability.

## Static branch audit

The actual GitHub branch was inspected after the hardening.

All required source checks were present:

```text
admit_passive_wake                          PRESENT
apply_active_transition                     PRESENT
wake evidence revalidation                  PRESENT
wake authority revalidation                 PRESENT
external Secondary rejection                PRESENT
verifier_pass mandatory evidence            PRESENT
no_internal_work mandatory evidence         PRESENT
wake_condition_satisfied evidence           PRESENT
human-before-authority stop                 PRESENT
rotating result binding                     PRESENT
```

All six new public API symbols are exported:

```text
AspTransitionError
PassiveWakeAdmission
PortfolioTransitionResult
TransitionAuthorityGrant
admit_passive_wake
apply_active_transition
```

## Execution attempts and boundary

Two independent execution paths were attempted.

### Local container

The local runtime cannot resolve `github.com`, so it cannot clone/materialize the private repository directly.

### External Python sandbox

The exact GitHub source was fetched through the authorized GitHub connector and prepared for execution in a separate Python sandbox.

That sandbox rejected the loader before running project code because its policy prohibits Python features used by normal module loading / the source itself, including:

- `exec` / `compile`;
- `sys.modules`;
- `@property`;
- `getattr`.

These are sandbox-policy rejections, not General Execution test failures.

Therefore no executable PASS is claimed for Wave 5 in this evidence record.

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
F6_REGRESSION_BANK = 18 CASES WRITTEN
F6_EXECUTABLE_REGRESSION = PENDING_COMPATIBLE_PYTHON_RUNTIME

FULL_REPOSITORY_REGRESSION = NOT_RUN
MAIN_INTEGRATION = NOT_AUTHORIZED
AUTHORITY_CREATED = false
```

Wave 5 is code-complete enough to preserve and review, but it does not satisfy the Build Colony `asp-transitions` evidence gate until the exact candidate is executed in a compatible Python environment.

## Next frontier boundary

The Build Colony sequence names `resume-tick-runtime` next.

It MUST NOT be promoted as an executable runtime on top of an unexecuted Wave 5 candidate.

The admissible next work is therefore:

1. obtain a compatible execution surface for the exact Wave 5 SHA;
2. run `test_asp_transition.py` plus the earlier focused banks;
3. run the full General Execution regression bank when possible;
4. only after Wave 5 execution evidence is GREEN, implement the short-lived idempotent resume/tick runtime.

This preserves evidence-before-status and prevents the automation layer from outrunning its verified transition core.
