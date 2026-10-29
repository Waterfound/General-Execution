# WRM-T1 — Real PR #48 read-only differentiation probe
Observed: 2026-10-11T01:45:00Z (snapshot observation bound, not an independently authenticated live feed).
Status: CANDIDATE PRODUCT PROOF / NO COMMERCIAL DIFFERENTIATION ESTABLISHED.

## Real provider observations
- GE PR #48 remains open, draft, unmerged at exact head `4eb8fabd3d62493ddfc150f8e36a930c09fea2b7`.
- GitHub Actions runs 38079592440 (Constitution), 38079592456 (integration) and 38079592509 (durable terminal) report completed/success at this head.
- Branch approval policy, required checks policy, review threads and external buyer use were NOT fetched; these remain unknown.

## Actual offline candidate execution
Recovered the isolated v0.3 product ZIP, executed `PYTHONPATH=src pytest -q tests/`: **45 passed** locally.
Constructed an offline PR #48 snapshot using the directly observed PR metadata and three current-head GitHub workflow run receipts. Executed `PYTHONPATH=src python scripts/run_revenue_pr_ledger.py examples/revenue_pr_ledger/pr48-live-observation-20261011.json`.

Output: `disposition=DRAFT`; `missing_evidence=[conversation_resolution_policy,required_check_policy,required_review_policy]`; `evidence_level=SUPPLIED_SNAPSHOT_NOT_INDEPENDENTLY_ATTESTED`; `execution_triggered=false`; economic claims all null. Snapshot SHA256: `a7e5f8ad1ce1d35b6f07f8d34e56e7d6b33fc6a100a5ca1777a1a24f25557b1b`.

## Commercial interpretation (critical)
The provider-native GitHub PR page ALREADY says DRAFT and workflow run pages ALREADY show three successful checks. The v0.3 candidate faithfully repackages those facts and explicitly lists policy evidence gaps. This one case **does not establish incremental customer value or competitive superiority**. It would be misleading to count it as a validated product wedge. Do not expand dashboards, orchestration, SaaS hosting, or pricing from this evidence.

## Next independent discriminating test
Find a representative genuinely stalled, non-draft agent-created PR with mixed checks/reviews/recovery receipts and documented authority boundaries, using only authorized read-only evidence. Compare native provider-visible diagnosis vs candidate action classification on the exact same receipts, record any *new, correct, useful* action beyond native UI, then adversarially test a substitute. If no incremental diagnosis survives, kill/refine this wedge and promote another market thesis. Do not fabricate agent provenance, stalled conditions or manual baseline.

## UFP / EP evidence limits
This was a genuine local executable product-candidate run and new provider-bound PR observation, not a cold-restart/owner-dispatched mission-specific UFP rehearsal. Existing Revenue Mission Autonomy hourly schedule remains admitted as an existing recurring ChatGPT owner, but does not by itself certify UFP UNATTENDED_READY or a native Durable event. No new activation, merge, outreach, spending, credential, release or customer contact.
