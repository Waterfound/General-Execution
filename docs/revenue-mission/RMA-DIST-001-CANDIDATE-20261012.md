# RMA-DIST-001 — Distribution & First Revenue Candidate (2026-10-12)

**State:** RESEARCH_VERIFIED; LOCAL_MOCK_ENGINEERING_VERIFIED; FIRST_REVENUE_PATH_NOT_READY; OPERATIONAL_NOT_VERIFIED.
**Authority:** candidate-only. No outreach, publication, payment, credentials, financial relationship, paid spend, merge, scheduler, or runtime activation.

## Evidence-first reconciliation

- GE PR #46 commercial checkpoint: NO_PRODUCT_SELECTED / NO_WTP / NO_REVENUE. Direct-substitution screens rejected generic supplier-statement, bid-addendum, and agent-dashboard differentiation.
- GE PR #48 already implements a candidate Commercial Progress Ratchet. This document does not duplicate the selector or mutate its state. Direct commercial evidence outranks internal support.
- Systems EP-FC-001 and UFP-001 require actual owner/wake attestation. A checkpoint and synthetic process-restart do not prove unattended commercial operation.
- Passive distribution subfrontier; no interference with CR-001 or other slots.

## Ranked channel feasibility (official sources, 2026-10-12)

Hard restrictions determine eligibility first. Remaining score is a **heuristic**, not measured conversion: autonomy weight 35, zero-upfront-cost weight 25, buyer relevance weight 25, self-service activation weight 15. Four 0..5 inputs; score = weighted sum / 5.

| Route | Disposition | A/C/B/S | Score | Caveat |
|---|---|---:|---:|---|
| OSS + lawful hosted self-service | CONDITIONALLY_AVAILABLE | 5/4/4/3 | 84 | Host, seller, buyer, product not approved |
| Technical docs + organic inbound | CONDITIONALLY_AVAILABLE | 4/5/3/2 | 74 | Search demand, conversion unknown |
| Direct SaaS | CONDITIONALLY_AVAILABLE | 4/3/3/4 | 70 | Commercial host, KYC, value proof unknown |
| Paid GitHub Marketplace | BLOCKED_FOR_FIRST_SALE | 3/2/5/4 | 68 before gate | Organization verified publisher + scale |
| Ecosystem integration | CONDITIONALLY_AVAILABLE | 3/4/3/3 | 65 | No integration released |
| Permission-based communities | CONDITIONALLY_AVAILABLE | 2/5/3/2 | 60 | Rules and permission, no outreach |

No channel currently qualifies as VERIFIED_AVAILABLE to this particular Waterfound seller and product. All customer reach, traffic and conversion estimates remain UNVERIFIED.

Official terms:
- GitHub Pages **cannot** host a commercial business/SaaS sales website free: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Vercel Hobby prohibits commercial use: https://vercel.com/docs/limits/fair-use-guidelines
- Cloudflare Pages Free has an official 500-build/month limit; commercial hosting approval and operational suitability are account-specific, still conditional: https://developers.cloudflare.com/pages/platform/limits/
- Paid GitHub Marketplace: verified organization publisher and approximately 100 GitHub App installs / 200 OAuth users; plan-change webhooks and finance onboarding: https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app
- GitHub retains 5% after 2021; payout once monthly earnings reach US$500: https://docs.github.com/en/apps/github-marketplace/selling-your-app-on-github-marketplace/receiving-payment-for-app-purchases
- Paddle Merchant of Record: 5% plus US$0.50 per checkout, but human-service-only businesses are unsuitable: https://www.paddle.com/pricing and https://www.paddle.com/help/start/intro-to-paddle/what-am-i-not-allowed-to-sell-on-paddle
- Lemon Squeezy base fee 5% plus US$0.50, plus certain international, PayPal, subscription and payout extras; Brazilian bank payouts not established: https://docs.lemonsqueezy.com/help/getting-started/fees and https://docs.lemonsqueezy.com/help/getting-started/supported-countries
- Stripe Brazil domestic card fee 3.99% plus R$0.39, and international-card surcharge: https://stripe.com/br/pricing . Do not combine BRL and USD quotes.

No payment-provider decision: a service hypothesis must not be mischaracterized as software merely to fit a MoR.

## Engineering executed offline in this session

The separate user-delivered ZIP contains candidate.py, test_candidate.py, run_rehearsal.py, research, checkpoint and SHA-256 manifest. Python standard-library / SQLite proof passed **21 of 21 actual local unit tests**. These tests do not run on GitHub CI and the tested code was not added to this GitHub branch.

- candidate.py SHA256: 163feeabee6bef0966a49b96415f2410cff9d26bbbb380ff8a2915943fb66279
- test_candidate.py SHA256: 3565743422678b057d2a8b7ba8ca2a1b426363128633d411d7c57b641f1213bf
- run_rehearsal.py SHA256: 584b71ed07ea14a03c12b47afa41acaf84479effd39b4936352c862db0aa277c

Offline fixtures: synthetic funnel, idempotent mock billing, out-of-order event deferred/replayed, simulated payment success/failure, cancellation, terminal cancel protection, database cold restart, reconciliation and repair. Output: zero actual customers, zero external payments, zero real revenue. No live webhook signatures or processor API were verified. Mock event revisions **cannot** be assumed to exist in actual vendor APIs.

## Hypothetical monthly economics, no actual WTP

Illustrative USD steady-state modeled at 5% plus US$0.50 fees, assumed customer replacement CAC proportional to monthly churn. Excludes initial acquisition, tax, accounting, FX, refunds, chargebacks and unpredictable support.

| Scenario | Price assumed | Customers assumed | Gross modeled | Contribution modeled | Break-even modeled |
|---|---:|---:|---:|---:|---:|
| Conservative | $29/mo | 3 | $87.00 | $9.15 | 3 |
| Central | $49/mo | 10 | $490.00 | $380.50 | 1 |
| Optimistic | $99/mo | 25 | $2,475.00 | $2,238.75 | 1 |

All pricing, churn, acquisition cost, revenue, margins and demand are unvalidated. Values do not prove feasibility.

## Candidate ratchet evidence statuses, without shared state mutation

- Channels researched: VERIFIED_OFFICIAL_SOURCES.
- Feasibility: CONDITIONAL_ACCOUNT_PRODUCT_UNKNOWN.
- Acquisition hypothesis: PROVISIONAL_OSS_AND_INBOUND.
- Distribution candidate: PARTIAL_OFFLINE_MOCK_ONLY.
- Conversion instrumentation and monetization: VERIFIED_LOCAL_SYNTHETIC_ONLY.
- Economic model: HYPOTHETICAL.
- Recovery: VERIFIED_SQLITE_LOCAL_MOCK, NOT_UNATTENDED_OWNER.
- Launch gates: IDENTIFIED_NOT_AUTHORIZED.
- First revenue path: NOT_READY.
- Real operation: NOT_VERIFIED.

## Three causal blockers and next admissible action

1. Product/buyer differentiation: CR-001 still lacks buyer WTP and selected product. Direct real lawful evidence is highest priority.
2. Commercial host and seller/payment onboarding: genuine legal, financial, KYC, privacy and publication gates.
3. Mission-specific unattended productive owner: no attested recurring wake, no live payment/provider reconciliation or production recovery.

Next CR-001 action: obtain a lawfully reusable, independently truth-labeled actual buyer-paid narrow job and compare to a substitute before any product/UI expansion. Only then extend the reusable billing mock to a product-specific live adapter under new authorization. This subfrontier created no new System, no shared writer, no scheduled automation, and no commitment or public campaign.
