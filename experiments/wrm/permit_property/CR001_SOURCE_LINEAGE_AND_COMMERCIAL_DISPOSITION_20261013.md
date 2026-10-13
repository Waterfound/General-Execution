# CR-001 — Verified GIS query lineage, adversarial acceptance limits, and commercial disposition

**Status:** `DONE_TECHNICAL_CANDIDATE__FIRST_DEFENSIBLE_PRODUCT_NOT_SELECTED`. This is an isolated **candidate**, stacked on GE #60 exact base `6399a7cd7bd34e392e6059f3f008db523e7ba388`. The branch is not canonical, not a customer implementation, and not a deployed recurring job.

## Finding and actual repair
GE #60's offline Austin → Travis reconciler used `gis_url` (the **first** Geographic ID query) for every result's `source_gis`. It validated neither `gis_url_second` nor `gis_count_urls` against the corresponding IDs. This permitted a false/missing declared query or swapped dataset lineage without a fail-closed check, even though the supplied record count/ZIP reconciled.

This child fixes *declarative provenance integrity*:
- Exact HTTPS host/path and query parameters for Austin Socrata dataset `3syk-w9eu` and Travis TCAD layer `MapServer/0/query`; duplicate, unexpected, missing, or misleading query parameters rejected.
- Two exact 10-digit `geo_id` feature queries, one per requested ID, each requiring the field set and `returnGeometry=false`.
- Each separately declared count URL bound to the identical ID with `returnCountOnly=true`; malformed and extra mappings rejected.
- Correct `source_gis` attribution **per permit**, including both permits sharing the second Geographic ID.
- Explicit 3-permit, 2-GIS-ID evidence bound, full-source incompleteness, and supplemental Austin ZIP provenance limitation.
- Original 0-result and ambiguous (2-result) **nonidentity** outcomes preserved, not converted into false certainty.

## Actually executed in local Python 3.13.5
```sh
cd experiments/wrm/permit_property
python -m unittest -v test_permit_property.py test_source_binding.py
python permit_property.py observations.json
```
**69/69 PASS**: original 39 regression tests, 26 URL-lineage tests, and 4 full-reconciler provenance/adversarial tests. No skipped/failed. Exact tested source/test/observation Git blobs and the local test-log SHA-256 are in `CR001_SOURCE_LINEAGE_TEST_RECEIPT_20261013.json`. Independently checked Git blob identities for all five executed input files. This is **LOCAL** execution, not native GitHub CI. GE #60's earlier Canonical Constitution Gate is a different workflow and cannot be presented as this 69-test run.

Result on prior actual **connector-extracted** government sample: 3 bounded permits, 2 geographical IDs, three reported geographic reference matches, and correct ID-specific source URLs. ZIPs coincide on the saved normalized records. It is NOT a census of Austin permits, a parcel-title finding, or independent proof of official current HTTP bytes.

### Provenance falsification that remains OPEN
An adversarial test changed a **normalized fixture** GIS `PROP_ID` to a different positive number without changing its declared URL; the offline reconciler accepted and reported the altered reference. This is expected given **no downloaded/signed/pinned provider response bytes** and is an important negative assurance result. Never claim that a declared official URL cryptographically authenticates row content. Supplemental Austin `original_zip` also lacks a per-row frozen first-party ZIP source-response trace.

**External evidence gate:** obtain legal exact official raw JSON response bytes, digest + request URL + acquisition date, independent replay/check of counts and fields, ZIP/feature query row binding, and bounded pagination/sample sampling logic. Until then `RAW_PROVIDER_BYTES_AUTHENTICATED=false`, `COMPLETE_JURISDICTION_VALIDATED=false`, `OWNER_LOOKUP_VERIFIED=false`.

## Same-buyer-value competitive screen

