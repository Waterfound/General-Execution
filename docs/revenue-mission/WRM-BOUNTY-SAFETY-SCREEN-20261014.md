# WRM — Public bounty safety and admissibility screen (2026-10-14)

Status: `REJECT_PRIVACY_PAYMENT_CONTENTION_UNVERIFIED / NO_ATTEMPT / NO_PRODUCT_SELECTED`  
Observed Waterfound revenue: **USD 0**

## Candidate

Source: https://github.com/ClankerNation/OpenAgents/issues/79

The open, unassigned issue advertises a USD 3,300 bounty for a Solidity fix to `MultiTokenStaking`: reject duplicate pools and zero addresses, avoid reward overflow, and support pool-weight updates. This is advertised reward evidence only; it is not verified escrow, payment history, an award, or Waterfound revenue.

## Disqualifying facts

### 1. Required disclosure conflicts with privacy and security

The issue requires the contributor to place a metadata block in a modified source file containing:

- agent identity;
- the full platform initialization text preceding the user request;
- OS, architecture, working directory and shell details.

Those data are neither necessary to validate the Solidity fix nor safe to publish. The repository's public `CONTRIBUTORS.json` already contains captured platform instructions and runtime metadata from contributors:

https://github.com/ClankerNation/OpenAgents/blob/main/CONTRIBUTORS.json

This is direct evidence of an operating disclosure pattern, not a hypothetical concern. Waterfound must not copy private system/developer instructions, credentials, environment details, private paths, or session context into a public repository.

### 2. Claim flow requires public identity/payment disclosure and external action

The bounty-bot comment instructs candidates to post an `/attempt` comment with plan, ETA and wallet address or PayPal email, then open a public PR with `/claim` and the payment details. It asserts payment 2–5 days after merge and asks candidates to review competing PRs.

This would require public outreach/publication, an external claim, payment onboarding or wallet/account choice, and potentially financial/crypto handling. Those are genuine Waterfound gates and are not authorized for this run.

### 3. Funding and payout are not independently verified

The repository README describes a decentralized agent protocol and payment bridge, but does not identify escrow for this bounty, a funded transaction, a binding payer, payout terms beyond the bot comment, or auditable prior payment receipts:

https://github.com/ClankerNation/OpenAgents/blob/main/README.md

The issue label and `/bounty $3300` text are not proof that USD 3,300 is reserved or collectible.

### 4. Contention and allocation risk are high

The bot states that multiple agents compete and only the first accepted PR wins. At least two matching implementations were submitted and later closed without merge:

- https://github.com/ClankerNation/OpenAgents/pull/1980
- https://github.com/ClankerNation/OpenAgents/pull/6021

PR #1980 explicitly refused to publish private runtime/session initialization text. The issue nevertheless remains open. This is not a low-contention, safely claimable opportunity.

### 5. Scope is outside the current commercial proof frontier

The work is a crypto-eligible Solidity contest, not evidence for WRM-T1's surviving same-input diagnostic hypothesis. Even a correct patch would test speculative contest execution, not buyer demand, willingness to try, repeatable value, or a defensible Waterfound product.

## Decision

`PERMANENT_REJECT` for this issue under the present terms.

Do not:

- comment, claim, fork, open a PR or review competitors;
- disclose platform initialization text or runtime/session metadata;
- publish payment identifiers;
- perform wallet/KYC/payment onboarding;
- treat the advertised bounty as funded revenue;
- use the apparent lack of assignee as evidence of low contention.

No human decision is needed because the candidate fails existing privacy, publication, financial and commercial-selection constraints. Continue searching for machine-admissible buyer/problem evidence.

## Reusable bounty admission filter

A future public bounty may enter technical feasibility screening only if all are true:

1. no request for system/developer prompts, session context, hidden instructions, credentials, private paths, or unnecessary environment metadata;
2. funding or credible payout history is independently verifiable;
3. exact claim/assignment status and competing work are checked;
4. no public comment, PR, account installation, wallet/payment disclosure or contractual acceptance is required before a bounded private proof;
5. the task is legally and ethically compatible and does not require handling funds or deploying to production;
6. expected value after contention, review probability and payment risk exceeds the opportunity cost;
7. the work advances a repeatable commercial predicate rather than merely chasing a one-off prize.

## Evidence classification

- Buyer/problem evidence: **none** for a repeatable Waterfound product.
- Advertised reward: **present, unverified**.
- Funding/payment proof: **absent**.
- Technical scope: **defined but not attempted**.
- Privacy/safety compatibility: **failed**.
- Availability: issue open/unassigned, but prior competing PRs existed and were closed unmerged.
- Demand, WTP for Waterfound, ROI, price and revenue: **unverified / USD 0**.

No outreach, public publication, fork, claim, code change to the candidate repository, payment setup, credential use, spend, runtime activation or merge was performed.
