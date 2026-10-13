# RMA-DIST-001 — Distribution and payment eligibility research (2026-10-12)

**Provenance:** current official provider documentation linked below. **No channel has been activated, no seller account opened, no lead identified, no external customer engaged, no product selected, no fees incurred.** Feasibility classifications are channel-level, not Waterfound account approvals. All scores are **engineering heuristics**, not observed funnel performance or conversion.

## Deterministic channel-selection heuristic

Gate first: providers that prohibit the proposed commercial use or impose unsatisfied paid-listing scale gates are **ineligible for a first-revenue route regardless of score**. Conditional candidates receive four scored judgments 0..5 (`autonomy`, `no_upfront_cost`, `buyer_relevance`, `self_service_activation`), weighted 35:25:25:15. Composite = sum(component*weight)/5; higher means preferable under the specified constraints. Review/re-score only on new evidence; no inferred leads or traffic.

| Channel | Status | A / C / B / S | Weighted /100 | Evidence & principal risk |
|---|---|---:|---:|---|
| OSS repository + lawful hosted self-service upgrade | CONDITIONALLY_AVAILABLE | 5/4/4/3 | **84** | GitHub repository discovery is a candidate, not proof of inbound demand. Production SaaS host/seller still unconfirmed; OSS maintenance/security/competition costs remain. |
| Product-problem technical documentation + inbound search | CONDITIONALLY_AVAILABLE | 4/5/3/2 | **74** | Works only when product claims and public publication become authorized; SEO volume/conversion not verified. |
| Standalone direct SaaS self-service | CONDITIONALLY_AVAILABLE | 4/3/3/4 | **70** | Technically compatible with mock interface; requires approved commercial host, onboarding, support, payment provider and buyer proof. |
| GitHub Marketplace paid app | BLOCKED for first sale; CONDITIONALLY_AVAILABLE later | 3/2/5/4 | **68 before gate** | Verified publisher *organization*, GitHub App ~100 installs (OAuth ~200 users), monthly+annual pricing, financial onboarding, purchase webhooks. Monthly remittance subject to $500 threshold and 5% withholding. Not a shortcut to first revenue. |
| Integration/reference ecosystem | CONDITIONALLY_AVAILABLE | 3/4/3/3 | **65** | Discoverability depends on an actual integration, publisher terms and real value; no integration built. |
| Approved technical communities (permission-based) | CONDITIONALLY_AVAILABLE | 2/5/3/2 | **60** | No automated posting, scraping or outbound solicitation. Community rules must be verified channel by channel when a product exists. |

`VERIFIED_AVAILABLE` is **not** assigned to a production channel because no Waterfound-specific seller, hosting, product or approval eligibility has been established. `UNVERIFIED` applies to expected traffic, signup completion, acquisition costs and conversion for **all** channels. Marketplace numerical score is shown for comparison only and loses to the hard paid-app gate.

## Binding commercial hosting restrictions

- **GitHub Pages** — BLOCKED for running a commercial SaaS or e-commerce sales site on free hosting: official usage restrictions prohibit it. https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- **Vercel Hobby** — BLOCKED for commercial deployments: the published fair-use policy limits Hobby to non-commercial personal use and explicitly treats selling/advertising services as commercial. https://vercel.com/docs/limits/fair-use-guidelines
- **Cloudflare Pages Free** — CONDITIONALLY_AVAILABLE technical host only, not verified account-level commercial clearance. Official 2026 free limits include 500 monthly builds; terms, traffic, functions, payment flows and account eligibility require separate confirmation. https://developers.cloudflare.com/pages/platform/limits/

## Payment shortlist (not authorized or selected)

