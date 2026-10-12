# WRM — MSP vendor-side subscription commitment discrepancy: direct substitution screen
Observed: 2026-10-12. Status: BUYER/PROBLEM EVIDENCE + DIRECT SUBSTITUTION; NO PRODUCT PROMOTION, DEMAND, WTP OR ROI.
Owner: WRM Commercial Progress Ratchet. Public-source research only. No customer or private contract files were used.

## Narrow buyer and job
**Potential payer:** owner/finance operator of a small managed service provider (MSP) paying RMM/security vendors.
**Job:** before an RMM vendor invoice or renewal, reconcile the vendor-billed license quantity against the operator's observed active device count **and the applicable signed order-form commitment**; produce a source-cited review question rather than incorrectly calling every billed-minus-used gap an overcharge. This is **vendor-side accounts payable**, distinct from the MSP's **customer-side PSA accounts receivable**.

## Independent first-hand public signals (anecdotes, not validated customers)
1. 2026-06-18, /r/msp: a NinjaRMM operator says billed commitment rose after adding endpoints but did not automatically fall after removals; thread includes distinct replies describing monthly manual adjustment and separate device-class confusion. https://www.reddit.com/r/msp/comments/1u8zk56/warning_ninjarmm_they_wont_autoreduce_your/
2. 2026-09-16, /r/msp: another operator reports approximately 50 more billed devices than current deployment; replies disagree about whether contractual commitments justify this, highlighting the need for signed-terms context. https://www.reddit.com/r/msp/comments/1whx87k/ninjas_billing_isnt_automated/
3. 2026-10-08, /r/msp: a separate Dropsuite customer says they are being asked to move to NinjaOne contract terms/minimums and questions consumption-based billing. https://www.reddit.com/r/msp/comments/1x12kkf/dropsuite_ninja_billing/
4. 2025-11-17, /r/msp: N-able MSP describes the renewal commitment calculation including 80% of excess usage. Different vendor, same general *contract commitment vs observed consumption* failure class. https://www.reddit.com/r/msp/comments/1ozhbke/nable_contract_terms_forced_13_yrs_and_80_annual/
All quantities and experiences above are self-reported and unverified; posters are not confirmed buyers or purchase decision makers.

## Governing vendor source (limits of inference)
- NinjaOne's official MSP pricing FAQ confirms per-device tiered pricing, negotiated promotional commitments, and plan changes through an account manager; public page does **not** establish each customer's signed commitment, exact monthly reduction rights, rates or invoice truth: https://www.ninjaone.com/msp/pricing/
- NinjaOne's official EULA is a general terms source, but specific order forms and amendments may control; **do not** infer refunds or downgrade rights from active count alone: https://www.ninjaone.com/license-agreement/
- Public municipal order form search evidence includes a five-business-day written downgrade notice clause at term expiration and a distinct 60-day termination notice clause, illustrating why actual signed order-form evidence matters. The form is one specific contract, **not** a universal NinjaOne policy: https://ompnetwork.s3-us-west-2.amazonaws.com/sites/1834/documents/meet-packet-7e96b2ac7e9e4016be5fc4be97772cd2.pdf
- N-able official agreement must be checked at the customer's effective version and order form before any renewal forecast; an independent source catalog summarizes 80%-of-excess renewal language but is not controlling legal text: https://wiki.licenseware.io/wiki/n-able-licensing/

## Direct substitution, before any code
- **BillingReconcile** explicitly sells NinjaOne source-count vs PSA billing quantity reconciliation, client mapping and review: https://billingreconcile.com/integrations/ninjaone-billing-reconciliation ; https://billingreconcile.com/ . This covers **customer-side** MSP invoice review; the observed first-party pages do not establish parity on the *vendor's invoice vs signed commitment* job.
- **Rewst Billing Count Report Crate** explicitly collects NinjaOne and other vendor counts and generates scheduled billing reports: https://docs.rewst.help/documentation/crates/existing-crate-documentation/billing-count-report-crate . This weakens any generic multi-vendor count aggregation claim.
- **AllCaps** explicitly markets no-integration contract-to-vendor-invoice auditing, including software-license quantities, tier/renewal terms and minimums. Its illustrative SaaS case uses active seats and contract tiering. The vendor currently advertises a free limited contract scan, $1,500 100-invoice proof audit and subscriptions from $2,000/month: https://www.allcaps.ai/ . **Directly overlaps the exact contract/invoice comparison.** Prices are offers, not proven customer WTP or market size.
- **NinjaOne** itself advertises license management, usage history and billing integration: https://www.ninjaone.com/docs/information-technology-asset-management-itam/managing-software-licenses-renewals/ ; https://www.ninjaone.com/it-asset-management/software-license-billing/ . These are vendor-described capabilities, not an independent vendor-payables parity test.
- **Licenseware** publishes vendor-specific rule/source catalogs for NinjaOne and N-able, making generic vendor-terms extraction an existing substitute: https://wiki.licenseware.io/wiki/ninjaone-licensing/ ; https://wiki.licenseware.io/wiki/n-able-licensing/ .

## Ratchet verdict
- **BUYER PROBLEM:** meaningful independent anecdotal evidence of repeated vendor-billing commitment confusion. Commercial demand and buyer budgets UNKNOWN.
- **KILL generic:** invoice-vs-count alert; RMM device aggregation; no-integration contract/invoice auditing; vendor license-term summarization. These are already advertised by named substitutes.
- **HOLD residual:** a *small-MSP, vendor-specific, contract-aware exception memo* that handles different commitments, temporal snapshots, product-class separation and notice-window uncertainty with demonstrably less cost/friction and equal or better correct decision quality. This is a **hypothesis**, not product scope. AllCaps' free contract scan makes a zero-integration pitch alone insufficient.
- **NO BUILD THIS WAKE:** no representative permitted real vendor invoice/order form/usage triple, independent expert truth set, installed competitor parity, or distribution/WTP evidence. A synthetic classifier would demonstrate capability only, not incremental commercial value; building it now would repeat the instrumentation priority inversion.

## Next bounded independent discriminator
Find a lawful, representative *three-way* source (vendor invoice, governing signed commitment, same-period usage) or a sufficiently detailed public case with authoritative interpretation; independently test whether AllCaps, BillingReconcile, vendor-native reports or a spreadsheet already yield the same **correct next action** at negligible friction. If yes, KILL residual and switch payer/job. If a real unserved exception survives, freeze one rule, create one offline read-only fixture, and test without accessing customer accounts or making financial/legal determinations.

No outreach, releases, credential changes, spending, payment/KYC, private data exposure, new automation, runtime activation or canonical merge. This is commercial falsification evidence, not a UFP mission cold-restart or proof of revenue.
