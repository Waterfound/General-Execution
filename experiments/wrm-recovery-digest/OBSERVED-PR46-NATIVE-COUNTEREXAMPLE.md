# WRM — Native-only PR recovery discriminator: observed counterexample
Observation date: 2026-10-10 (UTC). Evidence class: REAL REPOSITORY OBSERVATION / NO CUSTOMER VALIDATION.
Scope: read-only GitHub observations. No external installation, outreach, merge or release.

## Source-bound observations
- General Execution PR #46: https://github.com/Waterfound/General-Execution/pull/46
- Exact observed head: 1528b070acd76694027a3cb60d2940a9c8e014b0.
- State OPEN, DRAFT=true, mergeable=true as reported by PR metadata (mergeable does NOT authorize merge).
- Three pull-request-triggered workflows associated with that head completed SUCCESS:
  * Canonical Constitution Gate: https://github.com/Waterfound/General-Execution/actions/runs/38079675136
  * Main integration gate: https://github.com/Waterfound/General-Execution/actions/runs/38079675068
  * Durable terminal verification: https://github.com/Waterfound/General-Execution/actions/runs/38079675091
- GitHub PR review API returned an empty list at observation. No authoritative branch/ruleset required-check or required-approval policy was established by the available evidence.
- Combined commit-status endpoint returned zero status objects; this does NOT contradict the workflow/check results (GitHub Actions produces checks, not classic commit statuses).
- This PR is a research draft, not a customer-created stalled coding-agent PR; therefore it is a negative control, not a representative buyer case.

## Native baseline vs incremental inference
Native GitHub PR view/Checks already supplies draft state, check outcomes, mergeability and review information; its documentation explains current-head checks and branch-protection requirements: https://docs.github.com/en/pull-requests/reference/status-checks and https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
Candidate digest can restate three successful runs and DRAFT. Without an authoritative required-check policy and approval policy, its own fail-closed contract must report UNKNOWN / INSUFFICIENT_EVIDENCE, not REVIEW_READY or HUMAN_GATE. A digest that simply repeats these native facts has NO DEMONSTRATED incremental decision value in this observed case.
Additional GitHub caution: required checks may apply to the test merge commit, not just the head; https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks

## Competitive falsification disposition
- Narrow 'summarize native PR checks/reviews' variant: REJECT_AS_DIFFERENTIATOR for this case.
- Broader 'zero-migration recovery from fragmented, cross-tool, independently linked receipts': UNTESTED; not killed by a non-stalled negative control.
- Next highest-commercial-information-gain experiment: locate a lawfully accessible real stalled agent-initiated PR with independent receipts and a genuinely ambiguous safe next action. First document native baseline and all provenance; run existing classifier only if exact policy evidence exists. If the extra inference cannot change a safe decision or requires intrusive setup, KILL/REFINE before feature work.
- No verified buyer pain, external demand, WTP, matched comparable, savings, ROI, revenue or customer outcome.
