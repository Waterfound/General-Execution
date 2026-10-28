# WRM — Global web wedge pre-screen, round 3 — 2026-10-28

Status: **THREE_HYPOTHESES_KILLED_PRE_BUILD / PAID_DEMAND_OR_CATEGORY_SPEND_OBSERVED / DIRECT_SUBSTITUTION_OR_PRIVATE_ACCESS_DOMINATES / DISCOVERY_ACTIVE / NO_PRODUCT_SELECTED**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

This round tests whether three one-shot website jobs can create a result worth paying for without privileged installation, live-system writes, unsupported assurance or a clone of an incumbent.

Admission still requires:

1. repeated public buyer/problem evidence from one segment;
2. a narrow and verifiable input/output;
3. one material result missing from native and adjacent substitutes;
4. public or user-supplied inputs;
5. a one-shot proof before recurrence, checkout or deployment.

## Hypothesis 1 — Shopify CSV import preflight

### Buyer/problem evidence

A recent worldwide Upwork job hired for product listings, bulk CSV uploads and fixing Shopify import errors. The client had spent US$1.8K across 91 hires, but the listing itself was only US$6 fixed price and had 10–15 proposals:

- https://www.upwork.com/freelance-jobs/apply/Shopify-Product-Listing-CSV-Upload-Expert_~022108140114304891418/

Other marketplace offers show that people sell bounded CSV diagnosis and repair:

- US$30 supplier CSV audit: https://www.upwork.com/services/product/development-it-a-clear-audit-of-your-supplier-csv-with-sku-and-price-issues-2103412929646364710
- US$45 tested CSV import fix: https://www.upwork.com/services/product/development-it-a-tested-python-fix-for-your-csv-import-errors-2112689263501400843
- US$200–1,200 import repair tiers: https://www.upwork.com/services/product/development-it-a-repaired-csv-or-excel-import-with-checks-and-a-clear-handover-2097445339022997940

The hired job proves buyer activity, but at a very low observed price and with broader catalog-management labor. Seller offers prove supply, not completed demand at their advertised prices.

### Direct substitution

The exact low-permission website formulation already exists:

- Activory validates a Shopify product CSV locally in the browser, reports row/column/suggested fix, requires no account and is free: https://activory.com/tools/shopify-csv-validator
- CSV SafeCheck is a free browser-local Shopify preflight utility: https://github.com/ReconcileKit/csv-safecheck
- RowReady gives free row-by-row diagnostics and charges US$9 only for a corrected export: https://rowreadycsv.com/
- Matrixify starts at US$20 per 30 days and reports failed imports with downloadable results: https://matrixify.app/pricing/ and https://matrixify.app/documentation/import-data-to-shopify-with-matrixify/
- Shopify documents common import errors itself: https://help.shopify.com/en/manual/products/import-export/common-import-issues

### Decision

**Kill before build.** The proposed input, diagnostics, safe-fix preview, privacy posture and one-time payment are already implemented. The only exact buyer signal found was low-priced and bundled with manual catalog work.

Re-enter only if repeated buyers identify an unsupported Shopify entity or failure class that the current validators and Matrixify do not cover, and a public fixture proves materially better recall without a live-store connection.

## Hypothesis 2 — Stripe subscription revenue-leak audit

### Buyer/problem evidence

A SaaS founder publicly asked how to detect active subscriptions without paid invoices. The discussion identifies unretried payments, expired discounts, metered-usage gaps, missed price migrations and cancelled-but-active states as manual-audit problems:

- https://www.reddit.com/r/SaaS/comments/1q1p6gp/how_do_you_handle_stripe_revenue_reconciliation/

Stripe also documents a concrete class where an active subscription can remain uncollected because invalid tax-location data prevents invoice finalisation:

- https://support.stripe.com/questions/manage-draft-subscription-invoices-with-invalid-tax-location-details

A marketplace service offers a written Stripe billing health report covering webhook handling, retries, dunning, proration, account/database state and plan configuration:

- https://www.upwork.com/services/product/development-it-stripe-billing-health-check-2113202078290826886

These establish a consequential problem and service supply. They do not prove completed Waterfound demand or a gap.

### Direct substitution

The proposed result is already occupied:

- Bleedpoint is a Stripe Marketplace app using read-only OAuth to quantify failed payments, legacy pricing, zombie subscriptions and discount leakage in an audit report: https://marketplace.stripe.com/apps/bleedpoint
- RevReclaim scans Stripe, Polar or Paddle for ten leak types; manual scans and PDF/CSV exports are free, with weekly monitoring at US$29/month: https://revreclaim.com/about
- MRRaudit traces Stripe/ChartMogul MRR differences to customers, invoices and subscription events: https://mrraudit.com/index.html
- Driftcheck reports billing/application drift and directional revenue at risk: https://www.driftcheck.io/
- DriftExact reconciles Stripe billing with product access using a read-only audit: https://www.driftexact.com/

