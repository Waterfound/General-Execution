# WRM — Print PDF Preflight Buyer Screen — 2026-10-28

Status: **REPEATED_BUYER_DEMAND / DIRECT_FREE_SUBSTITUTES / SPECIALIST_FIXUP_VALUE / NO_BUILD / DISCOVERY_ACTIVE**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound sell a global, self-serve website that accepts a print PDF and returns a deterministic preflight report for fonts, page boxes, bleed, color spaces, image resolution and PDF/X—without privileged accounts, proprietary desktop software, unsafe file rewriting or recurring human operation?

This candidate passed the first discovery filter: more than one independent buyer asks for the same acceptance artifact. It was therefore screened against exact substitutes before any proof or website work.

## Repeated buyer evidence

### 1. Missing-font repair plus preflight report

A Freelancer project offered **EUR 30–250** to repair a 16-page brochure rejected by a print shop because fonts were not embedded. The deliverables were a print-ready PDF, preferably PDF/X-4, and a brief preflight report. The listing showed **106 proposals** and an average displayed bid of **EUR 79**.

Source: https://www.my.freelancer.com/projects/adobe-acrobat/embed-missing-pdf-fonts-urgent

### 2. Print and digital book PDFs plus preflight report

A separate open Freelancer project offered **USD 30–250** for three professional PDFs: a CMYK print file with bleed, crop marks and embedded fonts; an optimized RGB screen file; and an interactive PDF with links and bookmarks. The buyer explicitly required a preflight report and the export settings.

Source: https://www.freelancer.com/projects/adobe-acrobat/pdf-libro-para-impresi-digital

### 3. Packaged InDesign verification

Another fixed-price scope requested packaged INDD/IDML verification, font and link resolution, editability, facing-page geometry, overset checks, PDF export, visual-reference parity and a pass/fail report with screenshots.

Source: https://www.freelancer.com/jobs/custom-project-apr.4409039/77

These listings establish repeated demand for the **final print-ready file plus evidence**. They do not prove demand for a standalone automated checker.

## Exact free substitutes

The diagnostic layer is already directly occupied:

- **Hypermatic** runs locally in the browser with no signup and reports MediaBox, CropBox, TrimBox, BleedBox, page-size consistency, font embedding, RGB/CMYK signals, encryption and PDF/X metadata.
  - https://www.hypermatic.com/tools/pdf-print-preflight-checker/
- **Preflighter.app** offers free browser preflight for bleed, image resolution, fonts, color space, output intent, separations, overprint, total ink coverage, RGB objects, PDF boxes and PDF/X.
  - https://preflighter.app/
- **PDFLean** runs locally, checks 12 prepress families and provides a downloadable report; it also advertises one-click fixes for common issues.
  - https://pdflean.com/tools/pdf-preflight
- **BANCO** runs offline in Web Workers and reports bleed, resolution, color spaces, fonts, overprint and font-license signals.
  - https://bancoscan.app/pdf-font-embedding-checker
- **BoxCheck** provides a free PDF/AI check for bleed, safe zone, CMYK, resolution, fonts and ink coverage, with job-type presets.
  - https://boxcheck.org/en

A Waterfound browser scanner would duplicate these products without an observed decision advantage.

## Professional correction substitutes

The paid value in the buyer scopes is not merely detection. It is controlled correction and responsibility for a printer-specific result.

- Adobe Acrobat Pro Preflight provides predefined and custom fixups for color conversion, PDF repair, optimization, version conversion, hairlines, transparency flattening, removal outside trim/bleed boxes and preparation for PDF/X, PDF/E and PDF/A.
  - https://helpx.adobe.com/acrobat/using/correcting-problem-areas-preflight-tool.html
- callas pdfToolbox supports variable preflight profiles, ISO/Ghent Workgroup standards, accurate print preview, fixes and REST automation.
  - https://callassoftware.com/products/pdftoolbox/
  - https://help.callassoftware.com/m/pdftoolbox/l/2097756-pdftoolbox-rest-api-operations

Published reseller pricing lists pdfToolbox Desktop at **EUR 375/year or EUR 625 perpetual**, and Server/CLI/SDK at **EUR 3,000/year or EUR 5,000 perpetual**. This proves professional spending on production tooling, not an opening for a generic checker.

Source: https://impressed.de/produkte/callas/pdftoolbox-desktop/technische-daten/

## Truth and safety boundary

Automatic font embedding is not a universal safe fix:

1. the required font program may not be present in the PDF or available to Waterfound;
2. font licenses may prohibit embedding or redistribution;
3. outlining text changes editability, searchability and accessibility;
4. color conversion depends on the intended press, stock, output intent and ICC profile;
5. bleed cannot be truthfully synthesized when source artwork does not extend past trim;
6. low-resolution images cannot be restored to original production quality by a deterministic fix;
7. printer-specific profiles remain the final acceptance authority;
8. permanent fixups can change visual output and require comparison against an approved reference.

The InDesign scope additionally requires proprietary source files, font/link availability and human visual parity review.

## Decision

**KILL BEFORE BUILD.**

Do not build:

- another browser PDF preflight checker;
- a generic PDF/X score;
- an automated “print-ready” certificate;
- a font-embedding service without licensed font inputs;
- automated bleed, CMYK, resolution or transparency “fixes” presented as lossless;
- a hosted upload pipeline for customer artwork;
- an InDesign parity workflow without the licensed application and human review.

The repeated buyer evidence is real, but the payable job is specialist correction and accountable production handling. The autonomous diagnostic layer is free and crowded.

## Evidence ledger

| Predicate | State |
| --- | --- |
| Repeated buyer/problem evidence | Three independent scopes |
| Budget signal | EUR 30–250; USD 30–250; fixed-price verification |
| Exact acceptance artifact | Print-ready PDF + preflight evidence |
| Public/self-serve diagnostic feasible | Yes |
| Direct diagnostic substitute | Multiple free browser-local tools |
| Safe autonomous fixup | Falsified for general case |
| Commercial differentiation | Falsified |
| Waterfound WTT/WTP | None |
| Quantified value/ROI | None |
| Revenue | USD 0 |

## Kill criteria hit

1. free direct substitutes already produce the same report;
2. paid value depends on source assets, licenses and human production judgment;
3. automatic repair can alter appearance, editability or accessibility;
4. the printer's exact profile remains the acceptance oracle;
5. no Waterfound advantage is measurable before handling private customer files.

## Active–Secondary–Passive decision

- **ACTIVE:** seek a repeated buyer artifact where the machine-deliverable output itself—not bespoke correction—is what buyers pay for.
- **SECONDARY:** PDF preflight only if a future buyer requests a missing deterministic check not offered by the direct free tools.
- **PASSIVE / SUPPORT_ONLY:** font/box/color/resolution scanners, PDF/X scoring, dashboards, generic reports, hosted upload infrastructure and automatic fixups.

## Next machine-admissible frontier

Retain the two-signal rule. Prefer opportunities where:

1. two buyers request the same bounded output;
2. the exact machine-generated artifact is independently valuable;
3. no free direct tool supplies it;
4. the truth is present in public or browser-local inputs;
5. no proprietary editor, credential, certification or human visual judgment is required;
6. a fixture can measure decision accuracy before outreach.

No customer file was accessed. No website, account, outreach, proposal, publication, checkout, card/crypto integration, payment/KYC, spend, contract, runtime activation, private producer activation, writer lease, dispatcher, SQLite write or DISPATCH_FENCE action occurred.
