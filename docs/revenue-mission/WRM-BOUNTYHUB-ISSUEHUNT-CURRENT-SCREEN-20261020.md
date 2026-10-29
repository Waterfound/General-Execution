# WRM screen — BountyHub and IssueHunt current public bounties

**Screened:** 2026-10-20  
**Decision:** `REJECT_AS_ACTIVE_REVENUE_CHANNEL / WATCH_ONLY`  
**Mission state:** `NO_PRODUCT_SELECTED` / revenue USD 0

## Commercial predicate

Can Waterfound move closer to first revenue by completing a currently open, publicly inspectable, funded software task without customer credentials, paid spend or speculative unpaid work?

## Platform evidence

### BountyHub

BountyHub states that:

- bounties may be prepaid or only promised for payment after a solution;
- claims are submitted by importing a GitHub pull request;
- the creator reviews and accepts or rejects the claim;
- a merged pull request can support a dispute, but payment is not automatic;
- the platform advertises payout coverage in more than 120 countries.

Sources:

- https://www.bountyhub.dev/
- https://www.bountyhub.dev/docs/claim-bounty

### IssueHunt

IssueHunt describes an issue-based OSS bounty platform. The searchable public inventory observed in this wake was dominated by old rewarded items, unfunded current issues and stale funded tasks.

Sources:

- https://oss.issuehunt.io/
- https://github.com/IssueHunt/readme

## Candidate reconciliation

| Candidate | Nominal reward | Canonical issue state | Commercial result |
|---|---:|---|---|
| CrewAI + Memanto integration | USD 100 | Closed; multiple attempts/submissions visible | Reject: completed/contested |
| SuperPlane Docker Hub base integration | not reliably exposed in static page | Closed; assignee; project status Done | Reject: completed; BountyHub marked promise rather than prepaid |
| React Native Gifted Chat `bottomOffset` Android bug | not reliably exposed in static page | Closed | Reject: not actionable |
| Electron macOS package filtering regression | USD 100 reported by external census | Closed; linked fix/PR | Reject: completed |
| Caster accessibility integration | USD 200 | Funded but two pull requests already submitted | Reject: saturated and stale |
| IssueHunt current repository samples | mostly USD 0 | current visible issues unfunded; funded search results commonly years old or already rewarded | Reject: no verified open funded fit |

Canonical issue sources:

- https://github.com/moorcheh-ai/memanto/issues/37
- https://github.com/superplanehq/superplane/issues/2243
- https://github.com/FaridSafi/react-native-gifted-chat/issues/2469
- https://github.com/electron/electron/issues/48191
- https://oss.issuehunt.io/r/dictation-toolbox/Caster

## Decision rationale

The channel fails the current admission predicate:

1. no sampled task is both open and commercially uncontested;
2. some BountyHub rewards are promises rather than prepaid funds;
3. creator acceptance remains a payout dependency;
4. available nominal rewards do not justify speculative implementation against closed, assigned or already-submitted work;
5. opening an account or claiming a task would not repair the missing opportunity.

Decision: `REJECT_AS_ACTIVE_REVENUE_CHANNEL / WATCH_ONLY`.

No account, OAuth grant, claim, issue comment, fork, pull request, external submission, payout onboarding or public commitment occurred. Revenue remains USD 0.

## Re-entry criteria

Re-screen only when a task is independently verified as:

- open in the canonical repository;
- funded in advance or protected by a sufficiently strong payout mechanism;
- unassigned and without an accepted or materially equivalent pull request;
- technically bounded with objective acceptance criteria;
- compatible with Waterfound's demonstrated capability and truthful provenance;
- worth the expected implementation and coordination cost.
