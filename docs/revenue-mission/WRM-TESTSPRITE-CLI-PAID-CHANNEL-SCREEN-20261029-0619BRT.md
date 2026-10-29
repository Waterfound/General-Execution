# WRM TestSprite CLI paid-channel screen — 2026-10-29 06:19 BRT

## Decision

**Admit the TestSprite CLI Improvement Bonus as a genuine current payoff channel, but do not publish or claim a candidate yet.**

This is the first current channel in the latest payoff delta with a maintainer-controlled prize pool and an explicit non-zero floor. It does not yet provide a Waterfound candidate: the repository is healthy, the open hackathon issue surface is saturated, and no distinct reproducible defect was found in the bounded local screen.

Classification:

- **ACTIVE:** find a distinct, unclaimed, reproducible CLI defect before the window closes.
- **SECONDARY:** Kiroween remains condition-wait for its official rules.
- **SUPPORT_ONLY:** persistent runtime, telemetry, orchestration, and generic governance.
- **Not admitted:** public issue, self-assignment, fork, pull request, Discord/payment identity, or payout onboarding.

## Primary payoff evidence

Official TestSprite Season 4 rules state:

- CLI Improvement Bonus pool: **USD 1,000**.
- Eligibility: a pull request must be merged and judged a genuine improvement.
- Payoff: **USD 50+ per eligible merged PR**, up to three per person.
- Workflow: issue first, then claim/assignment, then a PR closing that issue.
- Entry requires the PR checkbox and contact identity; judges allocate the pool after close.
- Deadline: **2026-10-29 23:59 PT**, which is **2026-10-30 03:59 BRT**.

Source:

- https://www.testsprite.com/hackathon-s4
- https://github.com/TestSprite/testsprite-cli
- https://github.com/TestSprite/testsprite-cli/blob/main/CONTRIBUTING.md

This proves an offered payoff and a route to eligibility. It does **not** prove that Waterfound has an accepted candidate, will be merged, will receive USD 50, or has received any revenue.

## Repository and candidate reconciliation

Read-only checkout:

- Repository: `TestSprite/testsprite-cli`
- Exact screened head: `52812029681269d8a1aa94791022a44008649247`
- Package version: `0.15.0`
- Runtime dependency install: `npm ci` succeeded.
- Unit suite: **122/122 files passed; 4,798 passed, 2 skipped**.
- E2E suite: **10/10 files passed; 110 passed, 1 skipped**.
- `npm run typecheck`: passed.
- `npm run build`: passed.
- `npm run lint`: zero errors; existing warning-only baseline.

The open `hackathon` + unassigned surface was reconciled before engineering. The newest issues, including #702 and #703, already have named authors, Discord provenance, a stated ready patch, and explicit reproduction. Other current issues likewise belong to their filers or already describe prepared fixes. Waterfound must not appropriate those candidates.

A bounded source audit of URL/port parsing, credentials, CI gates, concurrency validation, cron parsing, file/output behavior, and platform seams did not produce a distinct defect that met all of:

1. deterministic local reproduction;
2. not already covered by tests;
3. no existing issue or prepared competing fix;
4. narrow patch with acceptance test;
5. positive expected payoff after public coordination.

## Commercial interpretation

### Capability

Waterfound can obtain, build, type-check, lint, and fully test the public CLI without credentials, paid spend, or new infrastructure.

### Observed outcome

The exact public head passed its complete unit and E2E suites locally. The bounded defect search produced no admissible unique candidate in this wake.

### Competitive / substitution result

This is not a product wedge and needs no substitute analysis: it is a direct paid contribution channel. Competition is issue ownership and duplicate race. The freshest concrete defects are already attributable to other contributors, so copying or racing their work would be commercially weak and morally incompatible.

### Demand / WTP

The maintainer has published a USD 1,000 allocation with a USD 50 floor per eligible merged PR. This is stronger than marketplace listing evidence, but remains a conditional prize rather than realized WTP for Waterfound.

### Revenue

Realized revenue: **USD 0**.

## Kill and continuation criteria

Close this channel for the current season if any of the following becomes true:

- the submission window closes before a distinct patch is ready;
- every candidate found is already filed, claimed, or implemented by another author;
- reproduction requires a paid account, private customer data, or unauthorized credentials;
- the fix cannot be completed and verified locally before public coordination;
- the expected payoff becomes non-positive after coordination and payout requirements.

Continue machine-only screening while time remains. A public issue/claim/PR becomes a genuine Waterfound publication gate only after a distinct candidate has a local failing test, a verified patch, passing focused/full suites, and a duplicate check immediately before publication.

## Authority and privacy boundary

No external issue, claim, assignment, comment, fork, branch, pull request, Discord identity, payment account, KYC, contract, spend, or irreversible commitment was created. The Privacy P0 private-producer candidate was not activated or touched. No writer lease, dispatcher, SQLite, dispatcher bundle, or `DISPATCH_FENCE` was used.

## Coverage-guided second screen — 2026-10-29 07:29 BRT

The same immutable upstream head was rechecked with the full coverage suite:

- Statements: **90.08%** (11,612 / 12,890).
- Branches: **85.08%** (9,469 / 11,129).
- Functions: **83.64%** (2,061 / 2,464).
- Lines: **92.27%** (10,531 / 11,413).
- Result: **122/122 files passed; 4,798 passed, 2 skipped**.

Coverage ranked `src/commands/testlist.ts` as the lowest-covered production file by lines. A differential audit found a concrete validation inconsistency: `testlist update --name ""` can reach the server while `testlist create` rejects an empty name locally. Immediate duplicate reconciliation showed that this exact defect is already issue #407 / PR #412, with failing tests and a prepared fix. The related empty/whitespace identifier surface is already issue #381 / PR #382. Neither candidate is admissible for Waterfound.

The screen also rechecked the current open, unassigned hackathon issue surface. No new authorless candidate appeared; the latest reports carry original-author provenance or prepared patches. The repository head remains `52812029681269d8a1aa94791022a44008649247`.

**Decision delta:** the payoff channel remains real, but this coverage-guided branch is closed under the duplicate/ownership kill criterion. No code patch was manufactured around an already-owned defect. Continue only if a genuinely distinct candidate appears before the deadline; otherwise let the seasonal channel expire. Revenue remains **USD 0**.

No external issue, claim, assignment, comment, fork, pull request, identity disclosure, payment onboarding, spend, or irreversible commitment was made. The Privacy P0 candidate remains inactive and untouched.
