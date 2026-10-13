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


## Same-day recheck: compatible assets and source-state verification

A second screen on 2026-10-13 tested whether the first pass had missed a smaller software-only or already-owned-hardware opportunity.

### Objective hardware recipe bounties — valid format, unavailable equipment

sybil-solutions/local-ai-registry issues #216–#223 each advertise USD 50 on merge for a tested local-model recipe and specify six objective checks. The published targets are Intel Arc B580, GTX 1080 Ti, RTX 2080 Ti, RX 7900 XTX, selected AMD 16 GB cards, RTX 4060 Ti 16 GB, RTX 5060 Ti 16 GB and Radeon 890M. None matches Waterfound's available MacBook M1, iPhone/iPads or Steam Deck. The previously returned RTX 2070 is also not a target.

Sources:
- https://github.com/sybil-solutions/local-ai-registry/issues/216
- https://github.com/sybil-solutions/local-ai-registry/issues/223

Decision: **REJECT_WITHOUT_SPEND**. These are unusually clear acceptance tests, but completing them requires unavailable hardware. No purchase, rental, borrowing or fabricated benchmark is admissible.

### Copperhead end-to-end bounty — accepted-equivalent work already in flight

copperheadhq/copperhead issue #66 advertises USD 50 for an eight-stage KiCad pipeline run, fixes, deterministic coverage and a findings report. On inspection it had 105 comments and two assignees; multiple contributors had already claimed or supplied plans. The task also requires a configured KiCad/provider environment and a real full pipeline run.

Source: https://github.com/copperheadhq/copperhead/issues/66

Decision: **REJECT_FOR_CONTENTION_AND_UNBOUNDED_RUNTIME**. A speculative duplicate implementation has poor expected value and would not be a bounded public-fixture proof.

### Research leads — one unpaid, one heavily contested

aadarwal/swarmstatus-bounties issue #4 has precise primary-source acceptance criteria for an SEC county-data anomaly, but explicitly says no monetary reward is announced and already has an attempt. aLexzzz430/Cognitive-OS issue #5 advertises USD 3,000 for an accepted packet from at least eight distinct AI systems, but had 92 comments and multiple submitted PRs; compliant work requires genuine access to eight systems and acceptance remains maintainer-discretionary.

Sources:
- https://github.com/aadarwal/swarmstatus-bounties/issues/4
- https://github.com/aLexzzz430/Cognitive-OS/issues/5

Decision: **REJECT_FOR_FIRST_REVENUE**. The former cannot produce revenue; the latter combines provider-access burden, heavy competition and discretionary acceptance.

### Aggregator false positives — posted amount is not funding evidence

A recent BountyScout alert surfaced several apparently small software bounties. Direct source inspection found examples already closed as `not_planned`, including scaffold-studio-hq/scaffold-studio-mcp #3 (USD 45), Signpost-Labs/signpost-api #100 (USD 100) and Escaro-Labs/escaro #70 (USD 45). Their threads asked maintainers to confirm funding and payout, but no such confirmation was observed before closure.

Sources:
- https://github.com/2510034127qq-wq/BountyScout/issues/250
- https://github.com/scaffold-studio-hq/scaffold-studio-mcp/issues/3
- https://github.com/Signpost-Labs/signpost-api/issues/100
- https://github.com/Escaro-Labs/escaro/issues/70

Commercial learning: a title containing a dollar amount, or an aggregator's extracted reward, is not demand/WTP evidence unless the source issue is open and the maintainer or escrow mechanism actually authorizes and funds it.

## Updated admission order

For future public-bounty candidates, verify in this order before any implementation:

1. source issue is currently open and the advertised reward was authorized by the payer;
2. funding or credible payout history exists;
3. Waterfound is eligible and the payout route is lawful and available;
4. required hardware, provider access and fixtures are already available without spend or credential expansion;
5. no assignee, accepted-equivalent PR or excessive contention exists;
6. acceptance is objective enough to test privately before the public claim gate.

The recheck produced genuine negative commercial information: it eliminated the strongest recent hardware, end-to-end and research leads without implementation cost. **NO_PRODUCT_SELECTED and USD 0 remain unchanged.** Additional bounty-scanner instrumentation is SUPPORT_ONLY; source-state verification and a surviving paid job remain the commercial predicate.


## Same-day source-quality stress test

A fresh GitHub-label search surfaced two apparently open, low-cost Algora tasks. Direct issue, comment and repository inspection rejected both before implementation.

### oss-hunter-livefire #1 — public automation fixture, not a commercial opportunity

tine1117/oss-hunter-livefire issue #1 is open and labeled as a USD 50 bounty for a one-line duration-parser fix. However, the repository README explicitly describes the repository as a sandbox/test fixture for exercising an automated bounty-solving workflow and asks contributors to star the repository and follow its owner. The issue already had 66 comments, and repository search returned more than 160 near-equivalent pull requests for the same missing `"d": 86400` mapping.

