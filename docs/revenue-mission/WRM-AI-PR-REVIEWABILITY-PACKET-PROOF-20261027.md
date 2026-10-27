# WRM-T1 AI PR Reviewability Packet — Narrow Proof

Date: 2026-10-27

Status: `GENERIC_LEDGER_FALSIFIED / NARROW_REVIEWABILITY_PACKET_PROVED_ON_SYNTHETIC_FIXTURES / DEMAND_AND_WTP_UNPROVEN`

## Commercial decision

The generic **Agent PR Recovery & Approval Ledger** is closed as an active wedge. GitHub, GitLab, and CodeRabbit already provide overlapping agent-session traceability, review-thread handling, automated review/approval signals, CI repair, and continuation of agent work. Rebuilding those functions would not establish a differentiated commercial job.

The remaining falsifiable job is narrower:

> Before a maintainer reviews an AI-authored pull request, produce a provider-neutral packet that separates completion claims from observed evidence, identifies unresolved review state and high-risk paths, preserves residual uncertainty, names the human post-merge owner, and emits one bounded next action.

This is a deterministic pre-review admission artifact. It is not a dashboard, code reviewer, approval substitute, recovery orchestrator, or claim that a change is safe.

## Candidate buyer and problem evidence

Candidate buyer: engineering leads and maintainers who review AI-authored contributions across more than one repository or forge.

Public evidence supports the problem direction, but not Waterfound demand:

- Linux Foundation reporting describes low-quality AI-generated contributions as a growing maintainer burden. This supports the existence of review-cost pressure; it does not prove demand for this packet.
- Atlassian's 2026 developer-experience reporting describes a gap between faster code production and unchanged or increased friction, with review, debugging, and correction remaining material work. This supports the coordination-cost hypothesis; it does not quantify savings from Waterfound.
- *Plausible Is Not Enough* reports higher evidence requirements and lower trust for AI-authored changes, especially under residual uncertainty and unclear ownership.
- *Who Pays the Review Cost?* frames bounded scope, validation, stewardship, and ownership as conditions for reviewable AI-generated contributions.
- *Early-Stage Prediction of Agent-Authored Pull Request Outcomes* finds both quickly merged and stalled/abandoned regimes, with structural early signals predicting review effort.

No interview, trial request, willingness-to-try, willingness-to-pay, or revenue evidence exists yet.

## Substitute reconciliation

| Substitute | Native capability observed | Consequence for WRM-T1 |
|---|---|---|
| GitHub Copilot coding agent | Session logs, commit-to-session traceability, draft PR workflow, code-review assessments, CI-fix/continuation flows | Generic session, recovery, and approval ledger is occupied |
| GitLab Duo Agent Platform | Code Review Flow plus merge-request conversations, thread resolution, and agent commits | Generic review-thread recovery is occupied |
| CodeRabbit | Review commands, fix generation, request-changes/approval automation, triage, and CI-fix flows | Generic automated reviewer/repair wedge is occupied |

Residual candidate differentiation is limited to the conjunction below:

1. provider-neutral input;
2. explicit `claim -> required check -> observed result` mapping;
3. unsupported claims kept separate from passing evidence;
4. residual uncertainty kept separate from hard blockers;
5. post-merge human ownership represented explicitly; and
6. one deterministic, bounded next action.

Any single item alone is not sufficient differentiation.

## Smallest proof

`tools/revenue_mission/pr_reviewability_packet.py` reads a small JSON export and emits `wrm.reviewability-packet.v1`. It performs no network calls and changes no pull-request state.

Two synthetic fixtures exercise the commercial predicate:

| Fixture | Expected outcome | Observed outcome |
|---|---|---|
| Passing check, resolved thread, targeted validation, session link, human owner | `REVIEWABLE` | `REVIEWABLE` |
| Unsupported completion claim, unresolved thread, high-risk workflow path, no owner or session | `BLOCK` with one bounded next action | `BLOCK`; missing `full-regression` evidence is first action |

Validation command:

```text
python -m unittest tests/test_pr_reviewability_packet.py -v
```

Observed result on 2026-10-27: two tests passed.

## Evidence classification

### Capability proved

- Deterministically maps declared claims to named checks.
- Separates verified and unsupported claims.
- Preserves unresolved review threads, high-risk paths, residual uncertainties, blockers, and human ownership.
- Produces a bounded disposition: `BLOCK`, `HUMAN_VERIFY`, or `REVIEWABLE`.

### Observed outcome

- The two synthetic fixtures produced their expected classifications.
- The negative fixture did not allow a passing lint check to stand in for a missing full-regression check.

### Not proved

- No real maintainer workflow has been measured.
- No operator minutes, latency reduction, avoided rework, autonomous-resolution rate, monetary value, demand, willingness-to-try, or willingness-to-pay is established.
- No superiority over a buyer's existing scripts or templates is established.
- No claim is made that `REVIEWABLE` means correct, safe, mergeable, or approved.

## Kill criteria

Close this wedge rather than expanding implementation if any of the following occurs:

1. a native GitHub, GitLab, or adjacent control-plane export already yields the same claim/evidence/uncertainty/owner decision without material coordination work;
2. the packet cannot add a distinct decision to a representative PR beyond native checks and review threads;
3. a valid representative fixture is falsely blocked because the schema cannot express its evidence;
4. required inputs cannot be obtained read-only without privileged installation or sensitive data expansion;
5. after an authorized external validation round, no qualified buyer reports the problem or willingness to try the packet; or
6. willingness-to-pay remains absent after provable workflow value exists.

## Next commercial-information step

Apply the same schema to a public PR export or a separately authorized representative Waterfound workflow. Measure only naturally observable facts: intent and terminal timestamps, machine transitions, genuinely required human interventions, observable active minutes, retries/rework/recovery, and provenance coverage. Compare the packet's bounded next action with the native control plane; do not invent a manual baseline.

External customer contact, installation into an external account, public commercial publication, pricing, payment/KYC, contracts, paid spend, and irreversible commitments remain outside this proof and require their existing gates.

## Sources

- GitHub Docs, “Managing and tracking agents,” accessed 2026-10-27: <https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents>
- GitHub Docs, “About code review,” accessed 2026-10-27: <https://docs.github.com/en/copilot/concepts/agents/code-review>
- GitLab Docs, “Code Review Flow,” accessed 2026-10-27: <https://docs.gitlab.com/user/duo_agent_platform/flows/foundational_flows/code_review/>
- CodeRabbit Docs, “Review commands,” accessed 2026-10-27: <https://docs.coderabbit.ai/guides/review-commands>
- *Plausible Is Not Enough: Empirical Evidence on Review Requirements for AI-Authored Code*, 2026: <https://arxiv.org/abs/2610.21144>
- *Who Pays the Review Cost?*, 2026: <https://arxiv.org/abs/2610.11179>
- *Early-Stage Prediction of Agent-Authored Pull Request Outcomes*, 2026: <https://arxiv.org/abs/2601.00753>

## Authority and accounting

- Revenue remains US$0.
- No price is proposed because value and willingness-to-pay are unproved.
- No outreach, account installation, publication, financial onboarding, contractual acceptance, or paid spend occurred.
- No Privacy P0 activation occurred.
- No global writer lease, state dispatcher, SQLite database, dispatcher bundle, or `DISPATCH_FENCE` was touched.