- **Paddle** — CONDITIONALLY_AVAILABLE for an eligible **software** product; official MoR fee **5% + US$0.50 per checkout transaction**, no fixed monthly fee listed. Country guidance excludes specified countries but not Brazil; actual seller onboarding remains unverified. **Important:** Paddle explicitly discourages/prohibits human-service-only offerings, so do not assume suitability for the supplier-statement done-for-you service hypothesis. Sources: https://www.paddle.com/pricing ; https://www.paddle.com/help/start/intro-to-paddle/which-countries-are-supported-by-paddle ; https://www.paddle.com/help/start/intro-to-paddle/what-am-i-not-allowed-to-sell-on-paddle
- **Lemon Squeezy** — CONDITIONALLY_AVAILABLE subject to payout/KYC. Official base example **5% + US$0.50** with possible adders **+1.5% international**, **+1.5% PayPal**, **+0.5% subscriptions**; payout fees vary by settlement method and region (official help indicates 1% for non-US bank payouts). Brazil is not listed among bank payout countries in the consulted official page; PayPal-country support is a distinct route. Do not claim Brazil bank payout enabled. https://docs.lemonsqueezy.com/help/getting-started/fees ; https://docs.lemonsqueezy.com/help/getting-started/supported-countries
- **Stripe Brazil** — CONDITIONALLY_AVAILABLE subject to seller/KYC/tax setup. Official Brazilian price **3.99% + R$0.39 for domestic card transactions**, +2% on international cards; *BRL quote cannot be plugged directly into the USD model*. Payment Links/recurring billing costs and regulatory/tax obligations must be checked before provider choice. https://stripe.com/br/pricing
- **GitHub Marketplace billing** — BLOCKED for first paid launch until verified publisher/org and scale conditions. GitHub manages payment collection and retains 5% on transactions after Jan 1 2021. **Payment transfer happens after a monthly $500 threshold**. https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app ; https://docs.github.com/en/apps/github-marketplace/selling-your-app-on-github-marketplace/receiving-payment-for-app-purchases

**Payment recommendation:** no processor commitment until a product and legal seller type are determined. Paddle MoR is a *research candidate* for genuine software. If CR-001 selects a service, re-evaluate terms and do not route it through a software-only MoR by mischaracterizing the sale.

## Proposed first-revenue funnel / objective signals

| Stage | Synthetic event | Product-specific proof required before live use | Failure recovery |
|---|---|---|---|
| Discovery | `discovered` | Legal traffic source/campaign attribution policy | No unapproved tracker/cookie |
| Interest | `interested` | Intent action (docs read/demo request), actual consent | No unsolicited contact |
| Activation | `onboarding_started`, `activated` | Self-service authenticated onboarding completed | Bounded retry + clear support |
| Delivered value | `value_delivered` | Verified job-specific outcome vs manual/substitute | Fail closed or transparent error |
| Checkout | `checkout_simulated_started` | Approved seller, PCI-safe hosted checkout | Retry with stable external ID |
| Payment | `checkout_simulated_completed` | Signed provider source and settled payment verified; mock not sufficient | Verify webhook + provider reconciliation |
| Retention | `retained`, `churned` | Cohort and customer lifecycle rules compliant with privacy law | Cancellation and lawful deletion |

No real collection/analytics is enabled by the candidate.

## Model economics and critical missing inputs

`run_rehearsal.py` computes hypothetical USD **steady-state** contribution, with 5% + $0.50 provider fee as the *simplified base Paddle-price illustration*, **not a processor quote for this customer or settled revenue**. The hypothetical CAC is incurred only for replacements of churned customers; **initial acquisition, taxes, chargebacks, FX, refunds, founder labor, KYC, incident support, legal and accounting costs are excluded**. See the generated JSON for assumptions.

| Scenario | Assumed price | Assumed paying customers | Revenue (hyp.) | Contribution (hyp.) | Break-even customers (hyp.) |
|---|---:|---:|---:|---:|---:|
| Conservative | $29/mo | 3 | $87.00/mo | **$9.15/mo** | 3 |
| Central | $49/mo | 10 | $490.00/mo | **$380.50/mo** | 1 |
| Optimistic | $99/mo | 25 | $2,475.00/mo | **$2,238.75/mo** | 1 |

**Those numbers do not establish viable real-world margins**: zero verified customer WTP, support minutes, churn, channel CAC or compliant hosting quote. Even a modeled break-even of one customer may be unachievable.

## Shortest legitimate route after CR-001 product selection

1. Real differentiating outcome and self-service activation demonstrated under authorized lawful inputs.
2. Product-type-specific privacy, terms, tax and support design; choose compliant host and payment provider (external authority gates).
3. Smallest published documentation + opt-in product-led journey with no invented claims or outbound messaging (publication gate).
4. Hosted signed checkout, server-to-server authoritative payment reconciliation, cancellation and customer transparency (financial/launch gate).
5. Actual discovery → activation → value → paid event plus settlement proof; only then claim first revenue.

**Ratchet:** prioritized next step remains direct buyer/problem/product differentiation evidence under CR-001. RMA-DIST-001 mock support is isolated and does not supersede that selection.
