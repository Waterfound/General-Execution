# Continuity Check V1

Continuity Check is a **thin read-only protocol/tool inside General Execution / Durable Execution**. It is not an independent system.

> **conversation interruption ≠ development interruption**
>
> **conversation still open ≠ development progressing**
>
> **Evidence before status. Memory suggests. Evidence decides.**

## Responsibility

Continuity Check answers one operational question: given a workstream that may appear interrupted in chat, what does persistent execution evidence say about the actual development state?

It resolves the workstream, validates the evidence binding, reconstructs the current operational state, emits a deterministic development verdict, and recommends the subsystem/action that should handle the next step. It never performs that next step.

## Read-only boundary

Continuity Check may inspect normalized evidence from repositories, branches, commits, PRs, Durable Execution, Build Colony, provider/runtime observations, canonical ledgers and conversation context. It may classify and render.

It may not push, merge, dispatch, retry, restart Durable Execution, change portfolio state, create provider resources, grant authority, approve gates, alter consensus, or release anything. Machine-readable reports hard-code authority_created=false and execution_triggered=false.

## Evidence sources and precedence

Frozen V1 precedence, strongest first:

1. canonical runtime / provider evidence;
2. canonical repository state;
3. validated Durable Execution state;
4. validated Build Colony state;
5. canonical project ledger/state;
6. recent conversation context.

This ordering is applied with semantic guards rather than blind ranking. In particular, a provider failure is infrastructure evidence and does not automatically become a development failure. Canonical repository closure outranks a stale runtime file that still claims ACTIVE.

Evidence is rejected when it is not bound to the resolved workstream, repository, branch or relevant revision. A provider run from the wrong SHA, copied Durable state from another branch, or an ambiguous workstream resolution fails closed.

## Freshness rules

V1 deliberately has no global "N minutes without a commit = stalled" threshold.

Freshness comes from the execution contract:

- frontier-specific timing expectations;
- explicit wake conditions;
- scheduled checkpoints;
- provider-operation semantics;
- bounded recovery semantics;
- validated progress timestamps attached to relevant evidence.

DEVELOPMENT_STALLED therefore requires an admissible frontier, sufficient authority/no gate, an expectation of execution, **and explicit evidence that the bounded recovery/heartbeat semantics are exhausted**. Elapsed time alone cannot produce the verdict.

Old GREEN CI alone is not current progress. An open PR alone is not current progress. Conversation timestamps are auxiliary only.

## Orthogonal model

Conversation assessment is separate from development verdict.

Conversation assessment:

- CONVERSATION_ACTIVE_OBSERVED
- CONVERSATION_INTERRUPTION_SUSPECTED
- CONVERSATION_STATE_UNKNOWN

Development verdict:

- DEVELOPMENT_PROGRESSING
- CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED
- CHECKPOINTED_RESUMABLE
- CONDITION_WAIT
- SCHEDULED_WAIT
- HUMAN_GATE
- EXTERNAL_EVIDENCE_GATE
- DONE_TECHNICAL
- DONE_CANONICAL
- DEVELOPMENT_STALLED
- FAILED
- INSUFFICIENT_EVIDENCE

The special CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED verdict is used only when interruption is suspected and stronger execution evidence can be temporally placed after the last observed conversation point.

## Decision semantics

The decision engine applies these semantic gates:

1. canonical integration evidence -> DONE_CANONICAL;
2. exact unsatisfied human gate -> HUMAN_GATE;
3. exact unsatisfied external-evidence gate -> EXTERNAL_EVIDENCE_GATE;
4. validated scheduled checkpoint -> SCHEDULED_WAIT;
5. validated observable wake condition -> CONDITION_WAIT;
6. explicit workload/target failure -> FAILED;
7. technical terminal verdict not yet canonically integrated -> DONE_TECHNICAL;
8. active dispatch/provider execution -> progressing verdict (with conversation-continuation specialization when provable);
9. validated admissible frontier with no active run -> CHECKPOINTED_RESUMABLE, unless bounded recovery exhaustion proves DEVELOPMENT_STALLED;
10. otherwise -> INSUFFICIENT_EVIDENCE.

This is not a simple status priority list: conversation state is orthogonal, provider infrastructure status is separate, and stale/mismatched evidence is excluded before classification.

## Adapters

continuity_adapters.py converts provider-neutral normalized mappings into typed evidence objects. Transport-specific collectors can be layered outside the decision core as long as they preserve read-only semantics and bind evidence to repository/branch/revision.

V1 does not add a daemon or global state database.

## Resolver

A human workstream name can resolve against canonical names, IDs and aliases. Exact normalized matches win. Partial matching is accepted only when it produces one unique workstream. Ambiguity or no match -> INSUFFICIENT_EVIDENCE.

## Human renderer

render_report() intentionally emits a compact operational report: workstream, conversation assessment, development verdict, repository/branch/SHA, PR if present, Durable frontier/next admissible, blocking gate, infrastructure status and recommended action.

## Machine-readable schema

Canonical report schema: schemas/continuity-check-v1.schema.json.

The report contains no execution capability. recommended_action is advisory and does not create authority.

## CLI

The repository provides a provider-neutral read-only entry point:

    PYTHONPATH=src python scripts/run_continuity_check.py --input normalized-evidence.json --format text
    PYTHONPATH=src python scripts/run_continuity_check.py --input normalized-evidence.json --format json

The CLI consumes normalized evidence; evidence acquisition remains an adapter concern. This keeps V1 stateless, deterministic and provider-neutral.

## Historical replay policy

Real histories may be replayed only from evidence that already exists. Replays are not allowed to rewrite historical truth or fabricate missing provider/chat observations. Synthetic cases cover verdicts whose exact historical source set is unavailable.

The V1 evidence package includes real repository replay cases for:

- FAE Representative Device Evidence Readiness canonical merge;
- FAE Block Explorer BE-06 Oracle OUT_OF_HOST_CAPACITY condition wait;
- Waterfound Systems documentation closure where GitHub Actions/provider unavailability did not prevent provider-neutral verification and canonical integration.

## Relationship to other systems

- **Durable Execution** resumes/continues work. Continuity Check only observes and may recommend RESUME_DURABLE_EXECUTION.
- **Human Authority Bridge** owns real human authority transitions. Continuity Check only reports exact gates.
- **Diagnostic Intelligence** investigates why a real failure occurred. Continuity Check only emits FAILED / INVESTIGATE_FAILURE when failure evidence is explicit.
- **Total Systems Steward** owns portfolio reconciliation. Continuity Check may set canonical_state_reconciliation_recommended=true; it does not edit Steward state.
- **Build Colony** may supply execution graphs/frontiers/terminal verdicts. Continuity Check consumes them read-only.

## Acceptance criteria

V1 closes only when terminology, evidence precedence/freshness, verdict taxonomy and schema are frozen; resolver/adapters/decision engine/renderer are implemented; all primary verdicts are tested; false-progress, stale-state, revision-binding and provider-neutral failure cases fail closed; historical replays pass; the read-only/authority boundary is mechanically represented; General Execution integration is verified; and the corresponding Systems documentation is integrated without creating a new system.

Terminal technical verdict: CONTINUITY_CHECK_V1_READY.