Stripe itself exposes exports for subscriptions, customers, payments and financial reports and offers Sigma/API queries:

- https://support.stripe.com/questions/generic-report-types-at-stripe
- https://support.stripe.com/questions/exporting-payment-data

### Decision

**Kill before build.** A CSV-only audit would be less complete than existing read-only connectors and would duplicate free scans. The commercially important application-entitlement and webhook predicates require private app data or code as well as Stripe state. No unique low-permission result remains.

Re-enter only if two independent SaaS buyers identify a leak class not detected by the named tools and a synthetic truth set plus lawful export proves that class without claims about recoverable revenue.

## Hypothesis 3 — multilingual ecommerce SEO conflict audit

### Paid buyer evidence

Two explicit report-only or audit-first jobs were observed:

1. a completed US$300–500 project requested a one-off audit of UK, Ireland and Europe ecommerce sites, including hreflang, cross-domain ranking conflicts, WooCommerce, speed and actionable recommendations:
   - https://www.freelancer.com/projects/website-audit/comprehensive-independent-seo-website
2. an open €250–750 project posted on 2026-10-28 requests a paid Phase 1 audit for a five-language travel site with 1,680 indexed and 914 non-indexed pages, followed by possible implementation:
   - https://www.freelancer.sg/projects/website-audit/seo-audit-for-multilingual-travel

The open buyer explicitly requires Google Search Console, GA4 and Google Tag Manager access, plus diagnosis of a third-party booking iframe. This is paid demand for an expert audit, not proof that a public crawler report is accepted.

### Direct substitution and access boundary

The machine-detectable public layer is mature:

- Sitebulb crawls cross-domain alternate URLs, validates hreflang, reciprocity, canonicals, noindex conflicts, language declarations and exports a cluster matrix: https://support.sitebulb.com/en/articles/12839791-auditing-international-implementation-with-sitebulb and https://sitebulb.com/product/international/
- Screaming Frog audits hreflang, duplicates, crawl comparisons and can integrate Search Console, Analytics and PageSpeed: https://www.screamingfrog.co.uk/seo-spider/pricing/
- an Apify actor audits HTML, HTTP-header and sitemap hreflang for US$1.20 per 1,000 pages: https://apify.com/kayhermes/international-hreflang-audit-crawler
- an Upwork specialist sells a multilingual/hreflang report for US$59–199: https://www.upwork.com/services/product/marketing-a-multilingual-seo-and-hreflang-audit-for-your-international-website-2113925072168441478

The unresolved buyer value lies in combining private GSC/GA4/GTM evidence, search intent, conversion tracking and human prioritisation. A public synthetic crawl cannot establish those acceptance predicates.

### Decision

**Kill as an autonomous low-permission product.** Do not build another hreflang crawler or claim SEO impact from public markup alone. The exact public layer is commoditised; the valuable residual is credentialed expert service.

Re-enter only if a buyer explicitly accepts a public-only technical subset, a representative comparison shows a missing decision-relevant finding beyond Sitebulb/Screaming Frog/Apify, and no traffic or ranking outcome is claimed without private evidence.

## Evidence ledger

| Predicate | Shopify CSV | Stripe leakage | Multilingual SEO |
| --- | --- | --- | --- |
| Buyer/problem signal | Hired US$6 job; broader catalog work | Public SaaS problem and audit supply | Completed US$300–500 and open €250–750 jobs |
| Narrow verifiable report | Yes | Partly | Public layer only |
| No privileged installation | Yes | CSV-only is incomplete | Public crawl is incomplete |
| Direct substitute | Free/US$9 validators | Free/paid read-only scanners | Mature crawlers and low-cost services |
| Material missing result | None found | None found | Requires private data and judgment |
| Build admitted | No | No | No |
| Waterfound WTT/WTP/revenue | None / none / USD 0 | None / none / USD 0 | None / none / USD 0 |

## Portfolio decision

All three formulations fail before implementation. This prevents Waterfound from confusing visible pain with an unoccupied product opportunity.

The next ACTIVE search must avoid:

- platform-file validation where free local checkers already exist;
- billing leakage categories with read-only marketplace apps;
- public technical SEO findings whose decision value depends on private performance data and expert judgment.

Prefer a decision that buyers currently assemble from multiple public sources, where the native systems expose facts but no incumbent offers the combined one-shot result.

## Authority and safety accounting

No bid, proposal, outreach, comment, account creation, website, checkout, publication, customer file, live crawl, private analytics access, Stripe connection, contract, payment, KYC, card/crypto setup, paid spend, runtime activation, private producer activation, writer lease, dispatcher, SQLite write or DISPATCH_FENCE action occurred. Privacy P0 remains a non-activated candidate binding. Further read-only commercial discovery remains machine-admissible; no human gate is current.