- The posted permit scraper work offers **USD 30 per independently accepted jurisdiction scraper**; its real acceptance asks for complete jurisdiction pagination, 20 specified output fields, owner lookup by address when missing, contractor company email/phone where available, a clean unattended Windows run, and writing into a private target Sheet. Reference: https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/ . This is client posted labor budget, **not** demonstrated willingness to buy a Waterfound product. Access to the undisclosed 20-field rules, private Sheet and complete acceptance fixture has not been granted.
- **PermitStack**, firsthand pricing: free plan, paid from USD 29/month, location/address search, normalized city permit data and CSV exports; its Developer/Business tiers advertise contractor contact and property-owner mailing address where published. Sources: https://permit-stack.com/pricing/ and https://permit-stack.com/ . This directly substitutes **generic public-permit access**, without proving exact client-acceptance parity.
- **Shovels.ai**, firsthand API: geographic permit and contractor search, broad multi-jurisdiction ingestion: https://www.shovels.ai/solutions/api . No same-input licensed/account-connected benchmark executed.
- Adjacent GIS validation is already in the free QGIS Geometry Checker and Shapely STRtree. Separate exact-source **GE #63** ran a same-input synthetic Shapely comparator materially faster than its generic custom O(n²) overlap candidate; do not revive that as a commercial product without a new unique buyer result. Sources: https://documentation.qgis.org/3.44/en/docs/user_manual/plugins/core_plugins/plugins_geometry_checker.html and https://github.com/Waterfound/General-Execution/pull/63 .

**Falsification:** Present code only joins three public records with guarded URL declarations. It does **not** implement any private buyer acceptance criterion beyond a partial geographic ID cross-reference. Nothing proves the incumbent lacks the needed capability or that this candidate is economically superior. `KILL_GENERIC_PERMIT_SCRAPER_AS_FIRST_PRODUCT` and `KILL_GENERIC_GIS_OVERLAP_VALIDATOR_AS_FIRST_PRODUCT` remain correct *first-product* decisions, not claims all niche GIS work is economically infeasible.

## USD 30 / acceptance economics — explicit scenarios, not realized returns

Let `p` = accepted scrapers / attempted scrapers and `h` = end-to-end **human-equivalent delivery and maintenance hours per attempt**. Before platform fees, taxes, QA overhead, machine costs, rework and support:

| Acceptance p | Hours/attempt h | Expected gross/attempt | Gross per delivery hour |
|:--|--:|--:|--:|
| 100% | 1 | $30.00 | $30.00 |
| 80% | 2 | $24.00 | $12.00 |
| 50% | 4 | $15.00 | $3.75 |

These assumptions were **not measured**. Net profit may be lower or negative. At 80% acceptance, a hypothetical $15/hour opportunity cost alone requires no more than `$24/$15 = 1.6 hours` total work per attempt **before other costs**; if a portal breaks and causes recurring manual intervention, the One-Machine/near-zero-One-Man constraint fails. Without complete client acceptance fixtures, buyer behavior, renewal/maintenance data, and a legal autonomous delivery/payment path, no defensible unit economics exists.

## Commercial ratchet disposition

1. **REJECT FIRST PRODUCT:** generic permit scraper / raw data resale. Three-record source join is technically useful research, not a buyer deliverable.
2. **REJECT FIRST PRODUCT:** generic GIS overlap validator, as GE #63 demonstrated a strong free same-input substitute.
3. **HOLD:** USD 1,000 comprehensive GIS QC buyer task (5M features/30min, 2k seeded issues, precision/recall/false positives, reversible fixes), because exact private ground truth and at-scale acceptance have not been lawfully obtained; likewise USD 500 private controller audit GE #61.
4. **CANDIDATE CAPABILITY ONLY:** reusable official-source provenance gate in this draft. **Do not promote it to product** without a public input + independently assessed, paid acceptance not cheaply reproduced by free competitors.
5. **NEXT admissible selection evidence:** pivot research to independently verifiable buyer-funded problems with lawful representative input **before implementation**, compare against a real free same-input baseline, prove an outcome the buyer otherwise cannot cheaply achieve and near-zero human support. If external acceptance/WTP/private input is essential, record it as an external gate, not product selection. Do not manufacture customers or switch back to infrastructure-only activity.

**No outreach, account signup, spend, production, release, provider/scheduler/runtime mutation, human labor assumption, user-provided private data, or merge. No first revenue.**

Terminal flags:
```text
CR001_PUBLIC_QUERY_LINEAGE_CANDIDATE_VERIFIED = true (bounded declared URLs only)
CR001_AUTHENTICATED_PROVIDER_BYTES_VERIFIED = false
CR001_FULL_CLIENT_ACCEPTANCE_VERIFIED = false
CR001_SAME_INPUT_COMPETITOR_SUPERIORITY_VERIFIED = false
CR001_FIRST_DEFENSIBLE_PRODUCT_SELECTED = false
ONE_MACHINE_FIRST_REVENUE_READY = false
REVENUE_USD_OBSERVED = 0
```
