# WRM Commercial Discovery — external competitive substitution and product wedge
Date: 2026-10-10. Status: RESEARCH_CANDIDATE / NO_CUSTOMER_VALIDATION.

## Market evidence (public vendor primary sources)
1. GitLab AI Governance supports AI-agent session monitoring, audit events and Allow/Ask/Deny tool policies across GitLab Duo and external MCP-connected agents. Source: https://docs.gitlab.com/user/ai-governance/ (observed 2026-10-10). **Implication:** generic agent governance/audit is already a native incumbent feature; a generic dashboard is an unattractive first wedge.
2. GitLab's composite identity ties a service account and initiating human, preserving attribution and effective permission boundaries. Source: https://gitlab.com/gitlab-org/gitlab/-/blob/master/doc/user/duo_agent_platform/composite_identity.md (observed 2026-10-10). **Implication:** basic attribution and approval-policy language cannot be claimed unique.
3. CodeRabbit markets PR reviews, agent loops, multi-repo checks, architectural analysis and enterprise audit logging. Published annual-billing prices are $24/$48/$72 per developer-month across Essentials/Team/Advanced; on-demand agent run advertised $0.40 per agent-minute. Source: https://www.coderabbit.ai/pricing (observed 2026-10-10). **Implication:** buyers can already pay for adjacent PR automation; these are competitor list prices, NOT WRM willingness-to-pay or a price recommendation.
4. GitLab Duo Agent Platform already offers governed development workflows and visibility. Source: https://about.gitlab.com/press/releases/2026-01-15-gitlab-announces-duo-agent-platform-general-availability/ (observed 2026-10-10).

## Buyer/problem hypotheses — NOT interviews or validated pain
Candidate buyer: engineering lead at 5–50 developer teams running coding agents across PRs and CI. Candidate job: 'tell me which agent-initiated PRs are blocked, why, what proof exists, and what requires my approval, without granting an agent extra authority'. Trigger: growing PR automation with fragmented tool receipts. Substitute: GitHub/GitLab native PR and CI views, GitLab Duo, CodeRabbit, internal scripts. Budget owner, urgency, switching cost and WTP all UNKNOWN.

## Narrow product wedge: Agent PR Recovery & Approval Ledger
Read-only GitHub-first, single-repository, no agent orchestration required for v0:
- Input: existing GitHub PR metadata, check runs, immutable workflow receipts, authorized approval requirements.
- Output: one verifiable 'PR blocked / recoverable / needs human / insufficient evidence' digest with exact evidence links and next safe action.
- Explicit unknown when evidence absent; never claim saved hours, replaced reviews or risk eliminated.
- Self-service acceptance: least-privilege installation or token path only after authorization; isolated repo namespace; zero write permission in first release.
- Distinctiveness to test: cross-tool interruption recovery + explainable authority stops, not generic AI code review or governance dashboards.
- Kill criteria: native GitLab/GitHub/CodeRabbit already satisfy target workflow with negligible friction; customers do not experience repeat interruption/approval pain; evidence collection requires onerous onboarding; recurring cost exceeds proven willingness-to-pay.
- Do not build paid SaaS or announce differentiation before external validation.

## Evidence ladder and status
Capability: VERIFIED for core durable/host tests (not a customer outcome).
Real observed pilot: PARTIAL, admission pending exact receipt audit.
Matched comparable: NONE VERIFIED.
Buyer interviews: NONE.
WTP: NONE.
Revenue: NONE.
Suggested next machine-admissible step: produce a real PR #38 lifecycle evidence dossier from exact GitHub receipts and a read-only v0 CLI prototype that outputs a verifiable approval/recovery ledger for one public test fixture; never confuse fixture with customer demand.

## Governance
This file is research, not a marketing page, external outreach, deployment, merge, pricing approval, paid spend, provider change, or authority delegation. One Machine / Full Autonomy objective remains, with actual market falsification prioritized over more internal orchestration.
