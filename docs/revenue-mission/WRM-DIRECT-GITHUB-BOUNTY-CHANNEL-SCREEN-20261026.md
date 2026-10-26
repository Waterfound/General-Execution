# WRM Direct GitHub Issue Bounty Channel Screen — 2026-10-26

## Decision

`REAL_PAID_TASKS_CONFIRMED / CURRENT_ITEMS_ASSIGNED_AND_CONTESTED / UPWORK_AND_SLACK_DEPENDENCY / GENERIC_SEARCH_LOW_TRUST / NO_BUILD / WATCH_ONLY`

Do not treat global GitHub issue search as an ACTIVE first-revenue channel. Keep only a source-pinned watchlist of established maintainers whose payout authority, claim procedure, task state, and AI policy can be verified.

## Commercial question

Can Waterfound obtain first revenue by finding an open, explicitly funded GitHub issue, preparing the fix autonomously, and stopping only at the final public claim or submission gate?

## Evidence

### Real buyer spend exists

Expensify publishes current issue titles with explicit USD amounts and links them to external contributor work. Two current examples inspected:

- Expensify/App #104307 — USD 175; opened 2026-10-18.
- Expensify/App #104050 — USD 175; opened 2026-10-14.

This establishes a real payer and a concrete paid engineering job. It is stronger demand evidence than speculative product-market discussion.

### The current tasks are not unclaimed

At inspection:

- #104307 had an assignee and 30 comments. Multiple contributors and Expensify's own MelvinBot had already posted root-cause analyses, proposals, reproduction evidence, and fix demonstrations.
- #104050 had an assignee and 22 comments.

An open issue is not equivalent to available work. Preparing another implementation would create duplicate work with no reasonable payment assurance.

### The route depends on the blocked human channel

Both issue bodies:

- direct contributors to a Slack onboarding form;
- contain an Upwork job URL and job identifier;
- require an Expensify account/workspace to reproduce the bug;
- rely on proposal selection and an assigned issue owner.

Waterfound's prior Upwork attempt reached human verification and profile/account friction. Re-entering the same route would violate the One Machine constraint rather than solve it.

### Generic discovery is low-trust

Global GitHub searches for “bounty”, “USD”, and “USDC” were dominated by:

- self-authored opportunity-router repositories;
- unsolicited token integration offers posted into unrelated projects;
- already-claimed micro-bounties;
- security programs requiring separate private submission and eligibility;
- historical, closed, or stale payout notices.

Search presence, an amount-like string, or a “VERIFIED” label asserted by a third-party bot is not evidence of funded authority.

### Established alternatives checked

- Tuist has a documented historical bounty mechanism via Open Collective/GitHub Sponsors, but no open issue carrying the repository's bounty label was returned.
- Fastify documents an Open Collective expense route, but no open issue carrying the bounty label was returned.
- Mautic documents bounties, but no current open issue carrying the bounty label was returned.
- Cal.com has historical Algora bounties, but the surfaced examples were historical and/or already attempted.

## Capability versus outcome

### Capability

- Machine-side discovery can find real paid issues.
- Repository state, assignees, comments, claim competition, and payout instructions can be verified without contacting anyone.
- A source-pinned watchlist can exclude much of the generic-search noise.

### Observed outcomes

- Two live Expensify examples were already assigned and heavily contested.
- No unassigned, independently claimable, source-authoritative task with verified payout and an admissible payment path was found.
- No proposal, fix, account action, fork, comment, assignment, or PR was created.
- Revenue remains USD 0.

## Kill criteria applied

Do not build when any of the following holds:

1. the issue is assigned, claimed, or has an accepted/in-progress proposal;
2. payment depends on a blocked account, KYC, Upwork, Slack onboarding, or unverified third party;
3. the reward originates from the issue author rather than a repository maintainer or escrowed platform;
4. AI-assisted work is prohibited or unclear;
5. reproduction requires unavailable private/staging access;
6. multiple complete proposals or fix demonstrations already exist.

The inspected current candidates triggered criteria 1, 2, 5, and 6.

## Reactivation criteria

Reactivate only for a task that simultaneously has:

- explicit amount and currency;
- repository-maintainer or escrow authority;
- open and unassigned status confirmed from the source;
- objective acceptance criteria;
- no private customer data;
- AI assistance allowed or not restricted;
- a claim path that does not require new routine human setup;
- payment receivable through an already-authorized path, or a single bounded final payout gate after the fix is independently verified;
- no active competing implementation.

## Governance

This was read-only discovery. No outreach, comment, reaction, assignment, fork, patch, public PR, Slack form, Upwork action, account, credential, payment, KYC, contract, spend, security probing, or Privacy P0 activation occurred. Further generic bounty scanning is SUPPORT_ONLY.

## Sources observed 2026-10-26

- Expensify/App #104307: https://github.com/Expensify/App/issues/104307
- Expensify/App #104050: https://github.com/Expensify/App/issues/104050
- Tuist bounty policy: https://tuist.dev/blog/2023/01/18/issue-bounties
- Fastify expense policy: https://github.com/fastify/fastify/blob/main/EXPENSE_POLICY.md
- Mautic issue tracker: https://github.com/mautic/mautic/issues
- Cal.com issue tracker: https://github.com/calcom/cal.com/issues
