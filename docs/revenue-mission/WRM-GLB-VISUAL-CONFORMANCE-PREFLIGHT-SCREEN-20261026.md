# WRM — GLB visual-conformance preflight screen — 2026-10-26

Status: **REAL PRODUCTION PAIN / ADJACENT WTP CONFIRMED / FREE STRUCTURAL QA STRONG / EXACT VISUAL-DIFF WEDGE OCCUPIED / NO_BUILD / CLOSED**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound sell a low-touch, read-only preflight that catches visually important defects in a GLB before web/commerce delivery—especially transparency at silhouettes, material/texture drift, render mismatch, and loop defects—without duplicating free conformance tools or existing visual-regression products?

This screen follows an observed real workflow class: a technically valid GLB can still look wrong. It does not treat that observation as external demand, willingness to try, willingness to pay, customer outcome, or quantified value.

## Buyer/problem evidence

The surrounding job has proven spend:

- An Amazon seller described paying about USD 250 for a commerce-ready GLB and a multi-day production cycle. This is anecdotal spend for asset creation, not for Waterfound QA.
  - https://sellercentral.amazon.it/seller-forums/discussions/t/e5465bfe-a2de-4d11-885d-7ad788de974c
- Fiverr exposes many GLB/glTF creation, conversion, optimization and repair offers. One repair listing shows 13 reviews and transactions around USD 50–100; broader listings start around USD 10–50.
  - https://www.fiverr.com/gigs/glb
  - https://www.fiverr.com/waqas17/fix-your-glb-3d-file
- Shopify tells merchants to inspect whether they are satisfied with model quality, while its partner checklist treats merchant satisfaction plus technical standards as approval conditions.
  - https://help.shopify.com/en/manual/products/product-media/expert-3d-model
  - https://help.shopify.com/en/partners/resources/creating-media/3d-models/creating-3d-models/3d-modeling-checklist

These sources establish that people pay to create and repair commerce assets and that visual acceptance remains meaningful. They do **not** establish WTP for an independent automated preflight report.

## Native and free substitution

The proposed structural layer is already strongly substituted:

- Amazon explicitly requires the Khronos glTF Validator and recommends the Khronos Sample Viewer for a close preview of its rendering.
  - https://sellercentral.amazon.com/help/hub/reference/external/G7RGSNQFZ2BAG7K3
- Khronos provides the glTF Validator, Sample Viewer, Asset Auditor and commerce-oriented audit profiles. The Asset Auditor checks file attributes against deployment requirements and is available as an open package.
  - https://www.khronos.org/gltf/
  - https://github.com/KhronosGroup/gltf-asset-auditor
  - https://www.npmjs.com/package/@khronosgroup/gltf-asset-auditor
- Khronos Render Fidelity provides side-by-side, slider and difference comparisons across renderers for reference assets.
  - https://github.khronos.org/glTF-Render-Fidelity/
- ModelReady already checks GLB files in-browser against published Amazon and Shopify requirements.
  - https://github.com/modelready/modelready-validator
- MeshQA markets local validation, platform/engine rules, CI integration, health scores, security checks and reports.
  - https://meshqa.meshmarket.net/documentation/guides

A report limited to schema validity, mesh statistics, texture dimensions, platform budgets, extension use, animation inventory or packaging would add no defensible job.

## Exact visual-diff substitution

The narrower residual—prove that optimization or conversion did not change how the asset looks—is also occupied:

- SpatialPack offers six-view visual diff with ΔE94, SSIM and threshold-gated CI, plus checks for Apple Quick Look, Safari, Shopify AR and Khronos conformance.
- Its analyzer and visual checks are free with no account; the paid product repairs assets at USD 15/model after three free models or USD 39/month for Pro.
  - https://www.spatialpack.dev/
  - https://www.spatialpack.dev/pricing
- Nextech markets asset QA and governance with version control, approvals, performance budgets, channel profiles and human-in-the-loop review for assets that must remain on-brand.
  - https://www.nextechar.com/platform/asset-management-qa

This is direct functional and pricing evidence against a Waterfound visual-regression preflight. A synthetic GLB fixture could prove implementation capability, but it would not answer a missing commercial predicate because the exact proof is already public and free or inexpensive.

## Differentiation test

| Candidate output | Best substitute | Residual |
| --- | --- | --- |
| glTF/schema correctness | Khronos Validator | None material |
| Commerce budgets and profiles | Khronos Asset Auditor, ModelReady | None material |
| Viewer/render inspection | Khronos Sample Viewer and Render Fidelity | Reference assets only, but sufficient for conformance development |
| Local/CI policy validation | MeshQA and SpatialPack | Occupied |
| Multi-view before/after visual diff | SpatialPack | Exact wedge occupied |
| Human brand/visual judgment | Shopify acceptance workflow, Nextech and freelancers | Human review; conflicts with near-zero-operation autonomy |
| Coin-specific alpha, side material and loop taste | Manual creative QA | Too narrow and not independently demand-validated |

## Decision

Close the standalone GLB visual-conformance preflight before build.

The problem is real, and adjacent buyers pay for 3D creation, conversion, optimization and repair. However:

1. free official tooling already covers structural and commerce-profile validation;
2. an incumbent exposes the proposed multi-view visual-diff gate free and monetizes repair/optimization;
3. low-cost freelancers demonstrate a dense manual substitute market;
4. the remaining defects require reference imagery, artistic intent and subjective acceptance;
5. no buyer has requested a Waterfound report, trial, or price.

Do not build a parser, renderer farm, browser upload tool, CI action, dashboard, asset host, optimizer, conversion service, benchmark or paid plan for this wedge.

Keep GLB checks only as **SUPPORT_ONLY** inside a separately validated product workflow. The observed workflow may supply future synthetic fixtures, but private assets, customer files and identity-sensitive references remain outside scope without explicit authorization.

## Kill criteria applied

The candidate is killed because all of the following hold:

- the exact multi-view visual-regression function exists;
- structural validation is free and authoritative;
- direct paid repair is available at low prices;
- a standalone report has no independent demand or WTP evidence;
- the residual depends on subjective visual intent or human acceptance.

## Reactivation criteria

Re-enter only if an external buyer independently requests a narrower machine-verifiable acceptance predicate that current tools demonstrably miss, supplies a lawful public or authorized fixture, and accepts an evidence-only result without creative judgment. Before any product work, require a matched comparison showing a decision-relevant miss by Khronos Asset Auditor, ModelReady, MeshQA and SpatialPack.

## Evidence accounting

- Capability: Waterfound has observed a real GLB quality workflow; no candidate proof built.
- Observed outcome: technical validity and visual correctness are distinct; no customer outcome.
- Competitive differentiation: falsified for structural QA and multi-view visual diff.
- Demand evidence: adjacent creation/repair spend only.
- WTP for exact Waterfound job: none.
- ROI/value proof: none.
- Revenue: USD 0.
- Mission posture: **PASSIVE / ROUTE_CLOSED**; continue commercial discovery elsewhere.

No customer file, private asset, renderer infrastructure, account, API key, upload, outreach, proposal, publication, spend, payment/KYC, contract, runtime activation, state-dispatcher write or Privacy P0 activation occurred.
