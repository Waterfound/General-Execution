# WRM-T1 — Wedge refinement after substitution falsification

Status: **HYPOTHESIS ONLY / NOT PRODUCT SCOPE**  
Date: **2026-10-10**

Commercial Progress Ratchet applied: the generic “agent governance/control-plane/dashboard” wedge is too crowded to justify implementation expansion.

Observed substitutes already cover large portions of:
- agent session dashboards and logs;
- multi-agent monitoring;
- tool approvals and Allow/Ask/Deny policy;
- authority and evidence;
- workflow state and PR routing;
- recovery/closure;
- read-only multi-agent event aggregation.

Therefore WRM-T1 must not compete by adding another generic dashboard.

## Narrower job to falsify

**Zero-migration Agent PR Recovery Digest**

For a team that already uses heterogeneous coding agents, answer from read-only repository evidence:

1. Why is this agent-created PR stalled?
2. Is it recoverable without widening authority?
3. What exact evidence is missing?
4. Does the next step require machine action, a condition wait, or genuine human authority?
5. What is the smallest safe next action?

The candidate distinction is **zero-migration forensic recovery**, not orchestration. The user should not have to move their agents into a new control plane before obtaining value.

This remains unvalidated. It becomes buildable product scope only if the gap survives substitution testing and the smallest classifier proof demonstrates information not already available with negligible friction from incumbent views.

## Explicit non-goals

- no dashboard;
- no agent launcher;
- no replacement for GitHub/GitLab;
- no generic approval inbox;
- no write permissions in the first proof;
- no claims of saved hours, ROI, safety improvement, WTP or demand before evidence.

## Next discriminator

Freeze a small classification contract for one fixture PR and compare:
- native GitHub-visible facts;
- candidate recovery classification;
- incumbent/substitute output where available.

If the candidate does not add a materially clearer and verifiable next-action diagnosis, kill the wedge before further implementation.
