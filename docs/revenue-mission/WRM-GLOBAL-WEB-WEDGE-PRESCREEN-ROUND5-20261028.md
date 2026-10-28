# WRM — Global Web Wedge Prescreen, Round 5 — 2026-10-28

Status: **THREE_CANDIDATES_KILLED_PRE_BUILD / BUYER_SIGNALS_OBSERVED / NO_PRODUCT_FREEZE / DISCOVERY_ACTIVE**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can any of three current, globally deliverable, read-only website jobs produce a decision-relevant report from public or user-supplied inputs, without privileged installation, while remaining materially better than native and adjacent substitutes?

This round applies the Commercial Progress Ratchet. No runtime, telemetry, dashboard, connector, checkout, or generic governance work is admitted unless a candidate first survives substitution.

## Candidate 1 — GPSR online-offer field checker

### Buyer and problem evidence

Seller evidence is real. Amazon seller-forum reports describe listings removed or repeatedly placed at risk because manufacturer and EU responsible-person details are treated as missing, including a report involving more than 1,500 ASINs and repeated submissions.

Sources:

- https://sellercentral.amazon.com.mx/seller-forums/discussions/t/35b14023-4c90-4f49-b456-9532ddb174b3
- https://sellercentral.amazon.com.br/seller-forums/discussions/t/bcbb9f37-ba7b-452c-9661-c30f6464c030

A Shopify community offer advertised five beta listing-readiness audits at USD 49, covering up to three product groups, manufacturer and responsible-person fields, identifiers, warnings, document gaps, snippets, and a PDF report. This is an offer and feedback request, not verified sales or Waterfound WTP.

Source: https://community.shopify.com/t/offer-49-gpsr-listing-readiness-audit-for-shopify-sellers-selling-to-eu-ni/623000

### Substitution result

The public-page checker is already directly occupied:

- EcoClaim scans product pages for manufacturer, EU contact, product ID, and warnings, with free re-checks.
  - https://ecoclaim.eu/gpsr-product-safety-check
- ComplyFolio accepts up to five product links and generates structured GPSR online-offer findings in a free public beta.
  - https://complyfolio.com/gpsr-online-offer-checker
- GPSR Safety Sync provides product-page panels, bulk fill, multilingual display and downloadable reports; free up to 25 products and USD 12.99/month for unlimited products.
  - https://gpsrsync.com/
- Alnage advertises a catalog scanner, 24-language support, marketplace exports and recall matching, with a free tier and paid plans from USD 9.95/month.
  - https://pickyourapp.com/products/gpsr-compliance-hub
- Shopify's app marketplace lists a GPSR suite with duplicate/incomplete detection, compliance score breakdown, CSV/JSON audit export and plans from free through USD 79.99/month.
  - https://apps.shopify.com/eu-gpsr-compliance-suite-pro
- Complimus includes unlimited GPSR fields free and monetizes broader EU-commerce modules.
  - https://complimus.com/pricing

### Decision

**KILL.** A Waterfound URL scanner would duplicate free direct substitutes. The residual Amazon problem is not public-page detection: it is an account-specific, opaque submission and review loop. A public checker cannot prove why Amazon rejected private submissions or restore listings.

No build is justified.

## Candidate 2 — App Store age-rating / submission-readiness preflight

### Current operational signal

Apple's current requirements state that updated age-rating questions are required for app submissions and updates. Apple also added social-media capability questions in July 2026 and required responses beginning in September 2026. The answers live in App Store Connect and depend on actual app capabilities, including AI assistants and user-generated content.

Sources:

- https://developer.apple.com/news/upcoming-requirements/
- https://developer.apple.com/news/
- https://developer.apple.com/help/app-store-connect/manage-app-information/set-an-app-age-rating

### Substitution and truth boundary

- AuditStore already connects to App Store Connect, checks real submission data, includes the new social-media age-rating questions, and links findings to the relevant App Store Connect pages.
  - https://apps.apple.com/us/app/auditstore/id6787727965
- StoreShield already performs local archive readiness checks for privacy manifests, SDKs, entitlements and submission metadata, exporting a submission pack.
  - https://apps.apple.com/us/app/storeshield/id6767630916

A public App Store page does not expose the questionnaire responses or enough application behavior to determine truthful answers. A public-only Waterfound checker would either be shallow metadata linting or infer sensitive content inaccurately.

### Decision

**KILL.** The decision-relevant truth requires App Store Connect data and product behavior; direct tools already cover the privileged path. No public fixture can prove the acceptance predicate.

## Candidate 3 — cross-channel offer/listing consistency report

