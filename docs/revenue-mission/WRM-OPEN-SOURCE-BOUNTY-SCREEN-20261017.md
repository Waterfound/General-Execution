# WRM — Open-Source Bounty Channel Screen — 2026-10-17

Status: **PAID_BOUNTY_SIGNAL / CURRENT_HIGH_VALUE_TASKS_CONTESTED_OR_CLOSED / NO_BUILD / NO_PRODUCT_SELECTED**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound reach a public, technically reproducible, permissionless-to-investigate software task with an explicit reward of at least USD 500, low enough contention to justify a private proof before any public claim or submission?

## Channel evidence

Algora publicly describes a marketplace for software bounties, jobs and contracts with payment/compliance support. GitHub issue search also exposes reward-labelled tasks without requiring a new account merely to inspect scope.

Sources:

- https://github.com/algora-io/algora
- https://github.com/oll4com/spaceapp/issues/61
- https://github.com/oll4com/spaceapp/issues/63
- https://github.com/tenstorrent/tt-metal/issues/58228

This is evidence that explicit open-source engineering rewards exist. It is not evidence that Waterfound has been selected, will be paid, or can collect funds without later identity, tax or payment onboarding.

## Current high-value screen

### SpaceApp issue 61 — USD 600 OTLP trace continuity

The issue was open, unassigned and explicitly funded at USD 600. The maintainer stated that the first pull request meeting every acceptance criterion and merged wins; work is not reserved and partial diagnostics are not funded. Payment is sent within seven days after merge through PayPal, Wise or bank transfer, with method agreed after merge.

Admission nevertheless fails:

- at least seven competing pull requests were already linked from the issue discussion (#82, #98, #112, #138, #145, #147 and #151);
- additional contributors had announced attempts;
- review order follows pull-request opening order;
- the scope is broad: shared bounded exporter, three workers, workflow/activity trace structure, continuation links, replay suppression, privacy allowlisting, integration tests and documentation;
- the terms require the submitting person to personally review and test AI-assisted work.

A private implementation now would be a speculative race with low expected value, not the cheapest test of capability or demand.

### Adjacent SpaceApp bounties

The same repository exposed other USD 400–750 tasks, but each inspected issue already had multiple implementations in flight:

- #60: nine linked PR numbers found in discussion;
- #62: nine linked PR numbers;
- #63: five linked PR numbers;
- #64: seven linked PR numbers;
- #65: eleven linked PR numbers.

Sources:

- https://github.com/oll4com/spaceapp/issues/60
- https://github.com/oll4com/spaceapp/issues/62
- https://github.com/oll4com/spaceapp/issues/63
- https://github.com/oll4com/spaceapp/issues/64
- https://github.com/oll4com/spaceapp/issues/65

This is unusually strong payment and scope evidence but also unusually high winner-take-all contention.

### Tenstorrent indexed rewards

Mirrored/indexed pages surfaced rewards from USD 500 to USD 7,500. Direct inspection of the original issues showed the sampled tasks were already closed as completed and assigned, including #56290, #58227, #58228, #56277 and #56751. The index was therefore stale for admission purposes.

## Decision

Do not build against any screened bounty. Do not claim, comment, fork for submission, publish a branch, open a pull request, or begin payment onboarding.

Keep public open-source bounties as a **secondary discovery channel**, not the active wedge. Re-enter only when all are true:

1. the original maintainer issue is open and the reward is explicitly confirmed;
2. no assignee, accepted claim, earlier qualifying PR or material competing implementation exists;
3. scope and acceptance tests are complete enough to reproduce privately;
4. the repository can be built and tested without new paid infrastructure, private credentials or specialized unavailable hardware;
5. expected implementation and review cost is proportionate to the probability-adjusted reward;
6. a bounded private proof can retire a named technical risk before any public action;
7. Waterfound separately authorizes any claim, public PR/submission, contractual acceptance, payment/KYC/tax onboarding or payout details.

## Kill criteria

Reject a candidate before implementation if any one holds:

- winner-take-all race already has a substantive PR;
- reward exists only on an aggregator and cannot be confirmed at the original issue;
- issue is closed, assigned, reserved or stale;
- acceptance depends on unavailable hardware, paid services, customer credentials or production access;
- payout requires upfront money, wallet funding, undisclosed identity transfer or unverifiable terms;
- expected engineering cost exceeds the probability-adjusted reward;
- work is harmful, deceptive, license-incompatible or outside Waterfound authority.

## Evidence accounting

- Capability: not tested; admission failed before build.
- Buyer/problem: maintainers posted explicit, testable engineering needs.
- Payment signal: explicit USD 600 terms confirmed for one open issue; no Waterfound payment.
- Availability: open for SpaceApp, but heavily contested; sampled Tenstorrent tasks closed.
- Differentiation: unproven; speed alone is not a defensible advantage in an existing multi-PR race.
- Waterfound WTT/WTP/revenue: none / none / USD 0.
- Mission posture: continue commercial discovery; no current human gate and no new infrastructure.

No outreach, claim, comment, fork, public branch, pull request, publication, spend, contract, payment/KYC, private data, runtime activation or privacy-producer activation occurred.
