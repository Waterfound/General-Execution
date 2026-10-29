# WRM Apify Public Recall Feed Channel Screen — 2026-10-26

## Decision

`BUYER_PROBLEM_CONFIRMED / ADJACENT_WTP_CONFIRMED / OFFICIAL_DATA_AVAILABLE / EXACT_MARKETPLACE_DENSELY_OCCUPIED / OBSERVED_MARKETPLACE_DEMAND_WEAK / NO_BUILD / ROUTE_CLOSED`

Close the public governmental product-recall feed route on Apify. Do not build another CPSC, Safety Gate, FDA, NHTSA, USDA, or cross-source recall Actor unless independent evidence later shows paid usage for a materially different job.

This closes only this route. It does not assert that product-safety work, inventory matching, Shopify-native workflows, or Apify as a whole lack value.

## Narrow job tested

> Give technical buyers a paid, normalized, source-linked feed of official product recalls, optionally matched to brands, GTINs, or a catalogue, without requiring private credentials.

Target buyers: marketplace integrators, e-commerce operators, compliance teams, and AI-agent builders.

## Buyer/problem evidence

The underlying job is real:

- CPSC exposes machine-readable recall data through a public REST interface.
- CPSC documents fields including recall number, company, product type and description, hazard, date, and UPC when supplied.
- Seller discussion identifies the hard part as joining inconsistent recall notices to large inventories, not merely downloading notices.
- Commercial products including recallsapi.com and Shopify recall-monitoring apps sell catalogue matching and alert workflows.

This proves a problem and adjacent commercial activity. It does not prove demand for a new Apify Actor.

## Substitute and channel evidence

The exact marketplace route is already dense:

- `retrainmap/cpsc-recalls` — direct CPSC search Actor.
- `whitel1ght/unified-product-recalls` — five official sources in one schema, monitoring mode, priced at USD 5 per 1,000 recalls.
- `kittiwake/eu-recall-watchlist` — Safety Gate normalization plus GTIN/brand watchlist, priced from USD 1.40 per 1,000 alerts.
- `nightwave-owner/product-recalls-monitor` — CPSC, FDA, and Safety Gate in one format.
- Additional direct substitutes cover CPSC, Safety Gate, NHTSA, multi-source normalization, watchlists, schedules, webhooks, MCP, and pay-per-result pricing.

Direct observed usage is weak:

- `whitel1ght/unified-product-recalls`: 2 total users, 1 monthly active user, 0 ratings.
- `kittiwake/eu-recall-watchlist`: 1 total user, 1 monthly active user, 0 ratings.
- `retrainmap/cpsc-recalls`: 1 total user in the indexed marketplace page.

These counts are marketplace-displayed observations, not revenue, retention, or willingness-to-pay. The monthly active user may be the developer or a free user.

## Differentiation test

A candidate would need to beat existing Actors on a customer outcome rather than source count or schema polish. The apparent residual—accurate catalogue matching despite missing UPC/GTIN, inconsistent brand names, model ranges, and free text—cannot be proven safely from public notices alone. Fuzzy matches introduce false positives and false negatives in a safety-sensitive workflow; human confirmation against the official notice remains necessary.

Cross-source normalization, monitoring, only-new delivery, brand/GTIN watchlists, webhooks, MCP access, and source links are already present. More of the same is not a defensible wedge.

## Capability versus outcomes

### Capability established

- Official public sources are machine-readable.
- A read-only normalizer or monitor is technically feasible.
- The route avoids personal data and can preserve source attribution.

### Outcomes not established

- No customer outcome has been observed.
- No paid Apify use has been observed.
- No recall prevented, listing removed, operator-minute saved, or matching accuracy measured.
- No willingness-to-pay for Waterfound's version exists.
- Revenue remains USD 0.

## Kill criteria applied

The route is killed because all three conditions hold:

1. At least three exact or stronger marketplace substitutes already expose the same core job.
2. Direct comparable listings show only 1 monthly active user and no ratings.
3. The only meaningful residual requires safety-sensitive catalogue matching that public source records cannot reliably automate without private catalogue data and human verification.

## Reactivation criteria

Reopen only if one of the following becomes true:

- a buyer supplies an authorized representative catalogue and agrees to measure precision, recall, handling time, and verified actions;
- a marketplace comparable shows sustained paid adoption rather than listing presence;
- a source begins publishing stable product identifiers sufficient for deterministic matching; or
- a narrower jurisdiction/category demonstrates a non-substituted buyer job with verified WTP.

## Sources observed 2026-10-26

- CPSC Recalls API: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
- SaferProducts API FAQ: https://www.saferproducts.gov/FAQs/FrequentlyAskedQuestions11
- Unified Product Recalls Actor: https://apify.com/whitel1ght/unified-product-recalls
- EU Safety Gate watchlist Actor: https://apify.com/kittiwake/eu-recall-watchlist
- CPSC recalls Actor: https://apify.com/retrainmap/cpsc-recalls
- Multi-source recalls monitor: https://apify.com/nightwave-owner/product-recalls-monitor
- Commercial seller workflow: https://recallsapi.com/sellers

## Governance

No Actor, account, paid plan, schedule, scrape, catalogue upload, outreach, publication, credential, contract, payment, claim, or Privacy P0 action was created. This was read-only commercial discovery. Further instrumentation is SUPPORT_ONLY and is not admitted.
