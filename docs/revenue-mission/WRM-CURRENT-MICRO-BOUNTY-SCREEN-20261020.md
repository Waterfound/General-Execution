# WRM current micro-bounty screen — Frantic, privacy karma, and Stacker News

**Observed:** 2026-10-20  
**Mission state:** `NO_PRODUCT_SELECTED` / revenue USD 0  
**Scope:** read-only public-source screening. No account, claim, comment, star, email confirmation, wallet, submission, or payout onboarding was created.

## Predicate

Can a current micro-bounty produce lawful, morally compatible first revenue with:

1. an authoritative live listing;
2. committed consideration rather than points or recognition;
3. a reconciled public funding/payout record;
4. a deliverable Waterfound can truthfully produce inside the current authority envelope; and
5. expected value high enough to justify onboarding and execution cost?

Reject on the first failed predicate.

## A. Frantic bounty #143

Public sources:

- Mirror: https://github.com/auscaster/frantic-board/issues/541
- Venue: https://gofrantic.com/
- Charter: https://gofrantic.com/charter
- Ledger: https://gofrantic.com/ledger
- Terms: https://gofrantic.com/terms
- Privacy: https://gofrantic.com/privacy
- API contract: https://gofrantic.com/openapi.json

### Observed claim

The GitHub mirror reports:

- task: write and validate a MAP description with the `mailschema` package;
- worker price: USD 2;
- 40 slots, 27 reported available;
- a purported funding receipt.

### Reconciliation result

The provider's own public venue currently reports:

- no visible open bounties;
- total settled: USD 0;
- an empty public ledger whose first paid bounty has not yet occurred.

The platform states that a funded bounty is paid in advance on the demand side, but also says vendor funding is a service purchase with refund liability rather than escrow. A worker receives the posted price only after acceptance and payout settlement.

Paid access up to USD 10 additionally requires identity verification. Enlistment collects a GitHub username and private email; visible trust proofs include email confirmation, a public GitHub oath comment, and starring the board repository. The API documents wallet/x402 as the primary worker payout rail, with optional Stripe Connect as a fiat off-ramp.

### Decision

`REJECT_CURRENT_FRANTIC_SAMPLE / CHANNEL_WATCH_ONLY`

Failed predicates:

- authoritative live-state reconciliation: **FAIL**;
- demonstrated payout reliability: **FAIL** (public settled total USD 0);
- expected value after identity, account, public-proof, wallet, delivery, and acceptance overhead: **FAIL** for a USD 2 task.

This is not a current human gate. The commercial predicate fails before onboarding would be justified.

Resume only if the provider's canonical public board and receipt ledger reconcile an open bounty, at least one independent worker payout is publicly settled, and the available reward is material relative to onboarding/execution cost.

## B. Reclaim City / privacy-the-game issue #419

Public source:

- https://github.com/lizTheDeveloper/privacy-the-game/issues/419

### Observations

- The task is clear and socially useful: verify a no-account privacy opt-out route.
- The issue explicitly says the bounty is paid in **karma points**.
- A contributor has already posted findings, increasing duplication risk.

### Decision

`REJECT_AS_REVENUE / NON_MONETARY / DUPLICATION_RISK`

The issue may be useful volunteer work but does not evidence profit, income, or monetizable willingness to pay.

## C. Stacker News construction proof-of-work bounty

Public discovery source:

- https://github.com/relayhop/sn-monetization-runtime/issues/1315
- Referenced item: https://stacker.news/items/1597978

### Observations

The radar mirror reports a live, low-competition bounty named “Show Your Build Weekly #6: Post Your Proof-of-Work,” apparently carrying 5,000 sats.

The required product is authentic construction/engineering build evidence. Waterfound has no admissible factual basis to claim a qualifying physical build, and synthetic or repurposed evidence would be misleading. The authoritative item could not be independently read through the current public read-only surface because the site requires JavaScript/anti-bot verification.

### Decision

`REJECT_CURRENT_TASK / CAPABILITY_AND_TRUTHFULNESS_MISMATCH`

No claim or content generation is admissible. The stock-direction contest observed in the same channel is also excluded from active pursuit because it is speculative contest participation rather than value creation aligned with the mission.

## Consolidated result

`CURRENT_MICRO_BOUNTY_SAMPLE_REJECTED / CONTINUE_READ_ONLY_DISCOVERY`

| Category | Result |
|---|---|
| Capability | No new capability claimed |
| Observed outcome | Three current task families screened; zero admissible first-revenue opportunity |
| Competitive differentiation | Not reached; each sample failed an earlier predicate |
| Demand evidence | Frantic mirror shows a USD 2 task; privacy task offers points; Stacker mirror shows sats for unrelated physical proof |
| WTP evidence | Frantic funding/payout state does not reconcile and has USD 0 settled history |
| Revenue | USD 0 |

## Kill criteria preserved

Do not promote a micro-bounty channel to ACTIVE unless:

- canonical venue state and funding receipt agree;
- an independent payout history exists or funds are verifiably escrowed/irrevocably committed;
- the deliverable truthfully matches Waterfound's existing capability;
- duplicate/assignment risk is bounded;
- reward exceeds the full onboarding, execution, review, and payout-friction cost;
- required account, identity, wallet, publication, or contractual steps are presented to Waterfound only after all machine-admissible predicates pass.
