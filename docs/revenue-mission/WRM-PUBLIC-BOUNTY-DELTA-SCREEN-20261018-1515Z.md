# WRM — Public Bounty Delta Screen — 2026-10-18 15:15 UTC

## Decision

`REAL_FUNDED_BOARD_FOUND / ALL_OPEN_SPACEAPP_TASKS_MATERIALLY_CONTESTED / FALSE_POSITIVES_REMOVED / NO_PRIVATE_PROOF_ADMITTED / NO_PRODUCT_SELECTED`

Observed Waterfound revenue: **USD 0**.

This delta tests whether newly surfaced public software bounties contain one credible, unassigned, low-contention task whose acceptance can be reproduced privately before any claim, pull request, payment onboarding, or public commitment.

## 1. SpaceApp: payment rail credible, claimability absent

SpaceApp publishes six open cash bounties. Each issue states that maintainers pay the author of the first merged qualifying pull request within seven days, by PayPal, Wise, or bank transfer. The maintainer also confirmed publicly that the US$600 Podman issue remains open and that Wise/bank transfer are supported.

The live contention screen shows that the board is real but currently unsuitable for new work:

| Issue | Reward | Public issue comments | Distinct public participants | Explicit linked PRs observed in comments | Decision |
|---|---:|---:|---:|---:|---|
| #60 — real Temporal time-skipping and replay gate | US$400 | 34 | 21 | at least 8, plus a later #195 submission | Reject: crowded |
| #61 — OTLP spans across Temporal workflows | US$600 | 32 | 22 | at least 5 | Reject: crowded |
| #62 — WebGL renderer for 50,000 graph nodes | US$750 | 37 | 22 | at least 8, plus later #134/#189 submissions | Reject: crowded |
| #63 — rootless Podman launcher | US$600 | 25 | 16 | at least 5 (#77, #81, #117, #144, #183), with other claimed submissions | Reject: crowded |
| #64 — per-service container images | US$400 | 32 | 20 | at least 4 | Reject: crowded |
| #65 — one-command full source stack | US$450 | 36 | 22 | at least 8 | Reject: crowded |

Issue sources:

- https://github.com/oll4com/spaceapp/issues/60
- https://github.com/oll4com/spaceapp/issues/61
- https://github.com/oll4com/spaceapp/issues/62
- https://github.com/oll4com/spaceapp/issues/63
- https://github.com/oll4com/spaceapp/issues/64
- https://github.com/oll4com/spaceapp/issues/65

The reward range is material and the acceptance scopes are explicit. That establishes a credible public paid-work channel. It does not make any current issue rational to enter: payment is winner-takes-first-merged, maintainers do not pre-review open PRs, and each task already has multiple implementations or active attempts. Building another full solution would have low expected value and high duplication risk.

## 2. Fiddy US$2,048: not a contributor bounty

The Fiddy issue describes a product being built to compete for an external Farcaster prize. Its own progress report says the CLI, microsite, rebrand, and deploy agent already exist; remaining work includes UI integration, a fresh-VPS run, an agent hatch flow, and a human endorsement.

The US$2,048 is the prize the maintainer hopes the Fiddy product will win. The issue does not promise that amount to an outside contributor, and a public commenter has already asked whether a residual UI slice could be separately funded. No fixed residual budget or contributor payment commitment was observed.

Source: https://github.com/ivcained/fiddy/issues/1

Decision: reject as a Waterfound revenue target until the maintainer publishes a separately funded, bounded residual scope. Do not treat speculative prize sharing as WTP.

## 3. Paraloom: reports already paired with implementations

Fresh Paraloom “BOUNTY” issues are security reports submitted to the program, not clean unclaimed implementation tasks. Representative issue #1004 already links a completed wallet implementation in PR #95 and includes a settlement address.

Sources:

- https://github.com/paraloom-labs/paraloom-core/issues/1004
- https://github.com/paraloom-labs/paraloom-wallet/pull/95

Decision: reject as already claimed/implemented. Do not duplicate a submitted disclosure or infer that an open report is an open coding bounty.

## 4. Small community rewards

The fresh Salam community task pays AUD 5 for a first accepted multi-file project and requires installation of its VS Code extension, a public repository, promotional references, a star/fork, and more than five meaningful commits.

Source: https://github.com/SalamLang/Salam/issues/1713

Decision: reject. The compensation is immaterial relative to build, publication, installation, review, and collection effort; the promotional requirements also make it a poor fit for evidence-first revenue work.

## Admission rule retained

A public bounty enters private proof only when all of the following are independently verified immediately before work:

1. the issuer, exact cash amount, payment route, and acceptance authority are credible;
2. the issue is open, unassigned, and not merely a proposal, disclosure, contest entry, or speculative prize share;
3. there are zero active issue-specific implementations, or the issuer has defined a separately payable residual;
4. acceptance is objective and reproducible locally with the available toolchain;
5. no restricted hardware, customer secret, paid service, prohibited access, or credential expansion is required;
6. expected reward materially exceeds implementation, review, contention, and collection risk;
7. public claim, comment, fork, pull request, contract, and payment/KYC remain deferred until separately authorized.

## Outcome

- Credible paid channel: **observed**.
- Current high-confidence target: **none**.
- Private implementation: **not admitted**.
- Product: **none selected**.
- Waterfound WTT/WTP: **none**.
- Revenue: **USD 0**.
- Current human gate: **none**; public-source discovery remains machine-admissible.
- Privacy producer candidate: **not activated**.

No issue comment, attempt, claim, fork, pull request, account installation, external publication, subscription, spend, contract, credential use, customer access, or payment/KYC action occurred.
