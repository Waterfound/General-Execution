# Durable Execution Wave 3 — Checkpoint + Transition Policy Evidence

## Candidate lineage

Parent frontier:

```text
feature/durable-asp-portfolio-state
04fa50aefd6edfd5fb554bb604a1f0832d4ec591
```

Wave 3 candidate:

```text
feature/durable-asp-checkpoint-transition-policy
8883fd3fcad757cc036977c911f8dbaab88d1b00
```

The candidate is strictly ahead of F1 and does not modify `main`.

## Implemented contracts

### transition_policy

`src/general_execution/transition_policy.py` introduces:

- `AdmittedEvidence`
- `TransitionRule`
- `TransitionPolicy`
- `TransitionRequest`
- `TransitionDecision`
- deterministic policy/request/decision serialization;
- deterministic decision reproduction;
- fail-closed evidence requirements;
- explicit authority-reference consumption;
- canonical one-rule-per-match-key semantics.

The policy contract decides whether a transition is admissible. It does **not** mutate portfolio state, dispatch work, retry providers, verify results, integrate revisions, or create authority.

### execution_checkpoint

`src/general_execution/execution_checkpoint.py` introduces:

- `CheckpointCanonicalRef`
- `ExecutionCheckpoint`
- deterministic checkpoint serialization;
- exact binding to `portfolio_id`, generation, portfolio digest, work identity, entry digest, role/state, and source revision;
- admitted evidence preservation;
- canonical portfolio-state reference;
- canonical transition-policy reference when a next transition exists;
- explicit uncertainties;
- exactly one of:
  - a reproducible next transition decision, or
  - a fail-closed stop reason.

A checkpoint is evidence. It does **not** authorize the transition it records.

## Authority discipline

The contract distinguishes two authority cases:

1. **Entering a human gate** may be a mechanical safe stop. The rule names the authority boundary but does not require authority to stop.
2. **Leaving an authority gate** may require an immutable admitted `authority_ref`. The evaluator fails closed when that reference is absent.

The contract does not decide whether an authority artifact is semantically valid; that admission remains external. It only refuses to proceed when a policy says authority is required and no admitted immutable reference exists.

## ASP expressiveness without execution

Wave 3 can represent, but does not yet execute:

```text
Secondary READY -> Active READY
Active WAITING_EXTERNAL -> Passive PASSIVE
Active RUNNING -> VERIFYING
Active VERIFYING -> COMPLETE
Active * -> HUMAN_GATE
HUMAN_GATE -> resumed state only with required authority reference
```

Actual atomic portfolio mutation belongs to the later ASP transition-engine frontier.

## Verification

The current local container still cannot resolve `github.com`, so the full General Execution pytest bank was not executed from a repository clone.

The Wave 3 candidate logic was reconstructed in an isolated Python package from the inspected branch definitions and exercised with 24 focused behavioral checks.

Observed:

```text
24 / 24 PASS
```

Covered cases included:

- policy/request/decision canonical round-trip;
- deterministic decision reproduction;
- admitted evidence binding;
- missing evidence fail-closed;
- no matching rule fail-closed;
- ambiguous policy rejection;
- invalid role/state rejection;
- explicit human-gate boundary;
- authority reference required for authority-consuming rule;
- Active parking expressibility;
- Secondary promotion expressibility;
- checkpoint canonical round-trip;
- exact portfolio/entry binding;
- next-action preservation;
- canonical portfolio-state reference;
- canonical transition-policy reference;
- transition evidence preservation;
- fail-closed checkpoint stop;
- next-transition XOR stop-reason invariant;
- stale checkpoint rejection;
- tampered decision rejection.

Separately, the actual branch public API was inspected through GitHub and the required new exports are present.

## Verification boundary

This evidence supports continued stacked development, but not promotion to `main` by itself.

```text
F0_BASELINE_AUDIT = PASS
F1_PORTFOLIO_STATE = PASS_FOCUSED
WAVE3_TRANSITION_POLICY = PASS_FOCUSED
WAVE3_EXECUTION_CHECKPOINT = PASS_FOCUSED
FULL_REPOSITORY_REGRESSION = NOT_RUN_IN_CURRENT_RUNTIME
MAIN_INTEGRATION = NOT_AUTHORIZED
```

## Next frontier

Wave 4 may now proceed as two dependency-safe lanes:

1. `portfolio-persistence`
   - transactional durable portfolio head;
   - CAS / stale-write rejection;
   - checkpoint persistence and cold reload.

2. `bounded-retry-authority`
   - explicit retry classes;
   - bounded counts/backoff representation;
   - assertion/unknown/security/cost/authority stop behavior.

Neither lane may weaken the invariant:

> Execution consumes authority. It does not create authority.
