# WRM Gitpay funded-issue channel screen — 2026-10-26

## Decision

**LEGITIMATE PAYMENT CHANNEL / ZERO OPEN FUNDED ISSUES / NO BUILD / WATCH_ONLY**

Gitpay documents a current payment flow for accepted Git contributions and displays historical platform activity. However, its public catalog contained no open bounty-bearing issue when screened on 2026-10-26. There is therefore no machine-admissible task to claim, prototype, or implement now.

This is a reversible availability screen, not a claim that Gitpay is inactive or unable to pay.

## Commercial predicate tested

Does Gitpay currently expose at least one task that is:

1. publicly visible and open upstream;
2. attached to a non-zero bounty;
3. claimable before work begins;
4. sufficiently scoped to estimate and test;
5. unsaturated and technically unresolved; and
6. valuable enough to justify a narrow implementation before account, payout, KYC, or public-submission gates?

**Result: no.**

## Current public evidence

### Platform and settlement capability

- Gitpay's current homepage describes funded issues, merged-PR rewards, and direct payment requests: <https://gitpay.me/>
- On 2026-10-26 the homepage displayed aggregate historical activity of **US$175,531 paid**, **6,230 bounties and payment requests**, **5,972 users**, and **217 countries**.
- Current documentation says contributors should apply, obtain assignment, deliver a linked pull request, receive maintainer acceptance, and then receive a released transfer: <https://docs.gitpay.me/docs/en/contributor/>
- Current payment documentation explicitly warns that a merged pull request alone does not guarantee release; payment, transfer credit, and payout are separate stages: <https://docs.gitpay.me/docs/en/payments/>
- Payouts currently flow through Whop and remain subject to country support plus identity and account verification: <https://docs.gitpay.me/docs/en/payouts/>

These observations establish a real historical payment channel and a documented current workflow. They do not establish that a task is available now.

### Catalog reconciliation

The public Explore interface was inspected without login at:

<https://gitpay.me/#/explore/issues>

Observed on 2026-10-26:

1. "All public issues available" displayed **446** issue records.
2. Selecting "Issues with bounties" displayed **187** records.
3. The newest visible bounty records were already **Closed**, including:
   - wine-mono/mono issue 12 — **US$25**;
   - RetroShare issues — **US$20–US$30**;
   - Apache Superset issues — **US$100–US$500**.
4. Combining "Issues with bounties" with status "Open" returned the authoritative empty state: **“No records for this table yet.”**

Therefore:

- open public issues exist;
- historical bounty records exist;
- **open public bounty records do not exist in the current catalog**.

No candidate survived to repository-level technical preflight.

## AI and autonomy compatibility

No current Gitpay policy explicitly authorizing autonomous or agent-authored submissions was established in this screen. That unknown does not need resolution while the catalog has zero open funded work.

Even if a future task is compatible, the documented workflow still requires:

- task application and maintainer assignment;
- public pull-request delivery and review;
- maintainer acceptance and payment release;
- Gitpay/Whop account setup;
- payout eligibility and identity/account verification.

Those are bounded future gates, not reasons to stop current machine-admissible research. None was triggered here because no task exists to pursue.

## Demand, value, and revenue

- Historical platform payment volume: observed.
- Historical task-level willingness to pay: observed from closed records.
- Current open-task willingness to pay: **not observed**.
- Current customer demand for a Waterfound deliverable: **not established**.
- Revenue realized by Waterfound: **US$0**.
- ROI, operator-hour savings, approval reduction, and monetary-risk reduction: **not claimed**.

## Kill criteria applied

Stop without build when any of the following holds:

1. zero open funded tasks;
2. no claim/assignment reservation before implementation;
3. no explicit reward amount;
4. upstream issue is closed, solved, archived, or already occupied;
5. AI-assisted contribution policy is incompatible or unverifiable at the point of commitment; or
6. payout friction overwhelms conservative expected value.

Criterion 1 is decisive in this screen.

## Re-entry conditions

Reopen Gitpay only when the public catalog exposes a newly open, non-zero bounty. Before implementation, verify all of:

1. upstream issue remains open and reproducible;
2. reward amount and funding state are explicit;
3. maintainer is active and assignment is available;
4. AI-assisted contribution is permitted;
5. acceptance criteria are objective;
6. no competing solution has already satisfied the task; and
7. conservative expected value remains positive after platform fees, payout friction, review risk, and required human gates.

Any signup, assignment request, public pull request, Whop onboarding, KYC, payout configuration, contract acceptance, or financial action remains a separate Waterfound gate.

## Mission-state effect

- Gitpay becomes **PASSIVE / WATCH_ONLY**.
- No code, clone, claim, account, outreach, or payout setup is admitted.
- The absence of open bounties is a channel-availability result, not a product-thesis result.
- Active work continues toward buyer/problem evidence, differentiated narrow products, and credibly funded tasks on channels with live inventory.
- The privacy P0 producer candidate remains inactive and untouched.
