# CR-001 — Austin/Travis real public-data reconciliation (candidate)

**Execution date:** 2026-10-12 local (São Paulo). **Parent:** GE PR #57 exact head `ce780783a0bfc53828c4e49957e436915b8b5806`. Candidate branch `wrm/cr001-real-permit-gis-proof-20261012`. No main merge or product release.

## What was actually done

Read three genuine City of Austin issued-permit records from its publicly readable Socrata dataset 3syk-w9eu; selected only non-private columns `permit_number`, `tcad_id`, `issue_date`, `permit_class_mapped`, `jurisdiction`. Obtained `original_zip` through bounded publisher queries. Used two public, exact Geographic-ID ArcGIS REST queries for Travis County `TCAD_public/MapServer/0` with only geographic ID, public `PROP_ID`, situs ZIP/street; independently requested `returnCountOnly=true` for both IDs (**1 each**). No property owner/person name, contact details, legal conclusion or owner identity retained.

Source URLs, response scopes and cardinality checks are in `observations.json`. **Observation class:** connector-extracted public JSON; *not authenticated or hashed raw HTTP bytes*. Input is a three-row bounded sample, NOT full permit-dataset or county completeness. Austin data dictionary explicitly says `tcad_id` aligns with TravisCAD Geographic ID. Both GIS public responses contain one exact feature; equal 5-digit publisher ZIPs provide an independent conflict screen. No legal parcel-unit identity is established.

| Austin permit | Geographic ID | Public GIS property reference | Result |
| --- | --- | --- | --- |
| 2026-115272 PP | 0239360701 | 992875 | MATCHED_GEOGRAPHIC_REFERENCE |
| 2026-117823 PP | 0339500820 | 822637 | MATCHED_GEOGRAPHIC_REFERENCE |
| 2026-117826 PP | 0339500820 | 822637 | MATCHED_GEOGRAPHIC_REFERENCE |

Two valid permits sharing one Geographic ID are **not** duplicates or proof of a data problem.

## Reproducible engineering

```sh
cd experiments/wrm/permit_property
python -m unittest -v test_permit_property.py
python permit_property.py observations.json > report.json
```

No external Python packages, API credentials or runtime needed. Verified **39/39 exact-file local unittest PASS**. Negative cases include leading-zero IDs, duplicate permits, multiple GIS candidates, independent GIS cardinality drift, incomplete pages, missing IDs, postal conflicts, invalid date, malformed permit, input type confusion, source host/dataset drift, unknown provenance, and proof overreach. The output consistently declines to assert any owner, property title, lead quality, or commercial value.

**Exactly executed source blobs:** Python `58de43c88cffb21d23824e26d5fc753988b99cef`, tests `85a01837eea6b52b472ccf14083e1d943b1a8e22`, fixture `5ed9e9fda29a4cd2248d392b388f0be32b14ef4a`. Reproducible normalized snapshot digest `d2cb506064ceea283a94ccc58a305a86ff943cf53247e1818d9206eb2ef196ae`. Original HTTP response SHA **not obtained**. Retained test log and local report digest in the receipt.

## Competitive falsification

- **City of Austin** already provides public permit data, including publisher-documented TCAD ID linkage, daily updates and a public Socrata API. A simple cross-reference of public identifiers is not unique.
- **Travis County GIS / TCAD** exposes the matching Geographic ID and public parcel reference by exact query. A basic ID lookup is not a new product.
- **PermitStack** markets permit ingestion, enriched contractors, bulk CSV, source freshness and free/$29+ tiers; [its pricing](https://permit-stack.com/pricing/) is **marketing, not independently verified Waterfound parity or actual consumer spending**.
- **Shovels.ai** publicly describes integrated decisions, permits, contractor and property data. Claims are vendor-authored; same-case output was **NOT EXECUTED**.
- **PermitGrab** publicly shows Austin publisher-backed provenance/freshness observations with reproducible queries. These directly undercut claiming “publisher provenance” alone as a moat.

One source-bound two-field join and failure controls are technically demonstrated but not defensible paid differentiation. No same-input native-competitor result or external buyer approval was obtained.

## Economic reality of $30 per accepted jurisdiction

The public Upwork listing is a **posted contract-labor price**, not a Waterfound price/contract or software WTP: https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/

Illustrative algebra only: expected gross return per attempt = `$30 × P(accepted)`. At hypothetical `P(accepted)=80%`, expected gross is **$24 per attempt**, before compute, corrections, support, taxes or maintenance; if a deliverable requires 2 hours of total machine + operational supervision combined, that's **$12 gross per hour equivalent**, not measured labor or unit margin. The complete requested fields, true acceptance probability, execution labor and infrastructure operating costs were NOT accessible and were NOT fabricated. The scope requires separate portal adapters and long-term maintenance; hence profitable one-machine unattended delivery is unproven.

## Decision gate

**`CR001_REAL_PUBLISHER_SAMPLE_JOIN_CANDIDATE_VERIFIED`** for three permits and two Geographic IDs. **`CR001_FIRST_DEFENSIBLE_PRODUCT_SELECTED = FALSE`**.

**`KILL_AS_FIRST_PRODUCT`**: generic permit scraper / basic permit↔GIS lookup at a $30 accepted-per-jurisdiction labor listing. This is a strategic no-build decision on current evidence and support burden, not proof that every future variant is unprofitable.

The only defensible residual **HYPOTHESIS** would be an integrity/error outcome whose failure costs and same-input superiority over publisher/PermitStack/Shovels/PermitGrab can be independently demonstrated, with an identified buyer paying for it. Without that, do not expand code or integrations.

### Next admissible commercial action

Return to the existing Commercial Progress Ratchet and evaluate a **different buyer-paid, public-input, output-verifiable job** with lower source/credential/maintenance burden. Only build after a real competitor-output discriminator survives. Share minimal product scope with RMA-DIST-001; no duplicate runtime, new System or scheduler. No customer contact, signup, money movement, commercial publication, credentials, repin, Work or merge was authorized.

**No WTP for Waterfound; no client; verified revenue: US$0.** This is local code execution + public source observation, not mission-specific authenticated unattended continuation.
