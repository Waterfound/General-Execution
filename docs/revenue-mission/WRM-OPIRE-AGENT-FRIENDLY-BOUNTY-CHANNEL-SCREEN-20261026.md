# WRM — Opire Agent-Friendly Bounty Channel Screen — 2026-10-26

Status: **OFFICIAL_DOLLAR_CHANNEL / AGENT_FRIENDLY_TASKS_OBSERVED / CATALOG_STATE_UNRELIABLE / CREATOR_PAYMENT_NOT_ESCROW_ASSURED / CURRENT_CANDIDATES_STALE_OR_SATURATED / NO_BUILD / WATCH_ONLY**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Does Opire currently expose one specific, funded, agent-compatible task whose GitHub issue is open, whose payable residual is unclaimed, whose acceptance criteria are objective, and whose expected value remains positive without credentials, paid APIs, misleading identity or pre-authorization publication?

Admission requires:

1. the Opire listing and canonical GitHub issue/repository state agree;
2. the reward is backed by a credible payer and collection path;
3. no equivalent implementation or saturated queue already exists;
4. the task or maintainer explicitly permits truthfully disclosed AI-agent execution;
5. a private proof can be built and tested using already-authorized free resources;
6. claiming, public PR, contract acceptance and payout onboarding remain deferred until a differentiated proof exists.

## Channel evidence

Opire is an official open-source bounty platform with public documentation, GitHub integration and dollar-denominated rewards.

Official sources:

- https://opire.dev/home
- https://docs.opire.dev/
- https://docs.opire.dev/rewards/pricing
- https://opire.dev/terms-of-service
- https://github.com/Opire

Its public workflow is issue → pull request → bounty claim → creator review → payment. The platform advertises that developers receive 100% of a bounty, with Stripe used for payment processing.

This establishes a real channel, not a token-only or anonymous reward board.

## Payout assurance is weaker than the headline

The official documentation says:

- creating or claiming a bounty does not create automatic payment;
- each bounty creator decides whether the pull request meets the issue requirements;
- the creator then arranges payment;
- payment details should be agreed before claiming;
- Opire tracks the bounty but the contractual relationship is between customer and developer;
- Opire is not responsible if the customer fails to pay.

This conflicts with some repository copy that says payment is “automatic on merge.” The platform terms and payment documentation control the conservative interpretation: **a displayed reward is a promise subject to creator acceptance and collection risk, not evidence of escrowed cash**.

Account creation requires accurate identity and agreement to Opire's terms. Stripe terms and financial data are later payout gates.

## Catalog integrity check

The public inventory cannot be trusted without independent reconciliation:

- Opire displayed a USD 100 'c1work' bounty with zero solvers, but the linked 'rodrigompy/bugb' repository is archived/read-only and GitHub issue #1 is closed;
- an indexed USD 300 TypeORM bounty linked to issue #12578, which is already closed and has multiple completed implementations;
- an indexed high-value qtop proof-of-humanity task explicitly requires a verified LinkedIn profile or comparable human traceability and already has several proofs of concept;
- the public home view exposed inconsistent aggregate counters while still rendering old reward cards;
- very large aggregate reward values can be produced by repeated or contaminated reward records and are not reliable task value.

Therefore every Opire candidate must be resolved against the GitHub issue, repository state, comments, competing pull requests and actual reward records before implementation.

## Agent-friendly candidate: Claude Builders Bounty #5

The strongest compatibility signal found was:

- [claude-builders-bounty#5 — n8n + Claude weekly dev summary](https://github.com/claude-builders-bounty/claude-builders-bounty/issues/5)
- advertised reward: **USD 200**;
- task explicitly concerns Claude Code/AI tooling;
- an autonomous agent disclosed its authorship in the issue without being rejected solely for being an agent;
- repository instructions invite builders using Claude Code and state quality is preferred over speed.

This proves that an agent-friendly bounty niche exists.

It is not a viable current task:

- the repository shows roughly 3,500 pull requests;
- the issue contains more than 1,700 additional activity items;
- numerous complete workflows and PRs already implement the same acceptance criteria;
- recent October 2026 attempts continue to duplicate the same solution;
- the task requires a successful run on a real n8n instance and screenshot;
- a faithful run requires GitHub credentials, an Anthropic API credential and a delivery destination such as Discord/Slack/email;
- no already-authorized free Claude API spend, n8n account/host or new external webhook setup is available;
- even a valid duplicate has no differentiated payable residual.

Decision: **DO NOT BUILD / DO NOT CLAIM / DO NOT PUBLISH / DO NOT CREATE CREDENTIALS**.

## Other visible candidates

- 'rencfs' Windows research, USD 42: old and underspecified; current repository history already contains Windows compatibility work and later implementation activity. Reward is too small for platform-specific Rust/FUSE validation and Windows evidence.
- UdioWrapper captcha/server-error task, USD 20: dozens of solvers/claims, stale, and coupled to reverse-engineered third-party service access and captcha automation. Morally and legally unsuitable.
- 'c1work', USD 100: repository archived and issue closed.
- qtop proof-of-humanity task: deliberately designed to exclude bots/sock puppets and requires verified human identity.
- TypeORM normalization task, indexed USD 300: issue closed with multiple solutions.

No candidate retained a specific unsolved, payable residual.

## Evidence accounting

- Credible channel: observed.
- Agent-friendly task class: observed.
- Current reliable catalog state: **not established**.
- Escrow/payment assurance: **not established; creator payment occurs after acceptance**.
- Fresh, unclaimed, positive-EV task: none found.
- Differentiated private proof: not admitted.
- External buyer demand/WTP for Waterfound: unobserved.
- Revenue: USD 0.
- Account, attempt command, claim, clone, patch, n8n instance, API key, webhook, screenshot, pull request, terms acceptance, Stripe onboarding, KYC, bank disclosure or spend: none.

## Re-entry criteria

Re-enter Opire only when all are true:

1. canonical GitHub issue and repository are open and active;
2. the reward record is current, non-duplicated and backed by a credible creator;
3. the creator confirms the remaining payable scope and truthful agent eligibility;
4. no equivalent PR or implementation already satisfies it;
5. the proof runs with public/synthetic inputs and existing free resources;
6. conservative expected value remains positive after build, validation, competition and collection risk;
7. Waterfound separately authorizes public claiming, contractual acceptance and payout onboarding.

Mission posture:

**WATCH_ONLY / CONTINUE_DISCOVERY / NO_CURRENT_HUMAN_GATE**.
