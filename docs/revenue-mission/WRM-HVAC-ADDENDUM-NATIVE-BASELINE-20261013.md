# WRM — HVAC addendum residual: public-fixture native-baseline test

Date: 2026-10-13  
Status: BOUNDED REAL-FIXTURE TEST / RESIDUAL GENERIC WEDGE KILLED / NO PRODUCT SELECTED.

## Predicate

Can a no-control-plane, addendum-only review give a small HVAC subcontractor a materially different source-cited changed-scope decision than ordinary PDF reading/search and already-advertised construction-document products?

This tests the surviving residual in `WRM-TRADE-ESTIMATOR-ADDENDUM-SCOPE-LOSS-20261011.md`. It does not test customer demand, installed competitor parity, pricing, ROI, or automatic bid decisions.

## Official fixtures inspected

1. City of Worcester bid 8467-W6, RTU Replacement — Franklin Street Fire Station:
   - listing: https://www.worcesterma.gov/finance/purchasing-bids/bids/8467-w6
   - base drawings: https://www.worcesterma.gov/sites/default/files/bids/8467-W6-RTU%20Replacement-Franklin%20Fire-Drawings.pdf
   - Addendum 1: https://www.worcesterma.gov/sites/default/files/bids/8467-W6-ADDENDUM-1.pdf
2. City of Worcester bid 8599-F6, DCU Center Permanent Chiller:
   - listing: https://www.worcesterma.gov/finance/purchasing-bids/bids/8599-f6
   - Addendum 1: https://www.worcesterma.gov/sites/default/files/bids/Addenda%20%231_0.pdf
   - Addendum 2: https://www.worcesterma.gov/sites/default/files/bids/Addendum%20Number%202.pdf

The municipal listings expose these documents without registration and state that bidders are responsible for checking addenda. Read-only inspection does not imply redistribution or training rights.

## Observed obligation truth set

### 8467-W6

The base M001 drawing contains a DDC-oriented rooftop-unit sequence, while the demolition keynote says the existing thermostat and control wiring are to be reused. Addendum 1 asks whether the new units must join the City's Alerton BMS and resolves the ambiguity: use integral factory-mounted controls, reconnect existing thermostats/control wiring, and maintain the existing control strategy.

Decision-level delta: do not carry a new Alerton/DDC integration merely from the generic sequence. This is a clarification of governing controls scope, not a revised page or quantity change.

### 8599-F6 Addendum 1

Eight explicit RFI answers yield eight reviewable obligations or conditions:

1. no allowance for possible duct relocation; the prime contractor owns modification caused by its means and methods;
2. AISC certification may be waived only with at least five years of similar-project experience and three comparable projects for review;
3. the ATC contractor provides refrigerant leak detection;
4. provide four sensors with wells, per M501;
5. provide one new isolation valve;
6. provide one new electromagnetic flow meter;
7. chilled-water pumps are controlled by BMS;
8. the Contractor pipes manufacturer-provided differential-pressure transmitters.

Addendum 2 contains filed electrical sub-bid tabulation and general-bidder selection instructions, but no specification or drawing revision.

## Native and substitute baseline

- A drawing-revision overlay is not the relevant baseline for these fixtures: neither addendum issues revised drawings or specifications. The commercially important information is in RFI answers and responsibility assignments.
- Ordinary text extraction/search plus direct reading exposes every item above. The 8467 ambiguity also becomes visible by searching `DDC`, `thermostat`, and `control wiring`; the addendum itself states the controlling answer.
- A structured role/quantity/condition checklist would reduce navigation, but no measured estimator time, error reduction, missed item, or quote outcome was observed.
- Provision already advertises subcontractor-specific obligation extraction, citation-backed scope gaps, and cited answers across drawings, specifications, contracts, and addenda. That is advertised capability, not an installed same-input benchmark, but it directly covers the proposed output.
- Bluebeam remains useful for actual PDF revisions but is not the strongest substitute for answer-only addenda; its weakness here does not establish a Waterfound advantage because native reading and Provision cover the decision.

## Commercial decision

**KILL_AS_UNIQUE_DIFFERENTIATOR**:

- generic addendum summarization;
- source-cited scope/quantity/responsibility checklist;
- no-control-plane upload-and-review positioning;
- “find what changed” when the addendum explicitly enumerates RFI answers.

The fixtures validate that addenda can move cost-bearing responsibility and controls scope without revised sheets. They do **not** show that a new product produces a decision unavailable at negligible friction, that incumbents miss the items, or that a buyer will try or pay for Waterfound's version.

Do not build the planned parser, dashboard, or upload service from this evidence. A new construction wedge is admissible only with a harder representative case containing a complete independent expert truth set and a materially important decision missed by both a skilled native review and at least one directly comparable product at similar friction.

## Evidence state

- Capability: public source retrieval and obligation extraction observed.
- Observed outcome: 9 decision-bearing clarifications/obligations identified across two Addendum 1 documents; 0 independently verified misses versus a complete expert truth set.
- Competitive differentiation: failed for the generic addendum-only checklist.
- Demand, willingness-to-try, WTP, customer, saved hours, avoided loss, and revenue: unverified / none.
- Portfolio state: HVAC addendum residual closed as a generic first-product wedge; continue buyer/job discovery rather than instrumenting it.

No outreach, account creation, spend, private document use, publication, runtime or scheduler change, merge, quote submission, or binding commercial act was performed.
