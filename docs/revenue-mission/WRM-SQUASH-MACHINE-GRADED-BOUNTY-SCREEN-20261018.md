# WRM Squash machine-graded micro-bounty screen — 2026-10-18

**Decision:** `REAL_MACHINE_GRADED_CHANNEL / LOCAL_ACCEPTANCE_PASS / NEW_TASKS_UNFUNDED / NO_CLAIM / NO_REVENUE`

## Commercial predicate

Can a public, machine-graded micro-bounty provide a bounded route to first Waterfound revenue with objective acceptance, before any public submission, new provider permission, or financial onboarding is requested?

## Evidence boundary

Public GitHub sources and an isolated local reproduction were used. No Squash account was connected, no GitHub permission was granted to Squash, no Stripe onboarding or KYC was started, no issue was claimed, no fork or pull request was created, and no code was published or delivered.

Primary sources inspected on 2026-10-18:

- New candidate issue: <https://github.com/DaltonTheDeveloper/cal.diy/issues/1>
- Historical live-flow issue: <https://github.com/DaltonTheDeveloper/squash-live-test/issues/2>
- Public frozen acceptance fixture: <https://github.com/DaltonTheDeveloper/cal.diy/tree/main/.squash>

## Payment-channel evidence

A historical US$5 live-flow issue shows the following public bot states:

1. a frozen acceptance test and SHA-256 were posted;
2. the base failure was verified;
3. the funder later obtained `Squash: funded`;
4. an attempted claim without payout setup was rejected;
5. after payout onboarding was described as repaired, a solver successfully obtained `Claimed`;
6. the solver submitted an exact commit with `/deliver`;
7. the bot recorded `Delivery submitted` and stated that the exact commit would be graded against the frozen test.

This is stronger than an informal maintainer promise because funding, claim ownership, exact-commit delivery and automated grading states are externally visible. It is still **not evidence of a completed payout**: the inspected thread stops at submitted delivery, and the stated payment hold and Stripe eligibility remain unresolved in the public record.

The historical issue is no longer a Waterfound opportunity because another solver already holds the claim and has delivered.

## New-task state

Four new US$5 issues were opened by the same operator on 2026-10-18 in forked public repositories:

- `DaltonTheDeveloper/documenso#1`
- `DaltonTheDeveloper/activepieces#1`
- `DaltonTheDeveloper/archestra#1`
- `DaltonTheDeveloper/cal.diy#1`

Each bot response says `Squash: funding pending` and that a verified failing base run must unlock funding. At the last reconciliation in this run, none had a later `funded` state. Therefore no advertised US$5 amount is treated as available money, escrowed consideration, WTP, or a current claimable job.

The repositories are forks and the issues mirror upstream bugs; acceptance is governed by the fork's frozen fixture, not by upstream merge. That reduces maintainer-review uncertainty but does not eliminate platform, funding, claim-race, payout, tax or account risk.

## Minimal local capability proof

The smallest new fixture, `cal.diy#1`, was reproduced without cloning the large upstream repository.

Frozen assertions:

- space-separated scopes must produce two tokens;
- comma-separated scopes must continue to work;
- a single scope must continue to work.

Observed baseline: **2/3 pass; 1/3 fail**, with the space-separated input returned as one token.

A one-line parser change from comma-only splitting to splitting on comma-or-whitespace produced **3/3 passing assertions** under Node's native test runner.

This proves only that the public acceptance fixture is technically solvable. It does not prove that a full delivered commit will be accepted, that the bounty will be funded, that Waterfound can win the race, that Stripe will onboard the relevant payee, that funds will settle, or that the expected value exceeds the operational burden.

## Value and authority accounting

Potential gross consideration per new item: **US$5**, only after a visible funded state and successful machine grading.

Unmeasured or external costs include:

- Squash GitHub authorization;
- Stripe Connected Account onboarding, identity/tax requirements and country eligibility;
- public fork/commit/delivery;
- first-payout hold, fees and settlement;
- first-come claim and delivery race;
- platform and contract review;
- possible duplication among four simultaneous candidates.

