# WRM — Public Bounty Board Claimability Screen — 2026-10-18

## Decision

`PAID_CHANNEL_CONFIRMED / HIGH_VALUE_PUBLIC_MATCHES_CONTESTED / NO_PRIVATE_PROOF_ADMITTED / NO_PRODUCT_SELECTED`

Observed Waterfound revenue: **USD 0**.

This screen tests whether the public software-bounty channel currently contains a funded, unassigned, low-contention task that Waterfound can reproduce and solve privately before any claim, publication, payment onboarding, or external commitment.

## Live channel evidence

At 2026-10-18 13:34 UTC, BountyOS reported:

- 75 verified open bounties;
- US$11,017 combined advertised value;
- 20 posted within the preceding 48 hours;
- 5 at US$500 or more;
- 71 carried through Algora and 4 through BountyHub.

The board says it rechecks issue openness, assignment, repository activity, payout confirmation, merged solutions, competing pull requests, and obvious farm/honeypot patterns. Exact issue identities are withheld behind a paid plan, so these aggregate statements establish channel supply but do not identify an admissible target.

Source: https://bountyos.rovidev.com/en/github-bounty-board/

Algora's public bot instructions state that an accepted contributor receives 100% of a bounty 2–5 days after reward, subject to payout eligibility. This supports a real payment rail. It does not prove that a particular stale GitHub issue remains funded or that a new duplicate implementation will be accepted.

## Public-source reverse screen

A no-spend GitHub search for open issues commented on by the Algora bot found plausible higher-value matches. Their live issue and pull-request state falsified claimability:

| Candidate | Advertised amount | Public state on 2026-10-18 | Decision |
|---|---:|---|---|
| CapSoftware/Cap #73 — upload speed test and health check | US$500 | Multiple issue-specific implementations remain open, including #1659, #1827, #1917, #2238 and #2425; the issue thread asks maintainers to clarify what, if anything, remains independently payable | Reject: duplicated and scope unconfirmed |
| zio/zio #9211 — timeoutTo performance | US$300 aggregate (two US$150 funds) | At least three open implementations (#11060, #11246, #11285) plus many closed attempts; the thread reports that Algora lists zero open ZIO bounties | Reject: contested and funding availability contradicted |
| getdozer/dozer #1653 — WASM UDF | US$600 | Four solution links and multiple active attempts; several contributors are already asking which residual requirement remains payable | Reject: contested and residual unconfirmed |
| getdozer/dozer #1659 — streaming SQL IN | US$600 | Eight linked solutions and multiple active attempts; current discussion asks whether any remaining scope is separately payable | Reject: contested |
| gyroflow/gyroflow #45 and #742 | US$500 each | Public Algora state exposes multiple solution/attempt records for both | Reject: contested |
| zio/zio-schema #511 — typed value reconstruction | US$200 | Three open issue-specific PRs (#1137, #1212, #1213) plus earlier closed attempts | Reject: duplicated |
| javelin-anticheat/py-workedtask #4 | US$100 | Dozens of issue-specific PRs, a one-star repository, stale source activity, and unresolved acceptance ambiguity | Reject: low trust, heavily duplicated, low value |

Primary issue sources:

- https://github.com/CapSoftware/Cap/issues/73
- https://github.com/zio/zio/issues/9211
- https://github.com/getdozer/dozer/issues/1653
- https://github.com/getdozer/dozer/issues/1659
- https://github.com/gyroflow/gyroflow/issues/45
- https://github.com/gyroflow/gyroflow/issues/742
- https://github.com/zio/zio-schema/issues/511
- https://github.com/javelin-anticheat/py-workedtask/issues/4

## Fresh GitHub delta

A separate search of issues created after 2026-10-18 13:00 UTC produced new bounty-like records, but the representative entries were not unclaimed paid work:

- BasedHardware/omi proposals already contain proposed implementations and claimant payment details; the US$50 amount is proposed, not an issuer-funded open task.
- Pollinations POLLEN-QUEST issues already point to completed linked implementations and offer 3 Pollen after merge.
- BountyScout's new alert aggregates issue text containing bounty terms, including reports, proposals, zero-dollar work and unrelated bounty-system code; it is not an issuer-verified opportunity list.

No private implementation was admitted from this delta.

## Why paid board access is not the present gate

Paying to reveal exact BountyOS targets would be new spend and is not authorized. More importantly, the public reverse screen shows that an “open” bounty can still have competing PRs, already-rewarded work, stale funding, or unclear residual acceptance. A subscription would reveal candidates, not establish that any one passes the mission's claimability predicate.

Therefore paid access is neither necessary nor proportionate at this stage, and its absence is not a human gate. Continue public-source discovery.

## Admission rule

A bounty may enter private proof only if all are independently verified immediately before work:

1. exact monetary reward and supported payout route;
2. credible active repository and issuer;
3. issue open and unassigned;
4. zero active issue-specific solution PRs, or an issuer-defined residual that is separately payable;
5. objective acceptance test reproducible locally;
6. required toolchain available without paid services, private credentials, restricted hardware, or prohibited access;
7. expected reward materially exceeds implementation, review, contention and collection risk;
8. public claim, PR, account action, contract and payment onboarding remain deferred until separately authorized.

## Outcome

- Capability build: **not admitted**.
- Available high-confidence candidate: **none found**.
- Channel: **ACTIVE WATCH**, because funded public tasks exist and new supply changes over time.
- Product: **none selected**.
- WTT/WTP for Waterfound: **none**.
- Revenue: **USD 0**.
- Human gate: **none current**; machine-admissible public discovery remains.
- Privacy producer candidate: **not activated**.

No issue comment, attempt, claim, fork, pull request, external publication, account installation, subscription, spend, contract, credential use, or payment/KYC action occurred.
