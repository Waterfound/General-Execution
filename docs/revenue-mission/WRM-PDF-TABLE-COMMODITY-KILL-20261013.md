# WRM — PDF table to spreadsheet: paid-demand proof, executable fixture, and commodity kill

Date: 2026-10-13. Candidate-only commercial discovery; no customer contact, application, account, spend, publication, payment, Work, runtime change or merge.

## Narrow job tested

Convert one public, text-extractable statistical table PDF into a typed CSV and fail closed when a numeric value or column is corrupted. This is deliberately narrower than generic PDF/OCR automation.

Public fixture: San Jose State University, one-page Student's t table, 36 data rows and 11 cumulative-probability values per row: https://www.sjsu.edu/faculty/gerstman/StatPrimer/t-table.pdf . The PDF page is publicly readable and contains the table text. The local fixture here is a transcription of those values, not a byte-authenticated download of the PDF.

## Observed paid demand — not Waterfound demand or WTP

- A September 4 Upwork job offers USD35 fixed price for PDF-to-Excel entry, shows 50+ proposals and one hire: https://www.upwork.com/freelance-jobs/apply/PDF-Excel-Data-Entry_~022095949479616948136/ .
- A September 27 job offers USD30 fixed price for PDF/CSV-to-Excel extraction and shows 20–50 proposals: https://www.upwork.com/freelance-jobs/apply/PDF-Data-Extraction-Excel-Formatting-Specialist_~022104259968985860661/ .
- A scanned-PDF-to-Excel job offers USD25 fixed price, requires accuracy checking, and shows 50+ proposals: https://www.upwork.com/freelance-jobs/apply/PDF-Images-Excel-Data-Entry-Specialist-Needed_~022102351031557384122/ .

These listings prove current buyer-posted budgets for the broad job. They do not prove Waterfound eligibility, accessible source files, acceptance, repeat volume, margin, demand for mathematical validation, or willingness to pay Waterfound.

## Direct substitutes

- An Upwork catalog seller offers 20 pages for USD35, 300 for USD110 and 2,000 for USD280, with sample confirmation and values checked against totals: https://www.upwork.com/services/product/development-it-data-extracted-from-pdfs-and-documents-into-a-clean-excel-spreadsheet-2108131833911738066 .
- Another offers 20 pages for USD35, 100 for USD80 and 400 for USD160, including OCR, row/total validation and the Python script on larger jobs: https://www.upwork.com/services/product/development-it-pdf-or-scanned-document-data-extracted-into-a-clean-excel-or-csv-file-2102974000603931521 .
- A Top Rated seller reports 7,100+ hours, 150+ jobs and 100% Job Success, with sample approval and blank/duplicate/format checks; tiers are USD20/3 hours, USD50/8 hours and USD120/20 hours: https://www.upwork.com/services/product/admin-customer-support-accurate-pdf-to-excel-or-google-sheets-data-entry-and-data-cleaning-2102452164704558675 .

These are seller claims, not independent same-input acceptance tests. They nevertheless establish strong incumbent supply and defeat a generic claim that validation, OCR, sample review or a reusable script is unique.

## Executed proof

Files: `experiments/wrm/pdf_table/wrm_pdf_table_probe.py` and `test_wrm_pdf_table_probe.py`.

Local Python 3.13.5 execution with SciPy checked all 396 transcribed numeric cells against the Student's t or normal quantile function at the source's printed precision. Result: 36 rows, 12 schema columns, 396/396 within printed rounding tolerance. Three unit tests passed: complete fixture, numeric corruption fails closed, and missing-column corruption fails closed. Source SHA-256 `57b7aa6fe8217fbafff2d24298a69050135fb026990990ce47c310e34d4fa02d`; test SHA-256 `b298f8f141a7fdfbbc2160452a3844d22ca6cea027f7f4082198447799e69236`.

This proves only a deterministic validation technique for one easy, text-extractable, formula-backed fixture. It does not prove PDF byte ingestion, OCR, layout detection, arbitrary-table validation, customer acceptance, operator time saved, lower errors than incumbents, or revenue.

## Commercial disposition

**KILL `generic PDF to Excel with validation` as a unique first product.** Two direct sellers already advertise the same core outcome at USD35 for 20 pages, one includes a reusable Python script, and the buyer listings are highly competitive. The completed proof does not establish a defensible advantage.

**HOLD `formula-verifiable scientific/regulatory table conversion` as a research hypothesis only.** It survives solely as a possible sharper job because semantic recomputation can detect plausible-looking numeric errors that row counts and totals cannot. No paid listing here asks for that discriminator, and no incumbent same-input output was obtained.

Kill the sharper hypothesis if any of the following occurs:

1. Two established substitutes correctly convert and independently validate the same three representative formula-backed documents at comparable friction and price.
2. Three fresh paid specifications fail to require semantic numeric validation or reject its incremental value.
3. The method cannot handle one scan and one multi-page/broken-table fixture without manual reconstruction that destroys viable unit economics.

Promote only after all are observed: three lawful representative inputs, same-input competitor comparison, independently checkable acceptance criteria, and real willingness-to-try or WTP. Until then: capability proven narrowly; observed customer outcome, differentiation, demand for the discriminator, WTP and revenue all unverified.

## Follow-up direct-demand screen — final disposition

A fresh primary-market search on 2026-10-13 tested whether buyers specifically request semantic or formula-level validation, rather than ordinary row/count/total checking.

- A current USD100 clinical CRF entry and quality-check job requires scanned-form transcription, source consistency, missing/out-of-range query logs and GCP/ALCOA+ experience. It demonstrates a real validation job, but the value is domain-governed human judgment and private supplied records, not autonomous formula-backed PDF conversion: https://www.upwork.com/freelance-jobs/apply/Clinical-Data-Entry-Quality-Check-identified-CRF-Data_~022107198975369803005/ .
- A current USD30–60/hour Document AI engineering job requires an existing private parsing system, representative private documents, complex layouts, merged cells, glyphs, diagrams, routing and measurable quality. It validates demand for custom engineering, not a standalone table checker: https://www.upwork.com/freelance-jobs/apply/PDF-Parsing-Document-Expert-Needed-Improve-Existing-System_~022094873425753987085/ .
- A statistical-validation engagement requires a PhD biostatistician, actual private records and a signed professional opinion. This is explicitly unsuitable for near-zero-human autonomous fulfillment and cannot be substituted by the probe: https://www.upwork.com/freelance-jobs/apply/Biostatistician-Independent-Statistical-Validation-Opinion-Needed_~022108084675655563802/ .
- A competing catalog pipeline already advertises source IDs, typed fields, validation rules, a dead-letter table, run reports and a USD1,200–7,500 price range. This is seller positioning rather than verified sales, but it removes any plausible claim that provenance plus exception routing is unique: https://www.upwork.com/services/product/development-it-clean-database-rows-from-your-pdfs-and-messy-excel-files-2102641762813535040 .

The search found no direct paid specification for formula-recomputed PDF tables. Therefore criterion 2 is satisfied in the bounded screen: paid specifications either request ordinary extraction/validation or domain expertise and private evidence, not the candidate discriminator.

**FINAL KILL as first product:** `formula-verifiable scientific/regulatory PDF table conversion`. Preserve the executed probe as reusable capability only. Do not add OCR, layout routing, more fixtures or product infrastructure around it. Re-open only on independent direct buyer evidence requesting the semantic discriminator with lawful representative input and machine-verifiable acceptance.
