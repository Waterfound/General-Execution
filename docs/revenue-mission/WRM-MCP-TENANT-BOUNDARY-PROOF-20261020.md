# WRM candidate — MCP tenant-boundary replay proof

**Observed and tested:** 2026-10-20  
**Candidate state:** `NARROW_PROOF_PASSED / DEMAND_FOR_STANDALONE_PROOF_UNVALIDATED`  
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

**Differentiation remains provisional.** A broader substitute or commercial penetration-testing service may already provide equivalent tests; this must be falsified before expansion.

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
| Competitive differentiation | Provisional gap versus reviewed static/injection-oriented scanners |
| Demand evidence | Multiple buyers explicitly require tenant isolation and destructive-action safeguards inside larger builds |
| WTP | Budgets observed for full implementation only; standalone proof WTP unknown |
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

## Next admissible frontier

Before adding features, test only these commercial predicates:

1. Is the tenant-boundary proof purchased or requested as a separable pre-deployment/release-gate deliverable?
2. Do established MCP security services already sell this exact dynamic invariant?
3. Can one public MCP fixture be assessed read-only with objective traces without account, credential, or external write access?

No outreach, proposal, account creation, publication, or pricing is authorized by this dossier.
