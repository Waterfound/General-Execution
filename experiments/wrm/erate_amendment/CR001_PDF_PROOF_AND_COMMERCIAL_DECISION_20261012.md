# CR-001 — Exact-source PDF-byte ingestion gate / decisive E-Rate commercial falsification

**Scope:** Standalone candidate child of GE #55, exact base `ae5b63d5e2f8faaf7f82723b926a4e2153b586f2`. No edits to #55/#53/#46 owners, main, canonical registry, scheduler, credentials or commercial surface.

## One genuine engineering improvement

`document_delta.py` implements an **offline parser of complete local PDF bytes** using PyMuPDF. It checks magic bytes, size, PDF structure, text extraction from *every* page (no pretending scanned pages are readable), optionally frozen source SHA-256, document-pair nonidentity, RFP addendum textual ID, and evidence-page hashes with page-local spans.

It classifies a narrowly evidenced **new acknowledgement obligation**, detects expressly conditional rejection language, official timeline precedence and source-labelled response-date changes or incompleteness. It never claims to infer deletions or pricing changes from silence, a legal determination, current bid status, official provenance from a caller-provided URL or commercial superiority. The bid date is **not** evidence of a verified tender submission time when the addendum omits a time.

Run (on lawful input PDFs already available locally):

```sh
python -m pip install pymupdf reportlab
cd experiments/wrm/erate_amendment
python -m unittest -v test_document_delta.py
python document_delta.py /secure/input/original.pdf /secure/input/addendum.pdf \
  --original-url https://www.clevelandmetroschools.org/fs/resource-manager/view/f20ecdb8-5417-4818-9535-ab4fe00bb3e1 \
  --addendum-url https://www.clevelandmetroschools.org/fs/resource-manager/view/6f113102-bfcd-45ec-a056-4fef7da70f40 \
  --original-sha256 ORIGINAL_REAL_SHA256 --addendum-sha256 ADDENDUM_REAL_SHA256 \
  --rfp-id 21372 --observed-on 2026-10-12
```

**Do not run this command with literal placeholder hashes** or claim an official file check from mock PDFs.

## Exact executed tests

- `28/28 PASS` local Python 3.13.5, PyMuPDF 1.26.7; source git blob `d6692b526266414632bc6bff091129340fce7c04`; tests git blob `aa5fa25dcd375a8342821da80490a25443f7851b`. 11 binary input/error tests and 17 semantic/negative tests.
- First run had `26 PASS / 2 FAIL` from a *test-only synthetic PDF writer* splitting words arbitrarily. Replaced arbitrary 88-character splitting by whitespace-aware wrapping, then **28/28 PASS** on same production candidate source. Failures were retained in the receipt rather than silently called source bugs.
- PDF test data are **locally generated synthetic binaries**, exercising an authentic PDF parser. These are NOT the official CMSD PDFs and not genuine customer proof.
- GitHub receipt: `CR001_PDF_BYTE_SOURCE_TEST_RECEIPT_20261012.json`. GitHub native workflow results separately verified by the PR metadata; do not label local 28 tests as CI.

## Official source-bound facts (actual inspection, NOT raw bytes)

Cleveland Metropolitan School District published:
- original RFP #21372, 2-page official PDF: https://www.clevelandmetroschools.org/fs/resource-manager/view/f20ecdb8-5417-4818-9535-ab4fe00bb3e1
- addendum #1, 1-page official PDF: https://www.clevelandmetroschools.org/fs/resource-manager/view/6f113102-bfcd-45ec-a056-4fef7da70f40

Official web-rendered PDF pages were read/visually inspected: the addendum requires acknowledgement of receipt, **states failure may lead to rejection** (not mandatory rejection), establishes timeline priority, and retains Feb 20, 2023 as response due date. The original PDF prints a time, but the addendum timeline lists only a date; **time equivalence cannot be claimed**. Source PDF binary downloads were attempted but failed via container download and DNS. Thus no official binary hashes and no byte-level E2E test: `CR001_REAL_DOCUMENT_DELTA_VERIFIED = FALSE`.

The source website itself directly displays the addendum requirement inside its one-page PDF. We did not measure material effort/time/accuracy improvement for a buyer over directly reading that official page.

## Incumbent substitution was expanded (claims, not execution)

1. [USAC](https://www.usac.org/e-rate/service-providers/step-2-responding-to-bids/) already supplies Form 470 bid documentation, attachments and amendment posting rules.
2. [ERateSignal](https://www.eratesignal.com/) advertises E-Rate public discovery, alerts and scoring (waitlist/advertised prices do **not** prove sales).
3. [ChangeTower](https://changetower.com/solutions/rfp-monitoring/) advertises RFP-page addenda, revised attachments, deadlines and award notices monitoring.
4. [ErateSync](https://www.eratesync.com/erate-compliance) advertises Form470/RFP issue checking and audit/compliance flags.
5. [BidCompliance](https://www.bidcompliance.com/) advertises requirements extraction with citations and a compliance matrix on uploaded bid packs.

No competitor was run against the same CMSD PDFs. Claims of installed feature parity are **NOT_COMPARABLE**, but generic alerting, PDF requirement parsing and compliance matrix are all claimed directly by providers: generic E-Rate document checking is **not** a demonstrated unique Waterfound wedge.

## Forced commercial disposition

**KILL**: generic E-Rate Form470 alerts, bidder addendum notifications, generic PDF compliance matrix, and a standalone acknowledgement/timeline summary as a product. Their differentiators were not demonstrated; expanding a dashboard or app would violate the Commercial Progress Ratchet.

**Retain only a reusable software capability** in this isolated draft (PDF hash validation and fail-closed document evidence), with no E-Rate product promotion.

**Pivot next:** bounded buyer-posted public-record data-quality jobs, beginning with the exact paid acceptance-criteria problem from [permit portal scraper task](https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/) ($30 per accepted jurisdiction, ongoing request). Distinguish software product WTP from a service budget and check strong substitutes and unattended portal availability before any engineering. A broader $22,000 public GIS ingestion job explicitly requires private NDA materials, multiweek full-time work and client-specific infrastructure; it is **poor near-zero-One-Man fit**, not license to build another ETL platform.

**Hard selection gates remain failed:** direct same-source incumbent run, differentiated end-buyer outcome, authenticated official PDF bytes, buyer willingness to use/pay Waterfound, near-zero support, customer acquisition and payment. No credible product selection, no buyer contact, revenue $0.

**Next machine step:** test whether an open legal county-government data service + buyer-accepted public-record reconciliation criterion yields an outcome demonstrably superior to existing scrapers without per-county/manual customization. If not, kill that too and continue commercial search. No accounts, credential changes, scraping against access restrictions, payment or paid compute.

This file is evidence of candidate engineering and a negative commercial decision, **not** a native productive recurrent wake or a launch authorization.
