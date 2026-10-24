# WRM — Observed buyer spending intent vs software substitution (2026-10-12)

**State:** REAL PUBLIC PROCUREMENT SIGNAL / DIRECT SUBSTITUTE SCREEN / NO PRODUCT PROMOTION.  
**Ratchet:** Buyer/problem -> actual posted buyer budget and visible hire -> differentiated, autonomously deliverable outcome.  
**Scope:** Public-source research only; no bids, outreach, account signup, payments, customer files, claims of product WTP or production deployment.

## Strongest new signal: recurring supplier-statement reconciliation

A publicly visible Upwork job, **Invoice to Statement Reconciliation**, requests recurring monthly matching of supplier statements against invoices, missing-document detection and discrepancy review. As inspected 2026-10-12, the listing specifies **$5-$20/hour**, **less than 30 hours/week**, **6+ months** and shows **one hire**, an active contract and **three hours** in the client's profile. This is a *real buyer request for paid labor* with a visible engagement signal, substantially stronger than anonymous frustration or a vendor's published SaaS price. It does **not** establish that this buyer would pay for software, what the hire was paid, whether the hire is for exactly this job, or that a machine could deliver an equivalent service.

Source: https://www.upwork.com/freelance-jobs/apply/Invoice-Statement-Reconciliation_~022107967499694032024/

Independent but broader adjacent spend signal: a hotel-bookkeeping job explicitly describes approximately **GBP 250/month** for ongoing bookkeeping including supplier/creditor reconciliation and requests a bookkeeping **company**, not a software license. Its responsibilities are much wider than statement matching; do not count it as an independent sale for the exact narrow job.

Source: https://www.upwork.com/freelance-jobs/apply/Hotel-bookkeeper_~022095139717329009705/

## Direct incumbent substitution (verified vendor marketing, not parity testing)

1. **Reconciles** explicitly sells supplier-statement vs AP-ledger export matching, including invoice, credit memo, payment and amount discrepancies, with browser-side processing and no card to try; published plans start at **$888/year**. Directly substitutes a generic upload-two-files reconciliation application. https://reconciles.ai/vendor-statement-reconciliation-software
2. **Cloudsquid** explicitly advertises PDF/email/CSV supplier statement extraction, matching to open AP invoices/payments, missing-credit flags and human review. Directly substitutes a generic statement-to-ledger exception list. https://www.cloudsquid.io/solutions/vendor-statement-reconciliation/
3. **Medius** explicitly markets AI supplier statement reconciliation with missing/mismatched invoice and duplicate detection. Directly substitutes the basic capability at enterprise scale. https://www.medius.com/solutions/medius-accounts-payable-automation/statement-reconciliation/
4. **Invogi** offers a no-integration CSV/XLSX AP-risk scan for duplicate invoices and supplier anomalies, with 500 free records; adjacent rather than complete statement-matching parity. https://invogi.com/product/ap-risk-scan

No installed competitor output, independent benchmark, confirmed competitor retention, customer willingness to pay for WRM or actual revenue has been observed. Vendor price is **an offer**, not evidence of customer payment.

## Commercial decision — an important distinction

**KILL** generic reconciliation software, upload/export UI, duplicate-invoice scan and statement exception dashboards as *unique differentiators*: these are explicitly advertised by direct substitutes.

**DO NOT KILL THE ENTIRE JOB JUST BECAUSE A BIGGER VENDOR EXISTS.** The live request for a recurring human service suggests a separate, still-unproven hypothesis: some buyers may prefer a **done-for-you, monthly, exception-only, source-cited supplier-statement reconciliation service** to operating software themselves. This is a *service preference hypothesis*, not a demonstrated market gap, pricing opportunity, or authorization to take customer data. A lower-friction service may win even where a software product exists, but only if correctness, acquisition and operations can be demonstrated.

**HOLD_UNPROVEN / NO_BUILD** for that service hypothesis: real supplier documents are confidential; the machine currently lacks a permitted representative matched supplier-statement + AP-ledger + independently labeled exception set. Accurate dispute handling, missing-document follow-up, payment authority and customer privacy create genuine operational risks. No observed proof that a service can be sold and fulfilled with near-zero Waterfound time, nor that its cost beats available alternatives. A synthetic parser would not answer those questions.

## Secondary observed pain — construction door-hardware extraction

A 2026-03-07 construction-manager discussion explicitly asks for AI tooling worth paying for. A respondent reports a tool failing to list doors by hardware set after ten doors and making an error. The specific buyer, vendor and test input are unverified. This is a **specific observed product failure**, not proof of a market gap.

Source: https://www.reddit.com/r/ConstructionManagers/comments/1rna2ye/are_there_any_legitimately_good_ai_tools/

