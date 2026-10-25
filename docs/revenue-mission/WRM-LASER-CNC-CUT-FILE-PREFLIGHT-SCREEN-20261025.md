# WRM — Laser/CNC cut-file preflight screen (2026-10-25)

## Decision

**KILL before prototype.** The proposed local-browser SVG/DXF preflight is a densely substituted free utility. No missing commercial predicate was found.

## Narrow job tested

> Before sending a 2D cut file to laser, plasma, waterjet or CNC, identify deterministic geometry/import defects that can reject a quote or waste material.

Proposed checks: open/nearly closed contours, duplicates/overlaps, live text and images, unsupported entities, self-intersections, tiny/zero-length geometry, units/scale, non-zero Z, bed fit and kerf-sized features.

## Problem evidence

The problem is real: open contours, duplicate cuts, unsupported splines, scale ambiguity and accidental Z values can break CAM import, burn edges, reject a job or waste material. Recent operator discussion reports recurring cleanup of exported customer files:
https://www.reddit.com/r/lasercutting/comments/1vjyhel/

However, material, thickness, process, tolerances, finishing, quantity and machine rules cannot be inferred safely from geometry alone.

## Direct substitution

Exact free browser/local substitutes include:

- Laser File Check — SVG/DXF; open paths, duplicates, live text, images, size/units, tiny geometry and DXF-specific entities:
  https://laserfilecheck.com/
- DXF Cut Preflight — local browser/extension; contours, duplicates, units and bed fit:
  https://www.dxfpreflight.com/
- sparq.tools File Check — duplicate lines, open paths, stray geometry and kerf-sized features:
  https://sparq.tools/
- LEVRTEK 2D — local DXF analysis; dimensions, cut length, pierces, contours, duplicates and unsupported entities:
  https://levrtek.com/2d/
- FilesCNC File Doctor — DXF/SVG/STL checking and repair:
  https://filescnc.com/file-doctor/
- Cut Files Shop optimizer — duplicates, open contours, splines/ellipses and zero/tiny geometry:
  https://www.cutfilesshop.com/pages/free-dxf-cnc-file-optimizer
- EZ Nesting checker — open outlines, endpoint gaps, duplicates/overlaps, splines/ellipses, text and zero-length lines:
  https://eznesting.com/dxf-viewer
- DXF Cleaner — local cleanup and contour closing:
  https://dxfcleaner.com/
- Nestpact — checking plus nesting and NC generation:
  https://nestpact.app/

A recent maker also published a free local DXF repair tool:
https://www.reddit.com/r/hobbycnc/comments/1w1jf92/

## Evidence classification

- Capability: not built; substitution failed first.
- Observed customer outcomes: not measured.
- Competitive differentiation: absent for the proposed check family.
- Demand: problem discussion exists, but willingness to use Waterfound's implementation is untested.
- WTP: not established.
- Revenue: USD 0.

## Kill criteria applied

Killed because:

1. multiple free tools cover the complete deterministic core;
2. several are already local/private in-browser;
3. adjacent products extend beyond lint into repair, nesting and G-code/NC generation;
4. no buyer evidence identifies a high-value omitted rule or workflow;
5. process-aware certification would require shop-specific inputs and responsibility beyond a static file check.

## Re-entry condition

Only reconsider with buyer evidence for a shop-specific batch/integration workflow that demonstrates measurable rejection handling or quoting cost and is not handled by existing CAM, quoting, nesting or preflight products. Do not re-enter for another generic validator, viewer, cleaner or checklist.

## Mission consequence

No prototype, publication, outreach, account installation, spend, KYC, payment, contract or recurring entitlement was used. Candidate status: **CLOSED / SUPPORTING MARKET EVIDENCE ONLY**.
