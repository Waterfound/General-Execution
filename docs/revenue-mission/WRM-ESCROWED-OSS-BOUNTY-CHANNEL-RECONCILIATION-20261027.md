# WRM escrowed OSS bounty channel reconciliation — 2026-10-27

## Decision

- **ACTIVE commercial predicate tested:** whether a public, traditionally payable, pre-funded OSS bounty can support an immediate narrow private proof.
- **Result:** NO_CURRENT_BUILD_CANDIDATE / FEED-NOT-SOURCE-OF-TRUTH.
- **IssueHunt:** PASSIVE / CANONICAL-ISSUE-FIRST.
- **BountyHub and Algora discovery feeds:** SECONDARY / CANONICAL-ISSUE-FIRST.
- Revenue observed remains **US$0**.
- No implementation, attempt/claim comment, account creation, PR, outreach, payment, KYC, publication, spend, wallet, runtime activation, or Privacy P0 activation occurred.

## Why this frontier

The prior Opire screen established that a dollar card without escrow is not reliable demand. This wake tested the stronger predicate: a card explicitly represented as pre-funded/escrowed and payable through a platform. The cheapest proof is reconciliation against the canonical GitHub issue and the platform's own live state before cloning or building.

## Candidate reconciliation

### 1. IssueHunt — yewstack/yew #1946, “VComp is not mounted”, US$100

- IssueHunt still displays **US$100 funded** and offers PR submission:
  - https://oss.issuehunt.io/r/yewstack/yew/issues/1946
- The canonical GitHub issue is **closed**, fixed by #2094 on **2021-10-02**:
  - https://github.com/yewstack/yew/issues/1946
- **Verdict:** STALE_CARD / CLOSED_CANONICAL_ISSUE / NO_BUILD.

This directly falsifies the hypothesis that an apparently funded IssueHunt card is sufficient admission.

### 2. BountyHub — channel mechanics and current candidates

Official current platform material distinguishes:

- pre-paid bounties from merely promised bounties;
- creator acceptance from automatic payment on merge;
- Stripe payout in supported countries, with PayPal available when Stripe is unavailable;
- creator review remains the acceptance authority.

Source: https://www.bountyhub.dev/

Current indexed escrowed examples were reconciled before build:

- **Memanto Security Challenge, US$100 escrowed:** canonical issue is open but has 54 comments and multiple linked solution PRs; repository policy has also blocked external PR creation for at least one finished entry. SATURATED / ACCESS-RISK / NO_BUILD.
  - https://github.com/moorcheh-ai/memanto/issues/1852
  - https://github.com/bountyhub-org/platform/issues/1
- **Dott app, US$35 escrowed:** acceptance requires a live third-party Android app to unlock and ride, implying real account/device/location/SMS execution and multiple competing submissions. EXTERNAL-ACCOUNT-AND-PHYSICAL-PROOF / NO_PRIVATE-FIXTURE.
- **Threads, US$250 escrowed:** requires desktop and mobile implementation, so it is not a narrow proof. BROAD-SCOPE / NO_BUILD.
- **AzerothCore map partitioning, US$200 escrowed:** canonical issue was closed as not planned; maintainers describe the requested architecture as enormous foundational work. CLOSED / SCOPE-VALUE-MISMATCH.
  - https://github.com/azerothcore/azerothcore-wotlk/issues/22571

### 3. Algora discovery feed — stale and saturated listings

The current discovery feed labels items as escrowed, but canonical reconciliation found material lag:

- **tscircuit/pcb-viewer #163, US$3:** issue remains open but shows dozens of attempts/claims and completed/closed PRs; the remaining value is indistinguishable from stale bookkeeping. SATURATED / NO_BUILD.
  - https://github.com/tscircuit/pcb-viewer/issues/163
- **FinMind #130, US$250:** repository was archived on **2026-06-19**, is read-only, has hundreds of pull requests, and the issue lists many attempted solutions. ARCHIVED / SATURATED / NO_BUILD.
  - https://github.com/rohitdash08/FinMind/issues/130
- **ZIO #9211, advertised US$150:** canonical discussion states that Algora shows **zero open ZIO bounties** as of 2026-10-15 and already contains a tested optimization prototype. FUNDING-NOT-CONFIRMED / EXISTING-SOLUTION.
  - https://github.com/zio/zio/issues/9211
- **Gyroflow #150, advertised US$200:** the canonical issue shows the bounty label removed on **2026-10-12** and multiple current solution attempts, including commits on 2026-10-25 and 2026-10-27. BOUNTY-REMOVED / SATURATED.
  - https://github.com/gyroflow/gyroflow/issues/150

## Commercial information gained

1. Escrow materially improves settlement credibility, but **does not prove that work remains available**.
2. Public aggregator/platform browse pages are discovery inputs only. Canonical issue state, bounty-label state, repository writability, current attempts/PRs, acceptance criteria, and payout eligibility must all agree.
3. The dominant failure mode is now stale/saturated supply, not missing instrumentation.
4. No code should be built for a card merely because it is marked funded or escrowed.

## Admission gate for any future OSS bounty

All must be independently true before build:

1. canonical issue open and not already solved;
2. explicit pre-funded/escrowed status still present on the canonical issue or live platform record;
3. repository accepts external PRs;
4. objective acceptance test and scope small enough for a bounded private proof;
5. no merged/equivalent solution and no excessive active competition;
6. traditional payout compatible with Brazil;
7. expected reward exceeds conservative implementation and proof cost;
8. no live-account, physical-world, public-contact, credential-expansion, paid-spend, or wallet prerequisite for the proof.

## Kill and reactivation criteria

- **Kill a candidate immediately** on closed/archive state, removed funding, contradictory amount/status, broad multi-platform scope, duplicate solution, saturated attempts, access restriction, or proof requiring unauthorized external action.
- **Reactivate the channel** only when a newly updated canonical issue passes the complete admission gate above.
- A listing/aggregator timestamp alone is not reactivation evidence.

## Unknowns preserved

- BountyHub does not publicly enumerate a definitive country-by-country payout list on the cited landing page; Brazil compatibility must be verified before any claim.
- Some platform cards may refresh asynchronously after canonical resolution.
- A low-competition escrowed issue may still exist outside indexed results; absence was not proven globally.
