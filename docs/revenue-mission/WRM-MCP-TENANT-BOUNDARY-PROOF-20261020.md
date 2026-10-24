# WRM candidate — MCP tenant-boundary replay proof

**Observed and tested:** 2026-10-20  
**Candidate state:** `CANDIDATE_KILLED / BROAD_PENTEST_SUBSTITUTE_CONFIRMED / CAPABILITY_SUPPORT_ONLY`  
**Mission state:** `NO_PRODUCT_SELECTED` / revenue USD 0

## Narrow job to be done

Before deploying a remote multi-tenant MCP server, produce deterministic evidence that:

1. a principal bound to tenant A cannot read tenant B's resources by changing tool arguments; and
2. a destructive tool fails closed unless both permission and an exact action approval are present in authenticated server-side context.

This is narrower than building, scanning, or governing an MCP platform. It is an executable boundary proof for one high-cost failure class.

## Buyer/problem evidence

Public marketplace demand repeatedly includes this exact risk inside larger implementation engagements:

- A current QuickBooks Online MCP project requires OAuth, multi-company switching, strict company isolation, read/write permissions, audit logging, and safeguards for destructive actions. Budget: USD 750–1,500; 139 proposals; now in progress/awarded.
  - https://www.freelancer.com/projects/typescript/quickbooks-online-mcp-server-development
- A current Senior AI Agent Engineer listing explicitly includes tenant-isolation testing, failure recovery, timeout handling, and retry behavior.
  - https://www.upwork.com/freelance-jobs/apply/Senior-Agent-Engineer_~022101132790930983210/
- A separate MCP dataset-server buyer requires authentication, permissions, and tenant isolation.
  - https://www.upwork.com/freelance-jobs/apply/Build-MCP-server-for-some-data-sets_~022102156808568493227/
- A recent ASP.NET MCP buyer asks candidates to explain security, endpoint testing, success criteria, latency, throughput, and error-rate proof.
  - https://www.freelancer.com/projects/dot-net-core/backend-net-integration

This proves demand for the outcome inside full implementation work. It does **not** yet prove demand or WTP for a standalone evidence pack.

## Substitute screen

Primary/official sources:

- MCP authorization guidance:
  https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/authorization
- MCP Inspector recipes:
  https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector/recipes
- Snyk Agent Scan:
  https://github.com/snyk/agent-scan
- Invariant/Snyk issue-code reference:
  https://github.com/invariantlabs-ai/docs/blob/main/docs/mcp-scan/issue-code-reference.md

Observed substitute coverage:

- official MCP guidance explains OAuth 2.1 authorization design;
- MCP Inspector exercises connectivity and protocol interactions;
- Agent Scan / mcp-scan focus on prompt injection, tool poisoning, tool shadowing, toxic flows, and agent-component supply-chain risks.

The reviewed substitutes do not establish the same predicate: dynamically replaying authenticated contexts to prove tenant isolation and exact destructive-action authorization at invocation time.

**Differentiation was falsified on 2026-10-20.** Appsecco sells standalone MCP server security assessments that explicitly test adversarial access boundaries, tool-parameter manipulation, authentication/authorization, and multi-tenant isolation, with reproduction evidence and retesting. Its public fixed-price bands are USD 3,500–5,000 for a single MCP server, USD 7,500–12,500 for 2–5 servers, and USD 15,000+ for enterprise multi-tenant scope. This is a direct commercial substitute for the broader outcome, while the marketplace evidence above continues to bundle the narrow invariant into implementation work rather than buying it alone.

Primary sources:

- https://appsecco.com/ai-security/mcp-pentesting
- https://appsecco.com/pricing
- https://github.com/appsecco/pentesting-mcp-servers-checklist
- https://arxiv.org/abs/2609.14780

## Smallest proof

Artifact:

- `docs/revenue-mission/proofs/mcp-tenant-boundary-probe.py`

The standard-library-only probe compares:

- a vulnerable adapter that trusts client-supplied tenant identifiers and treats delete permission as implicit; and
- a hardened adapter that binds tenant scope to authenticated server context and requires exact destructive-action approval.

Scenarios:

| Scenario | Expected |
|---|---|
| Same-tenant authorized read | allow |
| Cross-tenant read by changed argument | deny |
| Destructive action without exact approval | deny |
| Destructive action with permission and exact approval | allow |

Execution:

`python3 docs/revenue-mission/proofs/mcp-tenant-boundary-probe.py`

Observed result:

- vulnerable adapter: 2/4 passed;
- detected: `cross_tenant_read`, `unconfirmed_destructive_action`;
- hardened adapter: 4/4 passed;
- process exit: 0.

## Evidence classification

| Category | Result |
|---|---|
| Capability | Synthetic deterministic replay detects the two named boundary failures |
| Observed outcome | Vulnerable fixture failed 2/4; hardened fixture passed 4/4 |
| Competitive differentiation | Falsified against an established standalone MCP pentest service covering access boundaries, parameter abuse, auth and multi-tenant isolation |
| Demand evidence | Multiple buyers explicitly require tenant isolation and destructive-action safeguards inside larger builds |
| WTP | Real public pricing exists for broad MCP pentesting; no evidence that buyers purchase the narrow replay proof alone |
| ROI | Unmeasured |
| Revenue | USD 0 |

## What this does not prove

- no real MCP server was assessed;
- no real tenant data or credentials were used;
- no buyer has requested, tried, or paid for the proof;
- no operator-hours, incident reduction, or monetary risk reduction is claimed;
- the fixture is not a penetration test, certification, compliance attestation, or security guarantee.

## Kill criteria

Close the candidate if any of the following is established:

1. maintained substitutes already perform equivalent context-bound cross-tenant and destructive-action replay with useful evidence output;
2. bounded buyer research finds only demand bundled into full implementation or broad penetration testing, with no willingness to try a standalone proof;
3. representative testing requires privileged customer data or credentials before value can be demonstrated;
4. the proof cannot be adapted to a public/synthetic MCP fixture without product-specific implementation work;
5. evidence quality depends on model self-report rather than objective invocation traces and validators.

## Commercial decision — 2026-10-20

The candidate hits kill criteria 1 and 2:

1. an established provider sells the broader standalone outcome with explicit multi-tenant isolation, adversarial boundary testing, reproducible findings and retest;
2. bounded buyer evidence requests the narrow invariant inside full implementation work, not as a separately purchased proof.

Decision: `CANDIDATE_KILLED / NO_PRODUCT_SELECTED`.

The synthetic probe remains a truthful `SUPPORT_ONLY` capability. No public-fixture expansion, productization, pricing, outreach, proposal, account creation, credential use or publication is admitted. Revenue remains USD 0.

## Next admissible frontier

Return to buyer/problem discovery and reject the first failed commercial predicate before code. Prefer a job with direct evidence of a separable paid deliverable, a reachable payout path, and a differentiation claim that survives named substitutes.
