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

The public engine composes generic selection contracts rather than requiring knowledge of the private system registry.

Its input is a **minimal capability projection** containing only opaque candidate aliases, opaque capability identifiers, execution capability, deterministic cost rank, and digests binding the projection to one private registry revision and authority context.

The engine may then compose:

1. cheapest-admissible-executor preference;
2. evidence-equivalent capability substitution;
3. provider-resource routing when a provider route is required;
4. an existing execution admission surface;
5. a persistent execution owner.

The public engine is not itself compute. If a preferred executor is unavailable, another already-authorized executor may be selected only when it satisfies the same evidence predicate.

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

If one GitHub Actions resource class is known to be exhausted:

```text
private_repo_actions
  resource = UNAVAILABLE
  cause = CAPACITY
  cause_code = included_minutes_exhausted

public_repo_standard_runner / connector / local / provider-neutral candidate
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

## Public mechanism / private intelligence

The public engine deliberately does not require a full internal system inventory.

A private authority domain may keep real system identities, rich capability semantics, dependency topology, fallback policy, authority ceilings and planning rationale private, then emit a task-scoped projection such as:

```text
projection_id = p_<16-hex>
candidate_id = c_<16-hex>
capability_ids = k_<16-hex>[]
execution_capable
cost_rank
authority_ref_digest
registry_revision_digest
```

All candidates supplied for one decision must bind the same projection, registry revision and authority digest. The request itself also precommits the expected `projection_id`, `registry_revision_digest` and `authority_ref_digest`. A candidate set that is internally consistent but does not match the request binding fails closed.

The public result contains only the opaque aliases it was given. It cannot reconstruct the private registry, infer absent capabilities, or create new candidate identities.

## Core invariant

> **Before declaring execution unavailable, resolve the cause of unavailability and attempt every evidence-equivalent admissible executor.**

This rule never permits weakening the evidence predicate, widening authority, creating paid spend, changing credentials, bypassing provider controls, or treating an advisory result as observed execution.


## Resource scope

Capacity observations are scoped to the concrete executor/resource class.

For example, exhaustion of included minutes for private-repository GitHub-hosted runners does not imply that every GitHub Actions execution path is unavailable. A public-repository standard runner may remain admissible under GitHub's public-repository runner policy.

The protocol therefore rejects global statements such as `github_actions = unavailable` when the evidence only proves a narrower resource class is exhausted. Resource observations should be as specific as the available evidence permits.


Semantic names are intentionally invalid in the public projection fields. A caller cannot use an internal system name as `candidate_id` or a human-readable internal capability name as `capability_id`; those inputs are rejected by schema validation.
