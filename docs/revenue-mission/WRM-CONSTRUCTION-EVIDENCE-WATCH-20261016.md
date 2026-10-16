# WRM — cross-source construction evidence watch

Observed: 2026-10-16. Status: `GENERIC_WEDGE_KILLED / FORENSIC_RESIDUAL_HOLD / NARROW_CAPABILITY_PROOF_PASS / NO_PRODUCT_FREEZE`.

This is public-source commercial falsification plus a synthetic, read-only probe. It is not customer validation, a legal/forensic opinion, a production monitor, measured ROI, WTP for Waterfound, or revenue.

## Narrow buyer and job

**Potential payer:** owner or project representative on a dispute-sensitive construction project.

**Job:** independently observe a city permit portal and an internal construction document system at fixed intervals; preserve originals; identify every added, removed, renamed, metadata-only, and content-changed file; then provide a factual, source-linked change register without rewriting source systems.

The job is narrower than generic construction document management. The commercial question is whether an independent cross-source evidence service reduces buyer effort or improves evidentiary coverage beyond the tools already present.

## Strongest current buyer evidence

An Upwork listing published 2026-10-12 offers **US$7,500 fixed price** and describes twice-daily monitoring, 12 hours apart, seven days per week. It explicitly requests original downloads from a city permit portal and Procore, detection of additions/removals, file-size changes, status/version/name/header changes, visual overlay for changed plans, a daily summary, and a later factual timeline tied to logged/hashed documents. The listing reports 20–50 proposals, zero interviews when observed, and a client profile showing US$15K total spend and nine hires. These are marketplace observations, not proof that this contract will close, that the full US$7,500 is allocated to the monitoring portion, or that the buyer would buy from Waterfound.

Source: https://www.upwork.com/freelance-jobs/apply/Construction-Document-Controller-Metadata-Analyst-Project-Timeline-and-Report-Builder_~022109542801934675800/

This is stronger buyer evidence than anonymous pain reports because it specifies a budget, cadence, acceptance behavior and operating context. It is still a single buyer posting rather than repeated market demand.

A separately titled `Construction Document Logger & Metadata Specialist` listing contains the same wording and the same client profile; it showed four interviews when observed. Treat it as a split/duplicate procurement by the same buyer, **not** an independent demand signal: https://www.upwork.com/freelance-jobs/apply/Construction-Document-Logger-Metadata-Specialist_~022109541306566726990/

One adjacent, independent listing for a commercial-energy permit expeditor requests ongoing municipal-portal submission/status tracking, documentation and rejection follow-up at **US$15–35/hour for 6+ months**. It showed one hire, three interviews and a client profile with US$12K total spend. This supports recurring paid demand for permit-portal operations, but not for byte-level preservation or cross-source evidence: https://www.upwork.com/freelance-jobs/apply/Permit-Expeditor_~022098407170501687614/

Two further searches found paid downstream evidence work, but not a second independent buyer for the same prospective cross-source watch:

- A U.S. heavy-civil firm seeks a senior construction contracts and claims specialist for an hourly, multi-month engagement. The job requires an event chronology, indexed exhibits, a live claims register, and traceable review-ready work; it showed 10–15 proposals and a client with US$42K prior spend. This validates the value of factual construction chronologies in claims work, not a repeatable demand signal for automated monitoring: https://www.upwork.com/freelance-jobs/apply/Senior-Construction-Contracts-and-Claims-Specialist_~022110119114601588706/
- A construction-litigation paralegal listing requests defect logs, timeline charts, evidence folders and preservation notices in an hourly, 6+ month engagement; it showed fewer than five proposals and a client with US$1.7K prior spend. This is dispute-specific, expert-led legal support and therefore outside the proposed review-only monitoring job: https://www.upwork.com/freelance-jobs/apply/Experienced-Native-Paralegal-Pennsylvania-Construction-Litigation_~022109254961263298512/

These adjacent roles support a downstream need for trustworthy records and chronology. They do not satisfy the promotion criterion of a second buyer requesting substantially the same cross-source monitoring service.

## Direct substitution before build