Because all current items remain funding-pending, those external actions are not yet a justified Waterfound gate. The local proof is preserved as candidate evidence only.

## Promotion criteria

Promote exactly one candidate only when all are true:

1. the primary issue shows `Squash: funded`;
2. no other solver holds the claim or has a delivered result;
3. the frozen test hash and base commit still match the inspected contract;
4. the public license permits the forked modification and delivery;
5. Waterfound's exact payee country/entity is eligible under the actual Stripe arrangement;
6. the smallest bounded human action is authorization for the required GitHub/Squash connection and Stripe onboarding;
7. after that authorization, claim and delivery can be performed without paid spend, deceptive conduct, private data reuse or unrelated repository mutation.

## Kill criteria

Close the candidate when any one holds:

- funding remains pending or is withdrawn;
- a competing solver claims or delivers first;
- completed-payout evidence cannot be reconciled before external onboarding;
- payout eligibility or terms exclude the intended Waterfound payee;
- the public fixture changes after inspection;
- expected net value becomes negative after conservative account, tax, fee and settlement costs;
- delivery requires rights, credentials, private data, or commitments outside the existing authority envelope.

## Mission posture

This is the first screened channel in the current discovery branch with objective machine acceptance and a locally passing new-task fixture. It remains **SECONDARY / CONDITION_WAIT_ON_FUNDING**, not ACTIVE and not a present human gate.

No product is selected. No customer demand for WRM-T1, operator-hours saved, ROI, sustainable price, WTP for a Waterfound product, completed payment or revenue was established. Observed Waterfound revenue remains **USD 0**.

## Operational reconciliation — 2026-10-18T19:33Z

A global GitHub issue search for the exact public state `Squash: funded` found only two relevant Squash live-test issues from this operator:

- `squash-live-test#1` never advanced beyond funding pending. The bot rejected both claim and delivery; a solver had already published a fix but could not enter grading.
- `squash-live-test#2` advanced to funded, claim and delivery-submitted. More than five hours after the recorded delivery, the issue still contained no grader verdict or payout event. The delivered commit exposed zero GitHub check runs and zero commit statuses; its combined status remained pending.

This does not prove that Squash cannot grade or pay through a separate private backend. It does prove that the available public record does not yet demonstrate the advertised end-to-end predicate: funded task → objective green verdict → payout released/settled.

Accordingly, **no external onboarding is justified yet**, even if one of the four new issues becomes funded. Before promotion, require both a current funded-and-unclaimed item and a reconciled completed grader/payout precedent, or equivalent primary platform evidence. The channel remains `CONDITION_WAIT`; no Waterfound gate is active.

## Grading and settlement reconciliation — 2026-10-18T22:25Z

The historical live-flow issue advanced after the prior reconciliation:

- the maintainer publicly stated that the frozen test passed and the delivery was accepted;
- payout did **not** settle because the solver's Japanese bank account was not supported by the platform's US-based Stripe arrangement;
- the maintainer named the United States, Canada, the United Kingdom and the European Union as supported bank locations, reopened payout setup, and offered to find another route if the solver cannot supply one.

Primary source: <https://github.com/DaltonTheDeveloper/squash-live-test/issues/2#issuecomment-6255917408>

This upgrades one predicate from unknown to observed: **exact-commit machine grading can reach accepted**. It also exposes the current commercial bottleneck: acceptance is not equivalent to payable settlement, and the available public record does not establish a supported Brazil payee route or a completed payout.

Updated channel state:

`GRADING_ACCEPTANCE_CONFIRMED / SETTLEMENT_NOT_CONFIRMED / CURRENT_ITEMS_UNFUNDED / BRAZIL_ELIGIBILITY_UNKNOWN / NO_CLAIM / NO_REVENUE`

No Waterfound human gate is active. Promotion still requires a current funded-and-unclaimed item, independently verified Brazil payee eligibility under the actual arrangement, and a settled-payout precedent or an equivalent binding primary payment term. No onboarding should begin merely to probe eligibility.

## Award-preservation and reopened-task reconciliation — 2026-10-18T23:43Z