Direct specialist claims already cover full opening-to-hardware-set mapping and review: https://d8.bild.ai/division-8 ; https://fastbid24.com/products/doors-hardware ; https://www.pytrel.com/ ; https://www.dfhtools.dev/ . Some are explicitly human-verified; one preview disclaims a live AI service. Therefore **KILL generic door/hardware schedule extraction as unique**, and do not build from this one failure report. A demonstrably superior completeness/error-rate test against the same lawful public corpus remains possible but has no buyer-linked proof.

## Ratchet successor: one concrete commercial discriminator

**ACTIVE:** find a lawful real-world, independently truth-labeled supplier-statement reconciliation case (or other similarly strong public buyer-paid job) for which the incumbent output can be directly compared. Evaluate whether an *autonomous done-for-you service* produces a correct exception memo with meaningfully less buyer effort than the native self-service tool. Count a valid customer-paid engagement separately from a marketplace listing.

**SECONDARY:** retain construction/addendum and agent-PR candidate tooling only for a demonstrably superior case; no feature expansion.

**PASSIVE:** customer contact, proposals, account onboarding, real customer data, payment/KYC, spending, commercial publication, merges and runtime changes.

**Bounded fallback:** If no lawful paired documents/ground truth and no no-account incumbent comparison are available, stop this reconciliation hypothesis at `EVIDENCE_GAP` and search a different publicly budgeted job with safe public input and full machine-deliverability. Do not continue building a dashboard or instrumentation to fill an evidence void.

## Evidence accounting

- **New concrete buyer-spend signal:** 1 directly relevant posted job with a visible hire, plus 1 adjacent broader recurring-service budget.
- **New direct/adjacent vendor offers inspected:** 4.
- **New actual customer payment for WRM:** 0.
- **New verified product differentiation:** 0.
- **New code or deployed product:** 0.
- **Customer demand/WTP for WRM:** UNKNOWN.
- **Mission-specific UFP cold restart/owner attestation:** NOT PROVEN.
- **Authority created or expanded:** false.

A real public job posting plus visible hiring activity improves **commercial evidence quality** relative to unsourced ideation, but does not justify freezing a product or reporting increased completion percentage.


## 2026-10-16 public parity result — service hypothesis closed at the matching core

The previously missing lawful comparison fixture is now available. Two public synthetic pairs were inspected:

1. F20 FinanceOps publishes a vendor statement and AP ledger with one same-reference amount mismatch (USD 960.52 versus USD 915.52) and offers a free, no-account browser reconciliation tool. Source: https://finops.focus20labs.com/samples/ and https://finops.focus20labs.com/tools/vendor-reconciliation/
2. SupplierRecon publishes fictional supplier-statement and AP-ledger samples containing an exact match, a one-cent variance, a one-to-many split, and an unmatched credit. Source: https://supplierrecon.com/supplier-reconciliation-template/

A live, read-only run of SupplierRecon's public sample on 2026-10-16 completed locally in the browser without an account or customer data. The incumbent produced:

- 184 exact matches;
- 7 review candidates;
- 3 unmatched records;
- a USD 1,240.00 reported difference;
- explicit grouped and ambiguous classifications;
- row-level provenance, deterministic candidate equations, rule/version identification, and an exportable review workpaper;
- a human-review boundary rather than automatic accounting approval.

This is direct observed product behavior, not merely vendor copy. The sample demonstrates that a buyer can obtain a richer exception/review workpaper than the proposed minimal memo with negligible setup on a prepared fixture. No Waterfound implementation was needed to answer the predicate.

**Decision:** `GENERIC_MATCHING_AND_EXCEPTION_MEMO_KILLED / DONE_FOR_YOU_SERVICE_ADVANTAGE_UNPROVEN / NO_PRODUCT_SELECTED`.

The buyer-paid human-service posting remains valid demand evidence for operational work, but it does not establish that Waterfound can deliver lower buyer effort than a free native tool. Any residual value lies outside the tested matching core: collecting statements from email/portals, normalizing PDFs and irregular exports, chasing missing documents, and resolving exceptions. Those steps require confidential customer data, access, accounting review, and human communications; public synthetic matching fixtures cannot prove near-zero-Waterfound fulfillment or WTP.

Do not build a parser, dashboard, OCR pipeline, mailbox collector, ERP connector, or hosted reconciliation service for this hypothesis. Reopen only after an independent buyer signal isolates a specific incumbent failure in intake or exception follow-up and a lawful representative fixture can measure it. Revenue remains USD 0; customer demand and WTP for Waterfound remain unknown.

No upload of private data, account creation, outreach, proposal, spend, payment/KYC, publication, merge, or authority expansion occurred.
