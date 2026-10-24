# WRM — independent accounting data-path audit

Observed: 2026-10-16. Status: `CANDIDATE_KILLED / SERVICE_DEMAND_OBSERVED / AUTONOMOUS_LOW_TOUCH_DELIVERY_NOT_FEASIBLE / NO_PRODUCT_SELECTED`.

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


## Synthetic capability proof result

A minimal read-only comparator was tested against an independently fixed synthetic truth set containing:

- duplicate destination creation;
- a 45-minute delayed synchronization against a 15-minute bound;
- destination creation without the required approval evidence;
- a human edit after the initial synchronized create;
- an orphan destination record with no valid source-event correlation.

Result: **5/5 planted conditions detected (100% fixture recall)** and all 11 relevant receipt identifiers cited across the findings. The comparator emits `UNCORRELATED_DESTINATION` rather than guessing a source for the orphan record. The first test run failed only because the test incorrectly expected five unique evidence identifiers; the assertion was repaired to verify the exact 11-receipt provenance set, after which the test passed.

This is a narrow capability proof only. It does not establish real-system field availability, completeness of QuickBooks/Xero/Karbon exports, correct accounting interpretation, buyer active minutes saved, superiority over manual native-log review, production reliability, demand for Waterfound, or WTP.

Updated state: `TWO_BUYER_BUDGET_SIGNALS / SYNTHETIC_CAPABILITY_PROOF_PASS / REAL_PARITY_UNKNOWN / NO_PRODUCT_FREEZE`.

The next admissible commercial discriminator is a representative parity case using lawful exported schemas or public sample logs. No connector, dashboard or hosted service is justified until the same fault can be compared against separate native views and one measurable gain is observed.


## Real-source feasibility screen and decision

Official documentation was checked on 2026-10-16 before any connector or additional implementation:

| System | Read path actually available | Constraint relevant to the job |
| --- | --- | --- |
| QuickBooks Online | The native audit log records actors and changes, including third-party integration actions. | Intuit requires an active subscription and **admin access**; the UI shows 150 records at a time. Intuit's documented bulk export covers reports, lists and posting transactions, not the audit log. A view-reports role explicitly cannot access the audit log. Sources: https://quickbooks.intuit.com/learn-support/en-us/help-article/audit-log/use-audit-log-quickbooks-online/L2WoVnW6I_US_en_US ; https://quickbooks.intuit.com/learn-support/en-us/help-article/list-management/export-reports-lists-data-quickbooks-online/L1xleDrLp_US_en_US ; https://quickbooks.intuit.com/learn-support/en-us/help-article/access-permissions/user-roles-access-rights-quickbooks-online/L66POfRrI_US_en_US |
| Xero | The History and Notes report can be filtered and exported; the Accounting API can retrieve history for one existing document. | A cross-system review must first resolve each document, then retrieve its local history. Xero decommissioned the broader Accounting Activities API (including user activities) on 2026-05-04. Sources: https://central.xero.com/0/article/View-a-history-and-notes-summary-for-transactions-and-user-activity ; https://developer.xero.com/documentation/api/accounting/historyandnotes ; https://developer.xero.com/changelog |
| Karbon | Public API resources expose record identifiers, timestamps and supported external keys. | API authentication is **account-level**, requires an API application token plus access key, and is not scoped to an individual user. API actions are not attributed to a specific Karbon user. Private/hidden clients are excluded unless an administrator separately requests access. External keys are not guaranteed unique across connected systems. Sources: https://developers.karbonhq.com/guides/authentication/ ; https://developers.karbonhq.com/release-notes/2026-04-22/ |

### Falsification result

The synthetic comparator proves only that already-normalized receipts can be joined correctly. It does not solve the commercially decisive acquisition problem. For the exact paid buyer path, a complete, attributable chain cannot be assembled by a least-privilege reviewer from documented machine-readable exports alone:

- QuickBooks actor/change evidence requires admin UI access and has no documented audit-log bulk export in the official export guide;
- Xero history is exportable but API history is document-scoped, while the broader user-activity API has been retired;
- Karbon access is account-wide and some records require additional administrator action; the API cannot itself attribute API actions to a human user;
- therefore evidence collection becomes credentialed, system-specific and substantially manual before the comparator adds value.

This hits kill criterion 3 (vendor-admin access cannot remain least-privilege and low-touch) and kill criterion 4 (bespoke manual consulting dominates the workflow). The paid listings remain valid evidence for a human-delivered independent audit service, but not for an autonomous near-zero-operation Waterfound product under the current authority envelope.

Decision: **kill the accounting data-path audit candidate**. Preserve the synthetic comparator as capability evidence only; do not build connectors, normalize additional schemas, install provider access, request credentials, package a dashboard, submit a proposal or claim ROI.

No customer demand for Waterfound, willingness to try, WTP, time saving, accounting correctness or revenue was established. Revenue remains **USD 0**. The mission returns to commercial discovery with no product selected.