The maintainer subsequently clarified two facts:

1. the original solver's accepted US$5 award still stands; and
2. because the configured Stripe route cannot pay the solver's Japanese bank, Squash offered direct settlement through PayPal or another Japan-compatible route after the solver emails its GitHub handle and payment coordinate.

Primary receipt: <https://github.com/DaltonTheDeveloper/squash-live-test/issues/2#issuecomment-6256634917>

No public payment receipt was observed, so the state is **promised alternative settlement**, not settled payout.

The maintainer also reopened the same issue as “$5, first come” and stated that automated grading remains the judge. The public thread does not contain a new bot funding receipt that distinguishes a second funded award from the already accepted and still-unsettled original obligation. The reopened issue therefore remains **funding ambiguous**, not a new claimable Waterfound asset.

Reopen source: <https://github.com/DaltonTheDeveloper/squash-live-test/issues/2#issuecomment-6256191178>

The four separate candidates (`cal.diy`, `documenso`, `activepieces`, `archestra`) remain `Squash: funding pending`.

Updated channel state:

`GRADING_ACCEPTED / ORIGINAL_AWARD_PRESERVED / ALTERNATIVE_SETTLEMENT_PROMISED_NOT_OBSERVED / REOPENED_REWARD_FUNDING_AMBIGUOUS / FOUR_NEW_ITEMS_UNFUNDED / BRAZIL_ROUTE_UNPROVEN / NO_CLAIM / NO_REVENUE`

There is still no present Waterfound gate. A human action becomes justified only after a distinct current bounty has a new machine-verifiable funded receipt, no competing claim, a public acceptance contract, and a payment route explicitly available to the intended Brazilian payee without misrepresenting residence or account ownership.


## Settled-payout precedent — 2026-10-19T00:09Z

After the maintainer directed the accepted solver to send a payment coordinate through the stated private channel, the solver posted **“Squash payout confirmed”** in the public issue thread.

Primary receipt: <https://github.com/DaltonTheDeveloper/squash-live-test/issues/2#issuecomment-6256873006>

This is claimant-side confirmation of payment, not a processor receipt and not proof of the exact rail, fees, timing, or tax treatment. It nevertheless closes the historical channel predicate at the level supported by public evidence: a frozen-test delivery was accepted, the original award remained payable after the configured bank route failed, and an alternative settlement was confirmed by the recipient.

The confirmation also included a personal payment coordinate in the public thread. That datum is neither reproduced nor treated as an admissible Waterfound input; no contact, reuse, or outreach is authorized.

Updated channel state:

`HISTORICAL_GRADING_ACCEPTED_AND_ALTERNATIVE_PAYOUT_CONFIRMED_BY_RECIPIENT / CURRENT_FOUR_ITEMS_UNFUNDED / REOPENED_SECOND_AWARD_FUNDING_AMBIGUOUS / BRAZIL_ROUTE_UNPROVEN / NO_CLAIM / NO_WATERFOUND_REVENUE`

Commercial consequence:

- the channel now has one public end-to-end payout precedent;
- the precedent used an exceptional manual alternative after the configured bank route failed, so it does not establish routine settlement or Brazilian payee eligibility;
- the four distinct current candidates remain `Squash: funding pending`;
- the reopened historical issue still lacks a new bot funding receipt separating a second award from the already settled first award;
- no Waterfound gate is current.

Promote a Waterfound action only when a distinct current issue is visibly funded and unclaimed, its frozen acceptance contract remains unchanged, and the issuer explicitly confirms a lawful payment route for the intended Brazilian payee without misrepresenting residence, bank ownership, or account identity. Until then, preserve the local proof and continue public-payoff discovery.

## Brazil payout-route determination — 2026-10-19

Official Stripe documentation resolves the advertised self-serve Connect route more narrowly than the earlier generic country claims:

