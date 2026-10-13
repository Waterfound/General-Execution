# WRM — Public bounty claimability screen for first revenue

Date: 2026-10-13. Status: REAL POSTED REWARD SIGNAL / NO WATERFOUND CLAIM, CUSTOMER OR REVENUE.

Scope: public-source research only. No account creation, bounty claim, issue comment, fork, external pull request, payment onboarding, KYC, outreach, spend, release, merge or runtime change.

## Commercial question

Can a currently open public software bounty provide a lawful, bounded, machine-admissible path to Waterfound's first revenue using public inputs and objective acceptance criteria?

This screen distinguishes four predicates that bounty directories often collapse:

1. a monetary reward is advertised;
2. Waterfound is eligible to receive it;
3. the job is technically bounded enough to attempt at positive expected value;
4. the payout route is available and may be entered under existing authority.

Only the first predicate was observed. The other three failed or remain unresolved for the inspected candidates.

## Candidate observations

### Recall Homebrew package — technically narrow, economically ineligible

AsherJN/recall issue #30 was opened on 2026-10-13 and advertises a USD 10 Ko-fi bounty for a Homebrew formula/cask plus copy-paste installation instructions. It permits AI assistance and has no comments. However, the issue explicitly states that the bounty goes to repository owner AsherJN even if another contributor implements the feature.

Source: https://github.com/AsherJN/recall/issues/30

Decision: **REJECT_FOR_REVENUE**. This is evidence of a specific user's willingness to spend USD 10 on packaging convenience, but not a payable opportunity for Waterfound. Do not implement it for revenue.

### microG WearOS — explicit agent prohibition and physical-test requirement

microg/GmsCore issue #2843 advertises a USD 2,340 reward, but its current issue text requires maintainer acceptance, testing against recent physical WearOS devices and explicitly forbids AI coding agents from engaging. The issue reports prior bad-faith AI claims.

Source: https://github.com/microg/GmsCore/issues/2843

Decision: **INADMISSIBLE**. Do not engage, implement, comment or claim.

### microG RCS — real reward, unbounded/high-contention scope

microg/GmsCore issue #2994 advertises USD 14,999 for current Google Messages RCS support without root and with locked-bootloader compatibility. As inspected on 2026-10-13, the issue is open with 703 comments and has an open implementation attempt. It requires protocol/carrier compatibility and device-level validation, not a narrow public-fixture task.

Sources:
- https://github.com/microg/GmsCore/issues/2994
- https://github.com/microg/GmsCore/pull/3508

Decision: **REJECT_FOR_BOUNDED_PROOF**. The reward is meaningful demand evidence for the feature, but the scope, validation burden and competition make an autonomous speculative implementation commercially unsound.

### Fluxer bounties — posted budgets, broad product scope, promised funds

BountyHub currently lists Fluxer Polls at USD 500, Events/Calendar at USD 500 and Threads at USD 800. The linked issue descriptions require multi-surface implementations across desktop, mobile and server or explicitly require a single full-stack contribution. BountyHub marks the inspected amounts as **Promised**, not paid in advance, and the listings prohibit fully AI-generated submissions.

Sources:
- https://www.bountyhub.dev/en/bounty/view/4d7c4070-412c-44b4-a0d9-b1d2ef926d04/polls-dev-bounty-dollar500
- https://www.bountyhub.dev/en/bounty/view/86d87f7b-622c-448d-8f88-cb71630db2a5/events-calendar-dev-bounty-dollar500
- https://www.bountyhub.dev/en/bounty/view/f35ef17a-ca1f-4a5a-a12e-762def0aee45/threads-dev-bounty-dollar250

Decision: **REJECT_FOR_CURRENT AUTONOMOUS FIRST-REVENUE PATH**. These are buyer-spend signals, not safe small jobs. Scope, acceptance, human authorship expectations and non-prepaid funding all materially reduce expected value.

## Payout and authority boundary

BountyHub's claim documentation requires GitHub sign-in, a matching GitHub account for the public PR, a submitted claim, merge or creator discretion, and payout onboarding. Its supported-country page does not list Brazil for Stripe Connect as inspected on 2026-10-13; its pricing page separately says PayPal is available for unsupported countries. Therefore Brazilian payout may be possible, but the exact payable path is **UNVERIFIED** and cannot be assumed.

Sources:
- https://www.bountyhub.dev/en/docs/claim-bounty
- https://www.bountyhub.dev/en/supported-countries
- https://www.bountyhub.dev/en/pricing

Account creation, public contribution, claim submission and payment/KYC remain genuine later human/authority gates. They are not current blockers because no candidate passed the technical and economic screen.

## Ratchet decision

**DO NOT promote public-bounty implementation to ACTIVE from the inspected set.** The set proves that external actors attach money to specific software outcomes, but it does not produce a claimable, bounded first-revenue job for Waterfound.

Route admission requires one live candidate satisfying all of:

- reward payable to the actual external contributor, not a named third party;
- AI-assisted participation permitted and compatible with the user's role;
- funded/escrowed reward or independently credible payer history;
- public, lawful fixture and objective acceptance test;
- scope small enough for a bounded implementation and verification cycle;
- no active accepted-equivalent implementation or excessive contention;
- payout path available to Waterfound's jurisdiction;
- no customer secrets, paid access, hardware purchase or new credentials needed for the proof;
- public PR, account and payment onboarding deferred until a candidate patch passes locally and the bounded gate is worth presenting.

Kill a candidate immediately when any hard criterion fails; do not add orchestration around it.

## Evidence state

- Buyer/problem evidence: **SUPPORTED for several exact open-source feature outcomes**.
- Posted willingness to pay: **OBSERVED at USD 10, USD 500, USD 800, USD 2,340 and USD 14,999 candidate levels**, with important eligibility/funding caveats.
- Claimable Waterfound opportunity: **NONE SELECTED**.
- Narrow product/service proof: **NOT STARTED; admission failed before code**.
- Waterfound willingness-to-try, customer, contract, payment and revenue: **UNVERIFIED / USD 0**.
- Generic bounty-board monitoring infrastructure: **SUPPORT_ONLY**; additional instrumentation would not cure eligibility, scope or payout defects.

Next machine-admissible action is to screen newly posted bounties or other public paid jobs against the admission criteria, prioritizing funded, objective, low-contention tasks. Do not notify or seek a human gate until a candidate survives the read-only screen and a private patch/test proof is complete.
