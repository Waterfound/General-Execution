# WRM — Supplier PO commitment drift: buyer/job and direct-substitution kill test (2026-10-12)

**State:** RESEARCH / NEW PAYER-JOB SCREEN / GENERIC WEDGE REJECTED / NO PRODUCT SELECTED.  
**Selector:** WRM-CPR-001, buyer/problem evidence -> direct substitution.  
**Authority:** public-source research only; no outreach, customer data, new accounts, installation, release, merge, spend or runtime mutation.

## Exact hypothesis
Potential payer: purchasing lead of a small/mid-size manufacturer managing supplier purchase-order commitments through email and an existing ERP.
Job: detect when a supplier's promised delivery date, price, quantity or acknowledgment changes after an issued PO, with the original supplier response and a reviewable exception, without moving to a new ERP.

## Independent first-hand public pain (self-reported, unverified)
1. 2026-01-17: an oil-and-gas supply-chain intern reports that auto-issued POs often lack proactive supplier confirmations, making ERP delivery dates stale; proposes Outlook/SharePoint/Power Automate follow-up. Source: https://www.reddit.com/r/supplychain/comments/1qfguio/supply_chain_intern_here_would_this_po/
2. 2026-02-25: a self-described buyer at a mid-size manufacturer reports repeated supplier date changes after confirmation, pricing shifts, planner follow-up and ERP truth lagging reality. Source: https://www.reddit.com/r/supplychain/comments/1re436e/anyone_else_tired_of_constantly_chasing_suppliers/
3. 2025-05-22: a lone purchasing worker asks how to handle suppliers not acknowledging emailed POs and when to request ETA. Source: https://www.reddit.com/r/procurement/comments/1ksm3mi
These are separate anecdotes consistent with a repeated failure class; identity, buyer budget, prevalence, ROI and WTP are unknown. The first is an idea question rather than a buyer asking to purchase.

## Direct first-party substitutes found BEFORE code
- ConfirmPO: no-login supplier confirmation, per-line date/price/quantity exceptions, automatic follow-ups, CSV/XLSX and PDF/email inputs, free tier and advertised $19/$49 monthly plans. https://confirmpo.zbackroom.com/
- OrderDiff: no-ERP-upload PO-versus-supplier-confirmation comparison, ranked price/date/quantity deltas, uncertainty disclosure; free manual comparison, automation described as future. https://www.orderdiff.com/
- ERPlisity: no-login acknowledgment link, changed lines and dates, EDI and verified ERP write-back. https://erplisity.com/po-acknowledgment-automation
- Flowbit AI: inbound supplier confirmations compared line-by-line to POs for date, price and quantity changes. https://www.flowbitai.com/en/solutions/order-confirmation-processing
- SourceDay: supplier acknowledgment reminders, PO change handling and ERP synchronization. https://sourceday.com/automation/
- Pacteva: source/proposal/decision/commitment history and accountless supplier response; vendor page reports development status, not verified availability. https://pacteva.com/
These are vendor descriptions, not installed parity tests or independently verified paying customers. Listed prices are offers, NOT measured willingness to pay.

## Decision / information gain
**KILL_AS_UNIQUE_DIFFERENTIATOR:** basic PO acknowledgment chasing; accountless supplier links; line-by-line price/quantity/date discrepancy detection; no-ERP file upload; generic supplier commitment history. Direct substitutes explicitly advertise all of these, including low-cost small-team offers. No reason to create a new PO dashboard, confirmation engine, connector or hosted service.

**RESIDUAL HYPOTHESIS ONLY:** an independently evidenced, costly exception requiring a correct action that these specific substitutes do not already advertise, with accessible lawful inputs and a buyer who demonstrably values the incremental result. Nothing identified here satisfies that threshold. No product scope frozen.

## Cross-candidate adverse update
- Construction late-addendum scope: Provision explicitly advertises addendum-inclusive scope packages and cross-document citations (https://provision.com/blog/addendum-tracking-bid-day-scope-misses), further weakening generic uniqueness. Installed parity for exact trade-specific delta remains untested.
- MSP vendor-commitment invoice: AllCaps explicitly audits contracts and invoices for vendor-side license quantities and commercial terms (https://www.allcaps.ai/), and separately advertises usage-entitlement-invoice reconciliation on the customer-billing side (https://www.allcaps.ai/unbilled-usage-recovery). This weakens generic three-way matching as a distinctive claim but does NOT prove AllCaps covers the exact vendor-side MSP order-form/usage edge case. That residual remains HOLD, not a verified kill.

## Next machine-admissible commercial action
Stop broad feature-idea generation for these directly substituted jobs. Identify a single *specific exception* in a buyer's first-hand public account, document the buyer's actual attempted workaround and its failure, then compare the exact exception against specialist products' first-party contracts before any code. If no incremental action can be demonstrated from legally accessible representative data, reject the exception. Keep selection open across vertical automation and specialized intelligence; no invented demand or ROI.

## Evidence accounting
New public first-hand accounts reviewed: 3; directly relevant product offerings identified: 6; new implementation scope: 0; generic wedge killed: 1. Customer interviews, paid demand, WTP, product superiority and revenue: NONE. This research artifact is a commercial falsification result, NOT a UFP mission-specific cold restart or native Durable execution receipt.