- Stripe Connect cross-border payouts are self-serve only among platforms and connected accounts in the United States, United Kingdom, European Economic Area, Canada, and Switzerland.
- Stripe states that self-serve cross-border payouts to countries outside those regions are not supported; platforms must contact sales for alternatives or use a different product such as Global Payouts.
- Brazil is not listed in the documented legacy Express connected-account availability list used by the inspected onboarding model.

Primary sources:

- <https://docs.stripe.com/connect/cross-border-payouts>
- <https://docs.stripe.com/connect/accounts#express-accounts>

Therefore the current advertised Squash Connect/Stripe bank route is **not available to a Brazilian connected account under the public self-serve terms**. The recipient-confirmed Japanese payout demonstrates that Squash can settle an exceptional manual alternative after failure, but it does not create a standing Brazil route or a binding promise to Waterfound.

Updated decision:

`HISTORICAL_END_TO_END_PAYOUT_PRECEDENT / CURRENT_CONNECT_ROUTE_EXCLUDES_BRAZIL / MANUAL_BRAZIL_ALTERNATIVE_UNCONFIRMED / CURRENT_FOUR_ITEMS_UNFUNDED / NO_CLAIM / NO_WATERFOUND_REVENUE`

This closes eligibility research for the advertised integration and moves the channel to **PASSIVE / CONDITION_WAIT**. Do not probe onboarding. Re-enter only if a distinct task becomes funded and unclaimed **and** the issuer publicly commits to a lawful Brazil-compatible settlement route, fees, recipient requirements, and acceptance terms before any claim or implementation. Given the US$5 gross reward, reject any route whose human coordination, KYC, tax, transfer, or collection burden makes expected net value immaterial.


## Current-task funding and claim reconciliation — 2026-10-19

Two of the four distinct candidates advanced from funding pending, but neither became an admissible Waterfound opportunity:

- `DaltonTheDeveloper/activepieces#1` reached a funded state, was claimed by another solver, and received an exact-commit delivery. The public thread now shows grading delay and inconsistent later “open/first-come” messaging after that prior claim and delivery.
- `DaltonTheDeveloper/documenso#1` likewise reached funded, was claimed by the same external solver, and received an exact-commit delivery. It also has later “open/first-come” messaging despite the recorded delivery.
- `DaltonTheDeveloper/cal.diy#1` and `DaltonTheDeveloper/archestra#1` remain funding pending.

Primary sources:

- <https://github.com/DaltonTheDeveloper/activepieces/issues/1>
- <https://github.com/DaltonTheDeveloper/documenso/issues/1>
- <https://github.com/DaltonTheDeveloper/cal.diy/issues/1>
- <https://github.com/DaltonTheDeveloper/archestra/issues/1>

The first two items fail the existing promotion criterion that no other solver holds the claim or has delivered. Their later reopening language does not establish a distinct second funded award, a clean claim transfer, or an unambiguous acceptance contract. The advertised payout geography in those threads remains the United States, Canada, United Kingdom and European Union, so it does not cure the independently documented Brazil exclusion for the current Connect route.

Updated channel state:

`TWO_CURRENT_ITEMS_FUNDED_BUT_ALREADY_CLAIMED_AND_DELIVERED / GRADING_PENDING_OR_CONTRACT_AMBIGUOUS / TWO_ITEMS_UNFUNDED / CURRENT_CONNECT_ROUTE_EXCLUDES_BRAZIL / NO_WATERFOUND_CLAIM / NO_WATERFOUND_REVENUE`

Commercial consequence:

- do not race, duplicate, claim, implement, contact, onboard or publish against either delivered item;
- do not treat later “open” wording as a new award without a distinct machine-verifiable funding receipt and explicit claim reset;
- retain the channel as **PASSIVE / CONDITION_WAIT**, because no current item is both funded and unclaimed and no lawful routine Brazil settlement route is established;
- re-enter only under the already recorded conjunctive criteria: a distinct funded-and-unclaimed task, a stable frozen acceptance contract, and a public Brazil-compatible settlement commitment whose expected net value remains material after coordination, KYC, tax, transfer and collection burden.

No product demand, Waterfound WTP, payable Waterfound claim, or revenue is established. Observed Waterfound revenue remains **USD 0**.
