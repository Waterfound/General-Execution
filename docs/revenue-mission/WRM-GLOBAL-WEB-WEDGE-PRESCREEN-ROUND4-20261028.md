# WRM — Global web wedge pre-screen, round 4 — 2026-10-28

Status: **THREE_HYPOTHESES_KILLED_PRE_BUILD / MATERIAL_BUYER_RISK_OBSERVED / DIRECT_SUBSTITUTES_OR_ACCOUNT_SPECIFIC_TRUTH / DISCOVERY_ACTIVE / NO_PRODUCT_SELECTED**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can one of three consequential catalog or vendor-risk jobs become a low-permission global website product with a distinct one-shot result?

The minimum admission rule remains repeated buyer/problem evidence, narrow verifiable output, a material gap against substitutes, public or user-supplied inputs, and a proof before hosting or checkout.

## Hypothesis 1 — retailer catalog-to-recall matching

### Buyer/problem evidence

Amazon's recall policy makes sellers responsible for products they list, requires rapid action on affected inventory, permits reimbursement of Amazon's recall costs, and allows suspension or permanent removal of selling privileges:

- https://sellercentral.amazon.com/seller-forums/discussions/t/7aa55597c64912247c3120faf8f05497
- https://sellercentral.amazon.com.br/seller-forums/discussions/t/7aa55597c64912247c3120faf8f05497?mons_sel_locale=en_US

The same seller discussion reports recalls/refunds on deactivated products and material retrospective exposure. This is a consequential problem, but not evidence for a missing tool.

Official recall data is machine-readable. CPSC provides a public REST API with product names, descriptions and UPC where present:

- https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
- https://www.saferproducts.gov/FAQs/FrequentlyAskedQuestions11
- https://www.cpsc.gov/Data

### Direct substitution

The proposed CSV-to-recall result is already sold exactly:

- RecallDash accepts CSV or read-only Square catalogs, monitors FDA Food, FDA Drugs, USDA FSIS, CPSC and NHTSA, offers 100 SKUs free and 2,000 SKUs for US$19.99/month: https://recalldash.app/pricing
- recallsapi accepts SKU catalogs as CSV/JSON with UPC, model, NDC, lot, brand or name; checks nine US agencies plus early-warning sources; offers 100 products free and paid plans from US$29/month: https://recallsapi.com/

Both products explicitly link candidates to agency notices and preserve human confirmation, which is the safe boundary for fuzzy matches.

### Decision

**Kill before build.** CSV ingestion, cross-agency matching, free preview, daily monitoring and source links are already available at low prices. A cross-jurisdiction extension alone is not yet a differentiated buyer result and would increase product-safety assurance risk.

Re-enter only if two retailers identify an unsupported jurisdiction or recall source that materially changes a catalog decision, and a public truth set proves better recall without false certainty or compliance claims.

## Hypothesis 2 — SaaS vendor subprocessor and public-policy change monitor

### Buyer/problem evidence

A GRC practitioner asks how teams catch vendor-side changes such as subprocessors, processing locations, DPAs, trust pages and AI disclosures:

- https://www.reddit.com/r/grc/comments/1snlira/how_do_your_catch_vendorside_changes_in_practice/

PageCrawl describes missed vendor emails, expired aliases, varying objection windows and the scale problem across dozens of SaaS vendors:

- https://pagecrawl.io/blog/subprocessor-list-monitoring-saas-compliance

IAPP reports DataGrail research finding that many sampled AI vendors failed to disclose downstream subprocessors, creating a real due-diligence problem:

- https://www.iapp.org/news/a/how-shadow-ai-and-hidden-subprocessors-are-challenging-governance-and-compliance-efforts

These are public problem signals, not Waterfound demand or legal conclusions.

### Direct substitution

The proposed public-page monitoring and evidence result is densely occupied:

- Apify Subprocessor Change Monitor charges US$0.05 per URL check and emits structured added/removed/changed records: https://apify.com/virtual-constructs/subprocessor-change-monitor
- ClauseTrail monitors subprocessor lists, DPAs, privacy policies, terms and AI terms; three vendors are free and paid plans start at US$99/month: https://clausetrail.com/pricing
- TrustVendor monitors subprocessor changes, certifications and trust-center evidence from US$299/month: https://trustvendor.co/pricing/
- CG Alert monitors pricing, terms/SLA, DPA, subprocessors and security changes with URL, timestamp and SHA256 evidence; self-serve plans start at US$499/year: https://www.cg-alert.com/
- UpGuard trust centers let customers subscribe to material subprocessor changes: https://help.upguard.com/en/trust-centers-subprocessor-listings
- opentrust.center preserves public artifacts and review history: https://opentrust.center/monitoring

