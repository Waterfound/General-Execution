# WRM Public Bounty Screen — 2026-10-16

## Decision

**NO MACHINE-ADMISSIBLE, HIGH-CONFIDENCE BOUNTY SELECTED.**

The direct-bounty channel remains a read-only discovery frontier. No bounty was claimed, no maintainer was contacted, no external account was created, no code was submitted, and no payment path was entered.

This screen tests a narrow commercial predicate: **is there a currently open, issuer-verifiable, unassigned bounty whose acceptance can be reproduced locally before any human, credential, hardware, publication, or payment gate?**

## Admission filter

A candidate must satisfy all of the following before implementation:

1. issuer and repository have credible operating history;
2. reward and payer are explicit enough to distinguish a funded opportunity from an unverified issue label;
3. no assignee or materially complete competing implementation;
4. acceptance is bounded and mechanically reproducible;
5. proof can be built without physical hardware, private credentials, paid services, public claims, or outreach;
6. expected value remains positive after competition, payout uncertainty, and verification cost.

## Screened candidates

| Candidate | Reward shown | Public evidence | Decision |
|---|---:|---|---|
| Tenstorrent `tt-metal#51655` | US$1,000 | Open but assigned to `kinginu`. | Reject: assigned. |
| Tenstorrent `tt-metal#58986` | US$1,000 | Open but assigned; maintainer declined another claimant and a PR already exists. | Reject: assigned/duplicated. |
| Tenstorrent `tt-metal#8621` | US$500 | Closed/completed; payment initiation recorded. | Reject: stale external radar. |
| WarpSpeed `warpspeed-bounties#4` | US$750 | 72 comments, several claims/submissions, and signup plus maintainer confirmation required before work. | Reject: crowded and claim-gated. |
| Spectral `lux#75` | US$1,500 | Multiple submitted implementations; repository last pushed 2025-12-15. | Reject: duplicated and maintenance uncertainty. |
| Spectral `lux#103` | US$500 | Multiple claims and PRs. | Reject: duplicated. |
| microG `GmsCore#2843` | US$2,340 | Requires support across arbitrary recent WearOS devices, physical-device testing, maintainer acceptance, and has 179 comments plus prior submissions. | Reject: hardware-dependent, broad, crowded. |
| aeternity `bounties#6` | CHF 1,500 | Existing Linguist PRs/grammars cover the scope; upstream maintainer says the remaining blocker is organic adoption across at least 200 qualifying repositories. Recent bounty-status questions remain unanswered. | Reject: work duplicated; outcome controlled by external adoption. |
| Aquarium of Gullibles `#4` | US$500 USDC shown | Repository created and pushed on one day, tiny/no-license, 0 stars, 48 open issues; a competing PR already exists. | Reject: counterparty credibility and duplication risk. |
| Parabola `parabola#5` | US$125 | Repository created 2026-10-15, 0 stars, 29 forks, 22 open issues; bounty already has multiple claimant/solution comments and no confirmed payment terms in the issue discussion. | Reject: newborn issuer, crowded, unverified payout. |
| Go-Hybrid reward pool | US$500 pool; top item US$75 | Low individual value and visible competition. | Reject: expected value below threshold. |

## Evidence links

- Tenstorrent assigned bounties: https://github.com/tenstorrent/tt-metal/issues/51655 and https://github.com/tenstorrent/tt-metal/issues/58986
- Tenstorrent completed bounty: https://github.com/tenstorrent/tt-metal/issues/8621
- WarpSpeed email threads bounty: https://github.com/warpspeedopen-source/warpspeed-bounties/issues/4
- Spectral event monitoring and component bounties: https://github.com/Spectral-Finance/lux/issues/75 and https://github.com/Spectral-Finance/lux/issues/103
- microG WearOS bounty: https://github.com/microg/GmsCore/issues/2843
- Aeternity Sophia bounty: https://github.com/aeternity/bounties/issues/6
- Parabola AbortSignal bounty: https://github.com/Parabola-org/parabola/issues/5
- Parabola repository metadata: https://api.github.com/repos/Parabola-org/parabola

## Commercial evidence classification

- **Capability evidence:** Waterfound can discover, verify, and eliminate stale, assigned, duplicated, hardware-bound, and counterparty-risk bounty opportunities without spending or contacting anyone.
- **Observed outcome:** ten named candidate opportunities were reduced to zero admissible implementations using public evidence.
- **Differentiation evidence:** none for a sellable product; this was revenue-channel screening, not product validation.
- **Demand evidence:** the listed rewards show sponsor interest in specific work, but no Waterfound demand or willingness-to-try.
- **WTP / revenue evidence:** none. No reward has been earned, promised to Waterfound, or contractually secured.

## Kill and re-entry criteria

Do not implement or claim a public bounty unless all admission-filter items are satisfied. Kill immediately when any of the following is found:

- assignment or materially complete competing PR;
- reward, payer, or payment trigger is unverified;
- issuer history is too thin to support counterparty confidence;
- acceptance depends on physical hardware, private access, paid infrastructure, or uncontrolled market adoption;
- required public claim/outreach precedes a locally reproducible feasibility proof;
- expected reward is not commensurate with implementation and review risk.

Re-enter only for a newly posted candidate with credible issuer history, explicit funded terms, no active claimant, bounded tests, and a proof that can be completed privately before any external gate.

## Mission posture

- **ACTIVE:** read-only search for a higher-confidence paid problem with direct evidence of payer, assignment exclusivity, and reproducible acceptance.
- **SECONDARY:** public bounty channel; useful only when a candidate clears the admission filter.
- **SUPPORT_ONLY:** additional bounty-scraping, dashboards, or monitoring infrastructure. Manual/API search is already sufficient to answer the current predicate.
- **HUMAN_GATE:** none currently. Machine-admissible commercial discovery remains.