Sources:
- https://github.com/tine1117/oss-hunter-livefire/issues/1
- https://github.com/tine1117/oss-hunter-livefire/blob/main/README.md
- https://github.com/tine1117/oss-hunter-livefire/pulls

Decision: **REJECT_AS_NON-COMMERCIAL_FIXTURE_AND_EXTREME_CONTENTION**. An open bounty label and objective test are insufficient when the owner discloses that the repository is a workflow fixture and the solution has already been duplicated at industrial scale. Do not star, follow, comment, patch or claim.

### pcb-viewer #163 — funded history, but already repeatedly rewarded and economically dominated

tscircuit/pcb-viewer issue #163 remains open with a USD 3 Algora bounty. The Algora bot's issue table lists many submitted solutions and reward links, while repository search shows numerous later pull requests still claiming the same small migration. The public-claim requirement also includes a UI demo video.

Sources:
- https://github.com/tscircuit/pcb-viewer/issues/163
- https://github.com/tscircuit/pcb-viewer/pulls?q=is%3Apr+163

Decision: **REJECT_AS_ALREADY-SATURATED_AND_NEGATIVE_EXPECTED_VALUE**. This does demonstrate a payer history, but it is not a live exclusive task: the same outcome has repeatedly been submitted/rewarded, the nominal reward is USD 3, and the public/demo overhead exceeds the maximum gross return even before payout friction.

### Admission rule added

Before treating an open bounty as claimable, verify not only issue state and funding but also repository purpose and reward lifecycle:

1. reject declared test fixtures, engagement farms and repositories whose primary observed purpose is exercising automated submissions;
2. count equivalent open and closed pull requests, not only issue assignees;
3. inspect bot reward history—an open issue can remain visible after equivalent solutions have already been rewarded;
4. compare the maximum gross reward with mandatory public artifacts, account/payment overhead and contention; reject when the best-case economics are already negative.

This stress test found no admissible patch candidate. It improves the claimability filter but does not alter **NO_PRODUCT_SELECTED**, customer evidence, WTP, revenue or USD 0. No external interaction or implementation was performed.


## Same-day payer-lifecycle and expiry qualification

A further read-only screen tested two stronger-looking paths: a recurring commercial payer with recently posted defects, and a higher-value deterministic-testing challenge with public payout history.

### Expensify — real recurring payer, but current jobs are already allocated

Expensify/App issues #103775 and #103774 each advertise USD 175 for current Sentry defects and expose narrow suspected causes. Both source issues also embed Upwork job IDs. Direct state inspection found #103775 already assigned to the issue reporter and a contributor, while #103774 is assigned, labeled `Reviewing`, and has an issue owner. The latter also already has an automated implementation attempt in review.

Sources:
- https://github.com/Expensify/App/issues/103775
- https://github.com/Expensify/App/issues/103774
- https://github.com/Expensify/App/pull/103793

Decision: **REJECT_CURRENT ISSUES; RETAIN PAYER AS A MARKET SIGNAL**. The defects demonstrate a recurring payer and materially affected users, but neither is an unallocated opportunity. Expensify's proposal, assignment and Upwork lifecycle is part of claimability, not administrative cleanup after coding. Do not submit a duplicate patch or public proposal without selection and the later account/authority gate.

Commercial learning: for recurring-payer repositories, screen issue ownership, proposal selection, in-house/automated competing implementations and payment-platform eligibility before estimating implementation value. A public root cause is not a claim right.

### Turso deterministic-simulation challenge — proven historical payouts, submissions closed

Algora's official Turso challenge page advertises up to USD 1,000 for data-loss or corruption bugs found by extending Turso's deterministic simulator and shows a public leaderboard with prior rewards. It also explicitly states **Challenge Completed**, **Submissions are closed**, and **All bounties have been awarded to the winners**.

Source: https://algora.io/challenges/turso

Decision: **REJECT_AS_EXPIRED**. A shallow public-source checkout was inspected only to assess feasibility; no code was changed, no simulator run was claimed, and no toolchain was installed. The historical payout record validates that the mechanism once paid for rigorous reproducible outcomes, but it is not current demand or an available revenue path.

### Ratchet result

This pass adds two hard pre-implementation checks:

1. a challenge page must state that submissions are currently open, not merely preserve historical reward copy and a leaderboard;
2. a newly posted issue must be unallocated under the payer's actual assignment/proposal process, even when the code and suspected fix are public.

No candidate survived all claimability predicates. **NO_PRODUCT_SELECTED**, demand for Waterfound, WTP for Waterfound, customer status, revenue and USD 0 remain unchanged. The next ACTIVE commercial action remains source-state screening for a newly posted, unassigned, funded, objective job; generic scanner or runtime work remains SUPPORT_ONLY.