### Decision

**Kill before build.** URL monitoring, semantic diff, evidence hashes, alerts, document coverage and audit export are already sold across free-to-enterprise tiers. Legal/control impact requires customer contract context and human review.

Re-enter only if repeated buyers identify a decision not produced by these tools and a public fixture proves it without inferring contractual breach or regulatory noncompliance.

## Hypothesis 3 — marketplace catalog restriction eligibility preflight

### Buyer/problem evidence

Amazon requires sellers to satisfy product, category and listing restrictions and may deactivate accounts for unaddressed policy violations:

- https://sellercentral.amazon.com/help/hub/reference/external/G200301050
- https://sellercentral.amazon.com/help/hub/reference/external/R786P4BPEVKTBAG

Amazon's Manage Your Compliance dashboard exposes product-specific document requirements and bulk workflows:

- https://sell.amazon.com/blog/manage-your-compliance
- https://sellercentral.amazon.com.br/help/hub/reference/external/GC35Z63FGCUCUWXX?mons_sel_locale=en_US

Seller discussions show compliance-document review delays and recurring rejection patterns:

- https://sellercentral.amazon.com/seller-forums/discussions/t/c04d30eb-54fd-4540-882a-3c64ebb1c3e4

### Truth boundary and direct substitution

Eligibility is not a public product property. It varies by seller account, marketplace and item condition. Amazon's Listings Restrictions API is the authoritative machine path:

- https://developer-docs.amazon.com/sp-api/docs/get-listings-restrictions

Existing tools already query that account-specific source in bulk:

- Threecolts/Tactical Arbitrage checks up to 1,000 ASIN/UPC/EAN/GTIN identifiers and directs users back to Seller Central as final authority: https://threecolts.support/en/articles/15839864-restriction-checker
- WalSeller checks account-specific eligibility and approval links from US$14.99/month: https://sellercentral.amazon.com/selling-partner-appstore/dp/amzn1.sp.solution.8aeb999d-5556-4543-871a-07432e9a6809
- Seller Assistant includes wholesale-file analysis and bulk restriction checks from US$159.99/year: https://sellercentral.amazon.com/selling-partner-appstore/dp/amzn1.sellerapps.app.8040c52d-357a-41e5-8969-fdc7f14dbd34
- Plug Seller uploads CSV/Excel and returns Amazon's own eligibility reason and approval link: https://plugseller.com/features
- FlipIQ matches supplier catalogs to ASINs, profitability and seller-account eligibility, with a free tier and paid plans: https://sellercentral.amazon.com.br/selling-partner-appstore/dp/amzn1.sp.solution.b1012051-e4e2-46f6-9722-f3abd03138c7

### Decision

**Kill as a public/no-account product.** A public rule checker cannot answer the buyer's actual eligibility question. The authoritative result requires a seller-account connection, and that connected workflow is already occupied.

Re-enter only if a public pre-purchase decision remains valuable before account-specific eligibility, is not already covered by catalog-analysis tools, and can be verified without implying that a seller is permitted to list an item.

## Comparative evidence ledger

| Predicate | Recall matching | Vendor changes | Restriction eligibility |
| --- | --- | --- | --- |
| Consequential buyer problem | Yes | Yes | Yes |
| Public/user-supplied input | Yes | Yes | Catalog is; truth is not |
| Narrow verifiable output | Candidate match | Page-level diff | Account-specific API result |
| Direct substitute | RecallDash, recallsapi | Six named tools | Five named tools + native API |
| Free/low-price entry | Yes | Yes | Yes |
| Material missing result | None found | None found | None found |
| Build admitted | No | No | No |
| Waterfound WTT/WTP/revenue | None / none / USD 0 | None / none / USD 0 | None / none / USD 0 |

## Portfolio decision

All three hypotheses fail differentiation or the low-permission truth boundary. Do not build a recall matcher, vendor-policy monitor or marketplace restriction checker.

The next ACTIVE search should prefer jobs where the authoritative answer can be computed from public artifacts and where incumbents expose raw facts but do not assemble the buyer's decision. Avoid categories where the exact CSV upload, monitoring, evidence and alert workflow is already sold.

## Authority and safety accounting

No live seller account, product catalog, customer file, recall conclusion, compliance judgment, legal conclusion, outreach, proposal, account creation, external installation, website, checkout, publication, contract, payment, KYC, card/crypto setup, paid spend, runtime activation, private producer activation, writer lease, dispatcher, SQLite write or DISPATCH_FENCE action occurred. Privacy P0 remains a non-activated candidate binding. Further read-only commercial discovery remains machine-admissible; no human gate is current.