### Buyer evidence

A recent worldwide Upwork listing offered USD 40 fixed price for an audit across Shopify, Amazon, eBay, and TikTok Shop, including listing quality, pricing, competitor analysis, and an action plan.

Source: https://www.upwork.com/freelance-jobs/apply/commerce-Business-Analysis-Shopify-Amazon-eBay-TikTok-Shop_~022112585237682334640/

A separate Shopify migration audit offered USD 400 fixed price, but required private app, catalog, checkout, tracking, and analytics review plus a consultation. It proves budget for expert migration assurance, not for a public URL-diff product.

Source: https://www.upwork.com/freelance-jobs/apply/Shopify-Store-Pre-Launch-Audit-Migration-Quality-Check_~022110684606185178378/

### Narrow formulation tested

Given two to eight channel representations of the same offer, flag contradictions in explicit same-currency price, refund window, access wording, and file-format claims, preserving exact source quotes.

### Direct substitute

That exact narrow job is already sold by an Apify actor for USD 10 per 1,000 offer audits. It compares pasted English copy from two to eight channels and emits source-quoted differences in price, refunds, access wording and file-format mentions.

Source: https://apify.com/a.klimm67/cross-channel-offer-consistency-audit/api

Adjacent substitutes cover the broader catalog job:

- Sellenvo offers a free no-signup listing analyzer accepting links, screenshots or pasted content.
  - https://sellenvo.com/listing-analyzer/
- Listing Mirror synchronizes product details, prices, variants and inventory across Shopify and major marketplaces from USD 149/month.
  - https://apps.shopify.com/listing-mirror
- Akeneo and Syndigo provide cross-channel product-data validation, syndication and mismatch alerts for larger operators.
  - https://www.akeneo.com/activation/
  - https://syndigo.com/syndication/

### Decision

**KILL.** The precise read-only report is directly occupied at commodity pricing. Broader value belongs to account-connected syndication or expert merchandising, both outside the zero-permission public proof.

## Evidence ledger

| Predicate | GPSR checker | App age-rating preflight | Cross-channel consistency |
| --- | --- | --- | --- |
| Buyer/problem evidence | Seller disruption + USD 49 offer | Current Apple submission requirement | USD 40 and USD 400 buyer postings |
| Public/user-supplied proof feasible | Yes, but shallow | No, decisive answers are private/behavioral | Yes |
| Direct substitute | Multiple free and paid tools | AuditStore + StoreShield | Exact Apify actor |
| Material differentiation | Falsified | Falsified | Falsified |
| Waterfound demand/WTT/WTP | None | None | None |
| Quantified buyer value | None | None | None |
| Revenue | USD 0 | USD 0 | USD 0 |

## Kill criteria applied

Reject before build when any one holds:

1. a free or low-cost direct substitute already produces the same decision output;
2. decisive truth is private, account-specific, provider-opaque, or requires behavioral/professional judgment;
3. the observed buyer scope is primarily implementation, consulting, or privileged remediation;
4. the only residual advantage is provenance formatting, generic governance, or a dashboard;
5. the public proof cannot test the buyer's actual acceptance predicate;
6. the candidate has no plausible price room after direct substitute pricing.

All three candidates hit at least one criterion.

## Active–Secondary–Passive decision

- **ACTIVE:** buyer-posted problem discovery for a public or user-supplied, self-serve outcome not already sold as a direct checker.
- **SECONDARY:** re-check candidates only when new buyer evidence changes the acceptance predicate or substitute set.
- **PASSIVE / SUPPORT_ONLY:** GPSR field extraction, app-submission metadata linting, cross-channel offer diffs, generic evidence packs, dashboards, runtime and telemetry.

## Next machine-admissible frontier

Do not run another broad idea list or build a generic scanner. Mine current buyer-posted scopes for a **single bounded deliverable** that satisfies all of:

1. the buyer names an acceptance artifact rather than broad consulting;
2. inputs can be public or voluntarily uploaded without privileged installation;
3. at least one recent budget or paid substitute establishes spending;
4. no direct substitute provides the same decision at commodity pricing;
5. a synthetic or public fixture can falsify the output before outreach;
6. the output avoids legal, medical, financial, security-certification, or platform-approval conclusions.

Only after one job passes this screen should Waterfound create a minimal proof. External outreach, publication, account installation, checkout, payment/KYC, paid spend and contracts remain separate gates.

No website, account, outreach, commercial publication, checkout, card/crypto integration, payment, spend, runtime activation, private producer activation, writer lease, dispatcher, SQLite write, or DISPATCH_FENCE action occurred.
