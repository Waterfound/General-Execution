# WRM — cross-source construction evidence watch

Observed: 2026-10-16. Status: `BUYER_BUDGET_SIGNAL / NARROW_CAPABILITY_PROOF_PASS / DIFFERENTIATION_UNPROVEN / NO_PRODUCT_FREEZE`.

This is public-source commercial falsification plus a synthetic, read-only probe. It is not customer validation, a legal/forensic opinion, a production monitor, measured ROI, WTP for Waterfound, or revenue.

## Narrow buyer and job

**Potential payer:** owner or project representative on a dispute-sensitive construction project.

**Job:** independently observe a city permit portal and an internal construction document system at fixed intervals; preserve originals; identify every added, removed, renamed, metadata-only, and content-changed file; then provide a factual, source-linked change register without rewriting source systems.

The job is narrower than generic construction document management. The commercial question is whether an independent cross-source evidence service reduces buyer effort or improves evidentiary coverage beyond the tools already present.

## Strongest current buyer evidence

An Upwork listing published 2026-10-12 offers **US$7,500 fixed price** and describes twice-daily monitoring, 12 hours apart, seven days per week. It explicitly requests original downloads from a city permit portal and Procore, detection of additions/removals, file-size changes, status/version/name/header changes, visual overlay for changed plans, a daily summary, and a later factual timeline tied to logged/hashed documents. The listing reports 20–50 proposals, zero interviews when observed, and a client profile showing US$15K total spend and nine hires. These are marketplace observations, not proof that this contract will close, that the full US$7,500 is allocated to the monitoring portion, or that the buyer would buy from Waterfound.

Source: https://www.upwork.com/freelance-jobs/apply/Construction-Document-Controller-Metadata-Analyst-Project-Timeline-and-Report-Builder_~022109542801934675800/

This is stronger buyer evidence than anonymous pain reports because it specifies a budget, cadence, acceptance behavior and operating context. It is still a single buyer posting rather than repeated market demand.

## Direct substitution before build

- Procore Document Management already tracks versions and attribute-change history, including timestamp, actor, field and from/to values. It also compares document versions. Sources: https://www.procore.com/platform/document-management ; https://v2.support.procore.com/product-manuals/document-management-project/tutorials/view-change-history-for-documents-in-the-document-mangement-tool ; https://v2.support.procore.com/product-manuals/document-management-project/tutorials/compare-documents-in-the-document-management-tool/
- Bluebeam Revu already compares PDFs and overlays revised pages. Source: https://support.bluebeam.com/revu/features/compare-documents-vs-overlay-pages.html
- Newforma markets revision management and document audit trails. Sources: https://www.newforma.com/enhancing-risk-management-in-construction-with-document-control/ ; https://www.newforma.com/the-power-of-information-management-reducing-project-delays-in-construction-document-control/
- Permit-management platforms market status tracking, document management and notifications. Source: https://www.permitflow.com/blog/how-does-construction-permit-management-software-work

Vendor pages are capability claims, not independent parity benchmarks. They are sufficient to **kill generic version history, PDF comparison, overlay, audit trail and permit-status alerting as unique features**.

The only residual is the independent, cross-source observation boundary: a buyer may need a source-external record covering both a municipal portal and Procore, retaining byte-level identity and explicitly separating content changes from timestamp-only changes. The listing itself suggests that assembling those incumbent capabilities still leaves paid operational work. That is an inference from one posting, not proof of a market gap.

## Smallest falsifiable capability proof

`construction_evidence_snapshot.py` creates a read-only manifest containing relative path, byte size, modification timestamp and SHA-256 for every file. Comparing two manifests reports:

- added and removed paths;
- a one-to-one rename when content hash is identical;
- changed bytes even when file size is unchanged;
- timestamp-only changes separately from content changes;
- ambiguity rather than guessing when duplicate hashes prevent a unique rename mapping.

The probe never edits source files. Three deterministic tests pass on a synthetic fixture. This establishes only that a minimal independent manifest can preserve and classify file-level evidence. It does **not** establish portal acquisition, Procore integration, PDF signature verification, visual plan-delta interpretation, legal chain of custody, operational reliability, buyer effort saved, or advantage over an operator using Procore plus Bluebeam.

## Evidence ledger

| Predicate | Evidence | State |
| --- | --- | --- |
| A buyer specified the exact job and a budget | Public US$7,500 listing; client spend/hire history | Observed, single-buyer |
| Generic document versioning is differentiated | Procore/Newforma already cover it | Falsified |
| Generic PDF visual comparison is differentiated | Bluebeam and Procore already cover it | Falsified |
| Independent cross-source byte-level register is technically feasible | Synthetic manifest/diff tests | Capability proven narrowly |
| It improves correct decisions or buyer effort vs incumbents | No representative parity test | Unknown |
| It can operate lawfully on a real portal and Procore account | No project identifier, credentials, terms review or authorization | Unknown / not attempted |
| External demand or WTP for Waterfound | No contact, proposal, interview or sale | Unknown |
| Revenue | None | USD 0 |

## Kill and promotion criteria

**Kill the residual** if any one of these occurs:

1. a permitted incumbent configuration exports the same cross-source, source-preserving register with comparable setup and review effort;
2. a representative public/synthetic two-source fixture yields no action beyond native version history and ordinary Bluebeam comparison;
3. lawful acquisition requires brittle browser automation, credential sharing, prohibited scraping, or sustained human checking that prevents low-touch delivery;
4. two further buyer searches show only one-off forensic disputes rather than recurring monitoring demand.

**Promote to one candidate service proof only if:**

1. at least one additional independent buyer signal requests substantially the same cross-source evidence job;
2. a lawful representative two-source fixture can be truth-labeled;
3. the proof demonstrates one measurable improvement: lower observable active minutes, higher change recall, clearer provenance coverage, or faster terminal report generation than the native combination;
4. the output remains review-only and does not make legal, engineering or contractual determinations.

## Next admissible frontier

Search for a second buyer signal and a lawful public two-source fixture. Do not add a dashboard, scheduler, portal scraper, Procore connector, PDF renderer, hosted service or cryptographic ledger before those predicates are met. Private portal access, Procore installation, customer contact, proposal submission, contract acceptance and publication remain separate authority gates; they are not current blockers to continued public research.

No private producer activation, scheduler change, merge, paid account, outreach, spend, payment/KYC or canonical-state mutation occurred.
