# RMA-DIST-001 — Reconstructable candidate checkpoint

Date: 2026-10-12. Scope: isolated, reversible, no release, payment, personal data, mailing, new account, scheduler, runtime, merge or paid service.

## Preflight

- EP-FC-001 source: `Waterfound/Systems/architecture/EXECUTION_PROTOCOL_PREFLIGHT.md` (read/reconciled).
- UFP-001 source: `Waterfound/Systems/architecture/UNATTENDED_FLIGHT_PREFLIGHT.md` (read/reconciled).
- CR-001: General Execution PR #46 `docs/revenue-mission/WRM-CR001-COMMERCIAL-CLOSURE-20261012.md`; source doc reports head `682f9c60d6939ed5d768aa872ea6d7210d04de30`, **not independently asserted to remain latest throughout future time**. No selected product, no WTP, no revenue, weak direct differentiation.
- Ratchet: General Execution PR #48 candidate implementation and tests, **not merged or canonicalized by this work**.
- Independent use: isolated offline mock economics and entitlement state machine, standard-library tests; no overlap with CR-001 research files or shared ratchet state.

## Test acceptance

`cd experiments/wrm/distribution && python -W error::ResourceWarning -m unittest -v test_candidate.py`

Local outcome on 2026-10-12: **21/21 PASS**. `python run_rehearsal.py` produced deterministic synthetic funnel, out-of-order replay, cold-process reopening, duplicate webhook and cancellation checks. Evidence class: `SYNTHETIC_MOCK_ONLY`. No CI, Actions, external sandbox, production-webhook or unattended provider run claimed.

## Ratchet-facing candidate status (no shared writer)

| Predicate | Evidence | Status |
|---|---|---|
| Distribution channels researched | `CHANNEL_RESEARCH_2026-10-12.md` official sources | RESEARCH_VERIFIED (channel-level) |
| Channel feasibility established | provider restrictions + hard gates | CONDITIONALLY_ESTABLISHED, account/product unverified |
| Acquisition hypothesis selected | OSS + legitimate inbound conditional route | PROVISIONAL_ONLY |
| Distribution candidate implemented | offline contract, not landing/published site | PARTIAL_CANDIDATE |
| Activation instrumentation tested | synthetic SQLite counts | VERIFIED_MOCK |
| Monetization adapter verified | 21 tests, offline subscription transitions | VERIFIED_MOCK, NOT_PROVIDER_VERIFIED |
| Unit economics modeled | `run_rehearsal.py` scenarios | MODELED_HYPOTHETICAL |
| Recovery rehearsal passed | durable mock DB restart + conflicting/reordered events | VERIFIED_LOCAL_MOCK |
| Commercial launch gates identified | docs host, seller, KYB/KYC, taxes, publication, privacy, service policy | IDENTIFIED |
| First revenue path technically ready | no selected product/seller/host/provider or live end-to-end | NOT_READY |

## Critical blockers (re-evaluate before next action)

1. **Buyer differential / product selection:** CR-001 no product with proven buyer WTP. No public messaging or product landing permitted.
2. **Compliant commercial distribution and billing:** available providers only conditional; Vercel Hobby/GitHub Pages commercial sites barred, GitHub paid Marketplace scale/organization gate; Paddle software-only type constraint for service hypothesis.
3. **Operational autonomy:** no real recurrent owner admission or production-recovery evidence for RMA-DIST-001; local mock restart is not persistent machine work.

## Next independent authorized work

- CR-001: identify legally reusable real representative buyer-paid narrow job and a direct substitute/outcome comparison, as directed by its existing ratchet; do not broaden feature work to compensate for absence of buyer proof.
- RMA-DIST-001: once a selected product demands these, replace mock revision assumption with signed-provider authoritative verification in a provider sandbox, implement cancellation UX, refunds, chargebacks and lawful analytics; retain user authorization gate for any real provider account/payment/publication.
- Existing owner: evidence-based recurrent admission **only** after preflight, authentic wake and UFP verification; do not silently activate new scheduler.

## Final disposition in this wave

- `RMA_DIST_001_RESEARCH_VERIFIED` — PASS for public channel screening with explicit account-eligibility caveats.
- `RMA_DIST_001_ENGINEERING_VERIFIED` — PASS **only for local isolated mock tests**, not real provider integration.
- `RMA_DIST_001_FIRST_REVENUE_PATH_READY` — NOT YET; product, seller, host, legal and live reconciliation missing.
- `RMA_DISTRIBUTION_OPERATIONAL_VERIFIED` — NOT YET; no real launch, customer or revenue.

No genuine human action requested for mock preparation; eventual seller/KYC/financial terms/publication/charge collection require separately explicit approval.
