# WRM — GitHub Bounty Claimability Preflight Screen

Date: 2026-10-24  
State: `PROBLEM_CONFIRMED / DIRECT_FREE_SUBSTITUTES / PAID_DEMAND_ABSENT / CANDIDATE_KILLED`  
Observed Waterfound revenue: **USD 0**

## Narrow job considered

Given one public GitHub bounty issue, determine before implementation whether it is still plausibly claimable by checking:

- canonical issue state;
- archived or inactive repository state;
- remaining reward capacity;
- prior payment or accepted solution;
- active issue-specific pull requests and attempts;
- issuer repudiation or program termination;
- objective acceptance contract;
- payout authority versus a stale marketplace badge;
- prompt-injection, labor-harvesting and promotional-token warnings.

The output would be a deterministic `GO / CAUTION / NO_GO / INSUFFICIENT_EVIDENCE` evidence packet. No issue comment, claim, account or payment would be required for the check.

## Problem evidence

The mission directly observed repeated false positives:

- an Opire page kept an issue open after its USD 100 reward was already paid and no reward remained;
- another Opire listing pointed to an archived repository with no usable acceptance contract;
- Algora-visible rewards diverged from maintainer statements that the bounty program had ended;
- open boards exposed completed, contested or multiply implemented work;
- fresh GitHub “bounties” offered self-issued promotional tokens or non-monetary points.

A public complaint in Algora’s own repository also reports contributors completing work and being ignored or encountering bounties effectively reserved for insiders.

Sources:

- https://github.com/algora-io/algora/issues/174
- https://app.opire.dev/issues/01K85DT037D90AJ1AJ79VBX21K
- https://app.opire.dev/issues/01KSXXX60RR76RSSXZXD0F4AGF

This establishes coordination waste and payment-authority ambiguity. It does not establish willingness to pay Waterfound for a preflight.

## Direct substitutes

The proposed product boundary is already covered by public tools:

1. **bounty-check**
   - free, MIT-licensed CLI;
   - reads canonical GitHub issue state;
   - checks archived repositories and competing open pull requests;
   - explicitly targets Algora, Opire and IssueHunt false-open records.
   - https://github.com/wren-castellan/bounty-check

2. **agent-trap-db**
   - advertises free first-hand trap intelligence and a zero-dependency preflight;
   - targets labor harvesting, throwaway organizations, merge-gated traps and prompt injection.
   - https://github.com/johnanleitner1-Coder/agent-trap-db

3. **Algora Bounty Scout**
   - filters public Algora/GitHub work for assignment, saturation and inactivity;
   - available as an installable agent skill.
   - https://mcpmarket.com/tools/skills/algora-bounty-scout

4. **Algora Bounty Radar**
   - read-only safety, funding and competition filters;
   - offered at usage pricing, but public statistics show zero monthly active users and no ratings at inspection.
   - https://apify.com/sebarb/algora-bounty-radar/issues/open

The mission’s own public screening adds issue-side payment-authority reconciliation and explicit unknowns, but this is incremental packaging around an already available free baseline.

## Commercial evidence classification

| Predicate | Result |
| --- | --- |
| Pain exists | Confirmed by repeated stale, contested and repudiated listings |
| Machine-admissible inputs | Yes; public GitHub/platform state |
| Technical capability | Ordinary; no build needed to prove |
| Direct substitutes | Multiple, including free/open source |
| Observable paid demand for exact preflight | None |
| Existing paid substitute adoption | No useful evidence; sampled paid radar reports zero MAU |
| Differentiation | Insufficient |
| WTT/WTP for Waterfound | None |
| Revenue | USD 0 |

## Decision

Kill the standalone GitHub bounty-claimability product before build.

Preserve the admission checks as an internal commercial-selection method only. Do not create another CLI, dashboard, API, x402 endpoint, scoring model, watch service or marketplace wrapper.

Re-enter only if one of these occurs:

1. an autonomous buyer explicitly requests issue-side payment-authority reconciliation beyond existing tools;
2. a representative paid channel exposes machine-readable escrow and claim state that existing tools fail to reconcile;
3. an observable buyer pays for a specific missing output, not merely bounty discovery;
4. a distribution surface can validate willingness to try without a new human-operated account.

No code, account, wallet, publication, outreach, claim, proposal, payment/KYC, spend or Privacy P0 activation occurred.
