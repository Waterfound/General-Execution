# CR-001 | Same-input free GIS substitution and next paid-job screen (13 October 2026)

**Status: KILL generic GIS overlap checker as first product; broader buyer GIS contract HOLD.**

## Source and acceptance reality
Posted GIS QC job: https://www.upwork.com/freelance-jobs/apply/GIS-Data-Quality-Controller-Agent_~022101716284364662488/ . Listed USD 1,000 fixed is a budget signal, NOT an awarded Waterfound contract. Requirements include 2,000 seeded defects >=95% recall, <=2% clean-control false-positive rate, no unrequested modifications, reversible repairs, 5M features <=30m on 8 vCPU/32 GB, semantic adjudication, ISO 19157 reporting, bilingual responses and GIS layer publication. Current code is not a contract delivery.

## Independent competitive falsification
Installed Shapely 2.1.2 already supplies polygon validity, make_valid and indexed STRtree geometry lookups: https://shapely.readthedocs.io/en/2.1.2/strtree.html . With two repeats on identical synthetic fixtures (two separately seeded overlaps), the candidate O(n^2) comparison yielded exactly the same overlap pairs as free Shapely STRtree:

| N | Candidate median ms | Free Shapely median ms | Candidate/free |
| ---: | ---: | ---: | ---: |
| 20 | 3.509 | 0.192 | 18.27x |
| 60 | 30.360 | 0.372 | 81.66x |
| 100 | 81.445 | 0.526 | 154.90x |
| 180 | 269.791 | 0.816 | 330.45x |

24/24 local tests pass (19 original plus 5 additional) on exact checked-in Git blobs. Original 45-second longer benchmark timed out; no generalizable per-feature measurement was extracted from that run. Native GitHub CI did NOT run this new suite. Detailed machine-readable values and SHA receipts are in CR001_GIS_NATIVE_PARITY_RECEIPT_20261013.json. Reproduce: cd experiments/wrm/gis_qc && python -m unittest -v test_gis_probe.py test_benchmark_substitutes.py && python benchmark_substitutes.py .

QGIS has native geometry/topology validation and geometry-fixing options documented at https://doc.qgis.org/testing/en/docs/user_manual/working_with_vector/vector_properties.html and https://documentation.qgis.org/testing/en/docs/user_manual/processing_algs/qgis/fixgeometry.html . QGIS itself was **NOT executed**. This is a real same-input comparison to stock Shapely, not a claim of installed QGIS parity.

### Material limits
Synthetic-only geometry; no authentic provider bytes, no buyer 2,000-defect ground truth, no measured recall/FPR, no ISO 19157 compliance, no 5M/30min benchmark, no independent buyer acceptance. Nothing establishes positive Waterfound competitive superiority. The direct free substitute covers the simple value proposition, so writing a larger custom GIS checker would lower expected marginal commercial value.

## Commercial alternatives screened without code duplication
- GE #61: USD 500 Google Sheets/Apps Script/Python-Windows controller audit; actual posted buyer problem and observable counts, but logs and root-cause trace are private, and built-in Google monitoring/batching already cover basic optimization. **HOLD**, no independent acceptance input.
- Weekly Excel reconciliation posted at USD 8–10/hour: https://www.upwork.com/freelance-jobs/apply/Weekly-Excel-Data-Reconciliation-Specialist_~022104333107026349304/ . Real recurring operator workflow and an optional paid test, but requires 20–25 private screenshots, an existing private master file, continuous weekly validation and high-usage paid ChatGPT. **HOLD high One-Man burden**, not zero-human delivery.
- GoHighLevel CRM remediation: https://www.upwork.com/freelance-jobs/apply/GoHighLevel-Expert-Pipeline-Repair-Deduplication-Data-Verification_~022103528277149789583/ . Real narrowly described remediation, but sensitive healthcare-CRM private access, business-owner coordination, production writes, handover and 14-day support are incompatible with present autonomy/authority. **KILL for current mission**.

### Commercial ratchet
- P0 public *buyer-posted budget*: YES for GIS, NOT buyer willingness to pay Waterfound; no verified sale.
- P1 comparative GIS generic wedge: **FAIL** (free native parity, candidate considerably slower).
- P2 almost entirely autonomous paid delivery: **HOLD** (real lawful client input, independent acceptance and economics absent).
- P3 legitimate low-touch acquisition: **HOLD** (no permitted platform integration, outreach or payments).
- **Revenue USD 0; product selected FALSE.**

Do not reopen commodity permits, E-Rate change alerts, generic PR verification or generic GIS validity. Next machine-admissible action: find a buyer-funded task with a complete lawful public example and independent acceptance truth, then compare same-case native substitute before any new build. Avoid new schedulers, providers, Work, spending, outreach, client claims or canonical merges. This draft remains a candidate child of PR #60; Systems #25 is the single Commercial Ratchet status owner.
