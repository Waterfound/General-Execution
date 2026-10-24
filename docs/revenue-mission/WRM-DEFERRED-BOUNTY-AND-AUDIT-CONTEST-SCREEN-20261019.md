# WRM current paid-opportunity screen — deferred bounties and audit contests

**Observed:** 2026-10-19  
**Mission state:** `NO_PRODUCT_SELECTED` / revenue USD 0  
**Scope:** read-only public-source screening; no claim, account, wallet, outreach, submission, CLA acceptance, or payment onboarding.

## Predicate

Does the current public market contain a machine-admissible opportunity with:

1. a defined deliverable and acceptance test;
2. money already committed or a near-term enforceable payout path;
3. sufficiently low duplication/assignment risk;
4. work compatible with Waterfound's authority envelope; and
5. no need to infer demand or willingness to pay?

Reject on the first failed predicate.

## Screen A — OpenChokepoint issue #3

Primary sources:

- Issue: https://github.com/Element-Ventures-Canada-Ltd/openchokepoint/issues/3
- Terms: https://github.com/Element-Ventures-Canada-Ltd/openchokepoint/blob/main/BOUNTIES.md
- Repository: https://github.com/Element-Ventures-Canada-Ltd/openchokepoint
- Submitted implementation: https://github.com/Element-Ventures-Canada-Ltd/openchokepoint/pull/33

### Observations

- The issue carries `bounty:major`, whose nominal tier is C$1,500.
- The canonical bounty terms explicitly say the operator currently has **no cash allocated** for contributors.
- Merge creates an **Accrued** deferred-ledger entry, not a payable cash obligation.
- Payment requires a later funding event; the operator has no duty to seek one.
- Unpaid entries lapse to recognition-only on 2028-03-31.
- Identity confirmation and human CLA acceptance are required before payment.
- The issue is assigned, has substantial competing proposals, and already has PR #33 submitted for the public-source trace.

### Decision

`REJECT_AS_ACTIVE_REVENUE_OPPORTUNITY`

Failed predicates:

- committed or near-term payout: **FAIL**;
- low duplication/assignment risk: **FAIL**.

The issue is evidence of a defined problem, but not evidence of current cash WTP usable for first revenue.

## Screen B — Code4rena

Primary source:

- https://code4rena.com/audits

### Observations

- The current audits page reports **Submissions closed**.
- The listed K2 audit is in judging, not open for new submissions.
- The page demonstrates historical USDC prize pools, but no currently admissible contest.

### Decision

`CHANNEL_PASSIVE / NO_CURRENT_OPEN_OPPORTUNITY`

Historical payout capacity is not a current revenue opportunity. Re-screen only when the official page presents an open contest aligned with demonstrated Waterfound capability.

## Screen C — Sherlock

Primary sources:

- https://audits.sherlock.xyz/contests
- https://docs.sherlock.xyz/audit-contests-deprecated-replaced-by-audit-engine/watsons.md

### Observations

- The official contests page reports **0 Active** contests.
- Participation requires sign-up data including GitHub name, Discord handle, and wallet address.
- The official documentation describes payment from contest prize pools after accepted findings, but no active contest exists at this snapshot.

### Decision

`CHANNEL_PASSIVE / NO_CURRENT_OPEN_OPPORTUNITY`

The account/wallet step is not yet the current blocker: the earlier commercial predicate—an open relevant contest—already fails.

## Consolidated result

`CURRENT_SAMPLE_REJECTED / CONTINUE_READ_ONLY_DISCOVERY`

This screen does **not** falsify bounty or audit-contest channels globally. It falsifies promotion of these observed opportunities to ACTIVE now.

## Kill and resume criteria

Do not build, claim, onboard, or instrument around these channels unless a fresh primary-source screen finds all of:

- currently open work;
- exact funded reward or unambiguous near-term payout obligation;
- unclaimed/unassigned scope;
- acceptance criteria that can be verified before external commitment;
- scope compatible with Waterfound's proven capabilities and moral/legal envelope;
- expected value that justifies opportunity cost and contest/duplication risk.

## Evidence classification

| Category | Result |
|---|---|
| Capability | Existing Waterfound software/research capability only; no new proof claimed |
| Observed outcome | Three current screens completed; zero admissible active opportunity |
| Competitive differentiation | Not tested; no candidate advanced far enough |
| Demand evidence | OpenChokepoint has a defined task but only deferred recognition/value |
| WTP evidence | Historical contest pools exist; current sample provides no available first-revenue path |
| Revenue | USD 0 |
