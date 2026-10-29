# WRM-T1 — pr-shepherd direct-substitute falsification (2026-10-11)

**Classification:** source-verified competitive research; candidate evidence only. **No customer validation, competitor installation, paid access, customer contact or product release.**

## Why this changes the commercial decision
The prior matrix considered GitHub, GitLab, Agentplane, AgentHUD, ADHDev and CodeRabbit. A further **direct, free/open-source** substitute was found: `jonathanong/pr-shepherd`. Its public primary-source specification substantially overlaps the proposed *Zero-migration Agent PR Recovery Digest*, including the claimed differentiator of deriving the smallest next action from an existing GitHub PR without first migrating into a control plane.

Source snapshots inspected on 2026-10-11:
- https://github.com/jonathanong/pr-shepherd/blob/main/README.md
- https://github.com/jonathanong/pr-shepherd/blob/main/docs/features.md
- https://github.com/jonathanong/pr-shepherd/blob/main/docs/authentication.md
- https://github.com/jonathanong/pr-shepherd/blob/main/docs/escalations.md
- https://github.com/jonathanong/pr-shepherd/blob/main/docs/rest.md
- https://github.com/jonathanong/pr-shepherd/blob/main/docs/comparison.md

## Primary-source overlap / distinction

| Commercial job | Observed pr-shepherd capability | WRM hypothesis implication |
| --- | --- | --- |
| Use existing PR without workflow migration | CLI and MCP accept GitHub PR URL / owner-repo number, query native GitHub state | **Generic zero-migration claim is not unique.** |
| Identify why a PR is waiting | Fetches checks, reviews, threads, mergeability, requirements, and CI job/step excerpts when available | **Generic stalled-PR summary is already served.** |
| Derive smallest next action | Emits deterministic WAIT, FIX_CODE, MARK_READY, MERGE, CANCEL or ESCALATE with bounded instructions | **Actionable digest is not unique.** |
| Recognize human-only blockers | Explicit escalation taxonomy including missing permissions, startup failures, stalled waits and missing required checks | **Human-gate labeling is not unique.** |
| Agent/provider independence | Designed for Claude Code, Codex, Grok and other callers | **Heterogeneous coding-agent support is not unique.** |
| Read-only initial value | `iterate` gathers information, but its full documented workflow requires an authenticated token with Pull requests and Issues read/write, and optional mutating `apply` | **Possible residual gap:** a strictly no-write-permission, no-install, public-PR forensic view; demand and safety are unproven. |
| Cross-provider durable receipts / external run attestations | Docs focus on GitHub PR context; no general independent off-GitHub execution-evidence reconciliation was verified in the inspected docs | **Possible residual gap**, not proof of absence or buyer need. |

Important epistemic limits: the competitor's source and docs were read, but its executable was **not installed or run** here. Documented behavior is not independently benchmarked. A requirement for a token in the competitor's documented full workflow does not establish that a buyer values avoiding token setup, and public PRs alone may not expose enough information for a safe diagnosis.

## Additional real non-stalled control
- Agent-authored pr-shepherd PR #559 explicitly says it was generated with Claude Code: https://github.com/jonathanong/pr-shepherd/pull/559
- Exact observed head: `ea54b14cb92d1e6064ee502977b056c59a0b4d40`.
- GitHub Actions `CI` run `38114258474` was `in_progress`; `Labeler` run `38114258372` completed `success` at observation.
- Safe next action from these **limited** observations is to wait for current CI and obtain authoritative rules/reviews before any readiness claim. This is visible natively and already within pr-shepherd's documented WAIT behavior. It is **not** evidence of a genuinely stalled PR, no competitor-output parity test, and no WRM differentiation proof.

## Falsification / ratchet decision
- `GENERIC_ZERO_MIGRATION_PR_STATUS_AND_NEXT_ACTION_DIGEST`: **KILL_AS_PRIMARY_DIFFERENTIATOR** based on direct documented substitution, unless an independent comparison later reveals material gaps.
- `READ_ONLY_NO_WRITE_PERMISSION_PUBLIC_PR_FORENSICS`: **HYPOTHESIS_ONLY**. Need evidence that teams accept public-only limited context, that outputs change decisions, and that low-friction distribution yields demand.
- `CROSS_PROVIDER_EXECUTION_CLAIM_VS_EVIDENCE_RECONCILIATION`: **HYPOTHESIS_ONLY**. Must first identify a specific buyer/problem and lawful independent receipts, then prove a safe inference that native PR and pr-shepherd cannot already make. Do not silently rename the same crowded product.
- `VERTICAL_WORKFLOW_AUTOMATION` and `SPECIALIZED_OPERATIONAL_INTELLIGENCE`: **REOPEN COMMERCIAL DISCOVERY** as alternatives under WRM Market Thesis Tournament PR #47. Buyers and workflows remain unselected; no claims of market attractiveness.

## Next machine-admissible action
**Buyer/problem evidence** now outranks any further PR-ledger implementation: source independent, first-hand descriptions of costly recurring post-agent failure/recovery problems and compare with vertical workflow / intelligence opportunities. If no specific underserved payer/problem emerges, kill the entire PR recovery wedge and redirect to another opportunity. Do not build another dashboard, install a provider, contact customers, claim WTP, invent ROI or widen credentials. Retain existing classifier only as a reusable technical experiment.

Commercial acceptance deltas: competitor coverage increased by one high-overlap direct substitute; generic wedge demoted; no buyer, WTP, revenue, ROI or product superiority demonstrated. No authority created.