- Procore Document Management already tracks versions and attribute-change history, including timestamp, actor, field and from/to values. It also compares document versions. Sources: https://www.procore.com/platform/document-management ; https://v2.support.procore.com/product-manuals/document-management-project/tutorials/view-change-history-for-documents-in-the-document-mangement-tool ; https://v2.support.procore.com/product-manuals/document-management-project/tutorials/compare-documents-in-the-document-management-tool/
- Bluebeam Revu already compares PDFs and overlays revised pages. Source: https://support.bluebeam.com/revu/features/compare-documents-vs-overlay-pages.html
- Newforma markets revision management and document audit trails. Sources: https://www.newforma.com/enhancing-risk-management-in-construction-with-document-control/ ; https://www.newforma.com/the-power-of-information-management-reducing-project-delays-in-construction-document-control/
- Permit-management platforms market status tracking, document management and notifications. Source: https://www.permitflow.com/blog/how-does-construction-permit-management-software-work
- PermitFlow's Procore integration is a stronger direct substitute than a stand-alone permit tracker: it brings permit workflow into Procore, tracks status, replaces spreadsheets/document trackers, and adds reminders and follow-ups. It requires a paid PermitFlow subscription and Procore Company Admin, so it is not a parity benchmark for independent evidence preservation, but it substantially covers the operational coordination job. Source: https://www.permitflow.com/blog/permitflow-procore-integration
- Procore separately describes its audit trail as an automatically timestamped chronological record for accountability and disputes. This is a vendor claim rather than an independent evidentiary validation, but it further narrows any residual beyond native auditability. Source: https://www.procore.com/library/construction-audit-trail

Vendor pages are capability claims, not independent parity benchmarks. They are sufficient to **kill generic version history, PDF comparison, overlay, audit trail, permit-status alerting, and cross-system operational coordination as unique features**.

The only residual is forensic rather than operational: a buyer may need a source-external record covering both a municipal portal and Procore, retaining byte-level identity and explicitly separating content changes from timestamp-only changes. One buyer posting suggests that assembling incumbent capabilities can still leave paid manual work, but two further searches did not find a second independent buyer for this exact job. The residual therefore remains on hold and is not a selected product.

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
| Adjacent buyers pay for recurring permit-portal operations | Independent US$15–35/hour listing with one hire | Observed, adjacent only |
| Generic document versioning is differentiated | Procore/Newforma already cover it | Falsified |
| Generic PDF visual comparison is differentiated | Bluebeam and Procore already cover it | Falsified |
| Independent cross-source byte-level register is technically feasible | Synthetic manifest/diff tests | Capability proven narrowly; support-only |
| Cross-system operational coordination is differentiated | PermitFlow integrates permit workflow and status into Procore | Falsified as a generic wedge |
| A second buyer requests substantially the same watch | Two searches found claims/litigation chronology work, not the same prospective watch | Not observed |
| It improves correct decisions or buyer effort vs incumbents | No representative parity test | Unknown |
| It can operate lawfully on a real portal and Procore account | No project identifier, credentials, terms review or authorization | Unknown / not attempted |
| External demand or WTP for Waterfound | No contact, proposal, interview or sale | Unknown |
| Revenue | None | USD 0 |

## Kill and promotion criteria

**Kill the residual** if any one of these occurs:

1. a permitted incumbent configuration exports the same cross-source, source-preserving register with comparable setup and review effort;
2. a representative public/synthetic two-source fixture yields no action beyond native version history and ordinary Bluebeam comparison;
3. lawful acquisition requires brittle browser automation, credential sharing, prohibited scraping, or sustained human checking that prevents low-touch delivery;
4. two further buyer searches show only one-off forensic disputes rather than recurring monitoring demand. **Triggered on 2026-10-16 for the generic/prospective wedge.**

**Promote to one candidate service proof only if:**

1. at least one additional independent buyer signal requests substantially the same cross-source evidence job;
2. a lawful representative two-source fixture can be truth-labeled;
3. the proof demonstrates one measurable improvement: lower observable active minutes, higher change recall, clearer provenance coverage, or faster terminal report generation than the native combination;
4. the output remains review-only and does not make legal, engineering or contractual determinations.

## Next admissible frontier

Close the generic construction-document watch as an active candidate. Preserve the small manifest proof as support-only and do not extend it. The forensic residual may be reopened only if an independent buyer explicitly requests source-external byte preservation across permit and project systems, after which a lawful two-source parity fixture must demonstrate measurable advantage over PermitFlow + Procore + Bluebeam before any connector or service build.

The next commercial-discovery cycle should select a different buyer/problem wedge with stronger repeated demand and weaker native substitution. Private portal access, Procore installation, customer contact, proposal submission, contract acceptance and publication remain separate authority gates; none is needed to close this candidate.

No private producer activation, scheduler change, merge, paid account, outreach, spend, payment/KYC or canonical-state mutation occurred.
