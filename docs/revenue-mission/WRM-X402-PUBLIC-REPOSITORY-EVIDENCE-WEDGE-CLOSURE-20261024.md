# WRM — x402 Public Repository Evidence Wedge Closure

Date: 2026-10-24  
State: `MACHINE_DELIVERABLE / DIRECT_NATIVE_AND_FREE_SUBSTITUTES / WEAK_PAID_BUYER_SIGNAL / CANDIDATE_KILLED`  
Observed Waterfound revenue: **USD 0**

## Narrow job tested

Given a public GitHub repository and exact ref, return one machine-readable release-evidence packet covering:

- ref and commit identity;
- CI/workflow security findings;
- dependency-change and known-vulnerability evidence;
- repository security-health signals;
- build artifact provenance/attestation availability;
- explicit missing evidence and a bounded `READY / CAUTION / NOT_READY / INSUFFICIENT_EVIDENCE` result.

The proposed buyer was an autonomous software agent choosing whether to consume, build or release public code. Delivery would be read-only and compatible with a pay-per-call x402 endpoint.

## Why this candidate was selected

This candidate overlaps Waterfound's demonstrated strengths in exact-ref reconciliation, evidence provenance, authority stops and source-linked review. It also avoids customer credentials when limited to public repositories.

The commercial question was not whether Waterfound could implement it. The question was whether agents presently pay for this combined decision more than they already obtain from native and free tools.

## Observed paid-market evidence

Agentic Market exposes trailing 30-day call and unique-payer counts for indexed x402 endpoints. Relevant public observations on 2026-10-24:

| Existing endpoint | Price | 30-day calls | 30-day payers | Commercial reading |
| --- | ---: | ---: | ---: | --- |
| Cult OS verified pull-request review | $0.20 | 16 | 2 | repeated use but only two observed payers |
| Cult OS PR triage | $0.20 | 2 | 2 | minimal buyer signal |
| Cult OS repository vulnerability audit | $0.20 | 26 | 3 | repeated use concentrated among three payers |
| NetIntel GitHub repository analysis | $0.03 | 1 | 1 | no repeat-market evidence |
| agent402.tools GitHub repository enrichment | $0.005 | 8 | 4 | small commodity-enrichment demand |
| x402 Hono secret scan | $0.01 | 3 | 3 | minimal buyer signal |
| x402 Hono CVE lookup | $0.01 | 4 | 3 | minimal buyer signal |
| Cult OS Dockerfile audit | $0.01 | 35 | 23 | broader demand for one bounded deterministic check |
| Cult OS HTTP header audit | $0.001 | 85 | 33 | broader demand for a very cheap public primitive |
| Cult OS hash/integrity utility | $0.001 | 108 | 33 | broader demand for a commodity deterministic primitive |

Sources:

- https://agentic.market/services/www-cultos-dev
- https://agentic.market/services/netintel-dev
- https://agentic.market/services/agent402-tools
- https://agentic.market/services/x402-hono-api-inraby-workers-dev

These catalog metrics are buyer signals, not proof of payer independence, satisfaction, retention, profitability or successful delivery. The x402 authenticity screen separately established that transaction activity can be manufactured or internally clustered. Even on their face, however, the repository-review products show much weaker distinct-payer reach than cheap generic primitives.

For comparison, unrelated x402 services with large observed reach include public on-chain reads with hundreds of distinct payers, Exa search with thousands of calls and dozens of payers, and a token-verdict endpoint with thousands of payers. This indicates that the marketplace can expose substantial demand when it exists; the repository-evidence cluster has not shown comparable reach.

Sources:

- https://agentic.market/services/api-onesource-io
- https://agentic.market/services/api-exa-ai
- https://agentic.market/services/www-ax1-vc

## Direct substitution

The proposed evidence components are already available without a Waterfound endpoint:

1. GitHub dependency review exposes dependency additions, removals, updates and vulnerability information in pull requests and can be enforced with a required action.
   - https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review
   - https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action

2. OpenSSF Scorecard evaluates repository security practices and publishes weekly public-repository results.
   - https://github.com/ossf/scorecard
   - https://github.com/ossf/scorecard-action

3. GitHub artifact attestations establish and verify build provenance, including offline verification support.
   - https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds
   - https://docs.github.com/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline

4. zizmor audits GitHub Actions and related CI configuration, supports auditor mode, SARIF and GitHub annotations.
   - https://docs.zizmor.sh/
   - https://docs.zizmor.sh/audits/
   - https://docs.zizmor.sh/integrations/

A combined packet could improve convenience, but convenience packaging is not yet a material differentiated decision outcome. The earlier exact-SHA CI-review candidate also found only a single read-only buyer outlier and was demoted to `SUPPORT_ONLY`.

## Falsification result

The candidate fails both required commercial tests:

- **Differentiation:** the decisive evidence primitives are native or free; the residual advantage is aggregation and wording.
- **Demand:** directly adjacent x402 products show only one to four distinct payers for repository analysis and two to three for higher-priced review/audit products during the measured period.

Building a new scanner, score, API or dashboard would therefore add supply before there is evidence of an unmet paid decision.

## Decision

Kill the standalone x402 public-repository release/evidence product before build.

Preserve exact-ref reconciliation, provenance accounting and authority-stop logic as internal capabilities and future product components only. Do not create an endpoint, wallet integration, public host, pricing page, score, badge, marketplace listing or self-funded demand test.

## Re-entry criteria

Re-enter only if all are true:

1. at least one observable agent/buyer requests a decision output missing from GitHub, OpenSSF, zizmor and existing x402 services;
2. the missing output changes an objective consume/release decision, rather than merely aggregating reports;
3. multiple plausibly independent payers or an equivalent external signal support that exact output;
4. a local proof beats separate native/free tools on one measured outcome such as false-negative rate, time-to-decision or provenance coverage;
5. the proof remains public-input, bounded, privacy-safe and materially automated.

No code, product, endpoint, wallet, account, public publication, paid call, self-payment, outreach, pricing commitment, spend, contract, payment/KYC, Privacy P0 activation or state-dispatcher write occurred.
