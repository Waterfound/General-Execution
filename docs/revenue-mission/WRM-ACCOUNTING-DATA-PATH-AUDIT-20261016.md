# WRM — independent accounting data-path audit

Observed: 2026-10-16. Status: `TWO_BUYER_BUDGET_SIGNALS / NARROW_JTBD_SELECTED / DIFFERENTIATION_PLAUSIBLE_NOT_PROVEN / NO_PRODUCT_FREEZE`.

This dossier records public commercial evidence and a substitution screen. It is not an accounting opinion, customer validation, authorization to access financial systems, quantified ROI, Waterfound WTP, or revenue.

## Narrow buyer and job

**Potential payer:** partner or operations owner at a small accounting or service firm whose financial workflow crosses an accounting ledger and a practice-management, CRM, expense, or field-service system.

**Job-to-be-done:** independently reconstruct one critical data path from source event through synchronization, review/approval, destination record and exception handling; identify exactly where identity, amount, status, timing or authority stopped corresponding; provide a factual, source-linked control-path report understandable to a non-technical partner.

This is narrower than generic bookkeeping, SOC/compliance consulting, workflow automation, or an audit-log dashboard. It does not correct books, approve transactions, give accounting advice, or write to production systems.

## Repeated paid buyer evidence

1. A current Upwork listing offers **US$500 fixed price** for an independent audit of an accounting firm's QuickBooks/Xero-to-Karbon client-data path. It explicitly asks for failure points, automated actions, human approvals, missing append-only audit trail, and a report a non-technical partner can act on. Source: https://www.upwork.com/freelance-jobs/apply/Independent-audit-our-accounting-firm-client-data-path-QuickBooks-and-Xero-into-Karbon_~022110662478107182421/
2. A separate listing offers **US$300 fixed price** to review QuickBooks Online synchronized with Housecall Pro, identify cross-system inaccuracies and workflow/integration issues, and produce a detailed corrective report. Source: https://www.upwork.com/freelance-jobs/apply/Independent-Accounting-Audit-Review-Specialist-Needed_~022099594910711205369/
3. An independent paid research-call listing seeks real examples of HubSpot-to-QuickBooks failures: identity collisions, duplicate customers/invoices/payments, status or amount discrepancies, manual edits after sync, eventual-consistency timing, authoritative-source uncertainty, detection and repair. This supports the same problem class, but its budget and hire outcome were not verified in this run. Source: https://www.upwork.com/freelance-jobs/apply/HubSpot-QuickBooks-Online-Integration-Expert-Paid-Workflow-Review-Research-Call_~022101042975558391936/

These are buyer-posted scopes, not proof of completed payment, repeat volume, buyer willingness to hire Waterfound, or an autonomously deliverable service.

## Native and adjacent substitution

- QuickBooks Online records account activity, actors and changes in its audit log, including third-party integration actions. Source: https://quickbooks.intuit.com/learn-support/en-us/help-article/audit-log/use-audit-log-quickbooks-online/L2WoVnW6I_US_en_US
- Xero exposes transaction/user history and notes for changes, with filtering/export. Source: https://central.xero.com/0/article/View-a-history-and-notes-summary-for-transactions-and-user-activity
- Karbon markets tracked sign-offs, built-in audit trail, QuickBooks/Xero integrations, sync status, error details and retry for failed invoice syncs. Sources: https://karbonhq.com/solution/bookkeeping/ and https://karbonhq.com/release-notes/jul-31-2025/
- Cross-system finance-automation vendors market approval checkpoints and unified audit trails. Examples: https://clarionops.com/bookkeeping-automation ; https://www.loopfour.com/features ; https://automatic.co/accounting

These capabilities kill generic audit-log collection, exception dashboards, and approval tracking as differentiators. They do not prove that a small firm can reconstruct a disputed event coherently across multiple vendor logs. The repeated paid audit requests are evidence that native visibility may still leave a service job.

## Residual hypothesis

A useful independent audit may join siloed evidence into a single event chain and explicitly classify:

- source record and cross-system identity mapping;
- intended transition versus observed destination state;
- automated actor versus human actor;
- required approval versus observed approval;
- immediate failure versus delayed/eventually consistent state;
- retry, duplication, partial write or manual post-sync edit;
- native evidence present, missing, non-exportable or contradictory;
- bounded next check, without making or authorizing corrections.

The commercial discriminator is **faster, more complete fault localization than separate native-log review**, not creation of another log.

## Evidence ledger

| Predicate | Evidence | State |
| --- | --- | --- |
| Multiple buyers budget for independent cross-system review | US$500 and US$300 fixed-price scopes | Observed, marketplace intent |
| The failure class repeats across different system pairs | Karbon, Housecall Pro and HubSpot paired with QuickBooks/Xero | Observed |
| Native systems preserve useful local audit evidence | Official QuickBooks, Xero and Karbon documentation | Observed |
| Generic logging/approval dashboard is differentiated | Native and adjacent products cover it | Falsified |
| Cross-system factual fault localization is differentiated | No matched parity test | Unknown |
| It reduces reviewer effort or improves finding recall | No representative comparison | Unknown |
| Real customer access can be lawful and least-privilege | No authorization or credentials | Unknown / not attempted |
| External demand or WTP for Waterfound | No contact, proposal, interview or sale | Unknown |
| Revenue | None | USD 0 |

## Kill criteria

Kill this candidate if any one occurs:

1. an incumbent exports a joined source-to-destination event chain with actor, approval, retry and authoritative-value reasoning at negligible setup cost;
2. a truth-labeled two-system fixture shows no decision-relevant finding beyond reading the native logs separately;
3. correct fault localization requires accounting judgments, production writes, private communications or vendor-admin access that cannot remain review-only and low-touch;
4. the workflow cannot be audited without bespoke manual consulting that defeats near-zero Waterfound operation;
5. buyer evidence converges on remediation/bookkeeping rather than the independent diagnostic report.

## Promotion criteria

Promote only if all are met:

1. a lawful synthetic or public two-system fixture contains identity, status, timing, approval and retry receipts with independently fixed ground truth;
2. a minimal read-only proof identifies the planted failure and cites every supporting receipt without guessing missing facts;
3. comparison against separate native views shows one measurable gain in active review minutes, failure recall, provenance coverage or time-to-localization;
4. output remains factual and review-only; no accounting conclusion, credential expansion, writeback or correction;
5. at least one further buyer signal or observable engagement outcome supports the diagnostic report rather than implementation alone.

## Next admissible frontier

Create only the smallest synthetic two-system receipt fixture and an explicit truth set. Test whether a simple event-chain comparator can localize a duplicate, delayed sync, manual post-sync edit and missing approval while distinguishing unknown evidence. Do not build connectors, a dashboard, hosted service, accounting logic, remediation workflow or append-only ledger before that comparison passes.

Customer access, outreach, proposal submission, provider installation, financial onboarding, payment/KYC, public publication and contractual acceptance remain separate authority gates. No private producer activation, scheduler change, spend, merge or canonical-state mutation occurred.
