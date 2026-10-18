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
