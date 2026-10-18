# WRM — Pre-build decision-gap proof — 2026-10-18

## Decision

`NARROW_PROOF_PASSED / CANDIDATE_NOT_SELECTED / EXTERNAL_VALUE_UNPROVEN`

## Narrow job-to-be-done

Before development begins, reconcile structured business rules, design claims, workflows, permissions, and explicit product decisions; return source-linked blockers and unresolved decisions without inventing business rules.

This is narrower than a generic architecture review and excludes implementation, cloud configuration, security certification, pricing, estimation, and remediation.

## Buyer evidence

- [Fotografieagenda independent architecture review](https://www.upwork.com/freelance-jobs/apply/Independent-Technical-Architecture-Review-Fotografieagenda_~022110805667539158282/): USD 100 fixed price for concise independent analysis.
- [Medidocta pre-development technical review](https://www.freelancer.hk/projects/api-developmet/technical-architecture-review-mvp): open, payment-verified, CAD 500 maximum; asks for Figma gap severity, architecture, ERD, RBAC/resource scope, booking concurrency, API map, security/operations, and a decision register.
- [SaaS development technical supervision](https://www.freelancer.com/job-search/airline-reviews/): independent review of architecture, repository, database, scalability, security, delivery progress, and written recommendations.

These buyers establish repeated demand for independent pre-build or in-flight technical review. They do not establish demand or WTP for this exact automated subjob.

## Substitute boundary

- AWS Well-Architected and Azure Well-Architected provide structured cloud workload assessments and risk guidance.
- Figma Dev Mode exposes design properties, code snippets, assets, and handoff state.
- Eraser produces design documents and codebase/architecture diagrams.

The sources reviewed do not establish native reconciliation of contradictory business rules, design claims, workflows, RBAC grants, and explicit decision gaps into one evidence-linked register. This is the tested difference.

## Smallest read-only proof

Artifacts:

- `scripts/revenue_mission/prebuild_decision_gap_probe.py`
- `tests/fixtures/prebuild_decision_gap_fixture.json`
- `tests/test_prebuild_decision_gap_probe.py`
- `docs/revenue-mission/evidence/prebuild_decision_gap_output.json`

Synthetic fixture only; no customer data, credentials, account, publication, or paid tool.

Observed outcome:

| Result | Count |
|---|---:|
| Cross-artifact contradiction | 1 BLOCKER |
| Workflow/RBAC gaps | 2 BLOCKER |
| Product decision required | 1 HIGH |
| Total findings | 4 |

Verification:

- unit test: PASS (1/1);
- repeated execution output SHA-256: `44fc14be27f5e7602182c4d7d781c380c9f3001ffc0f0bdbd869d5be8c53a200` in both runs;
- read-only flag: true.

## Evidence classification

| Predicate | Status |
|---|---|
| Technical capability | Proven on one synthetic structured fixture. |
| Observed customer value | Unknown. |
| Human active minutes saved | Unknown; not measured. |
| Avoidable rework prevented | Unknown; no counterfactual. |
| Differentiation | Narrow and plausible; not yet validated against buyer workflow. |
| Demand | Repeated for broad independent architecture review. |
| WTT/WTP for exact proof | Unknown. |
| Revenue | USD 0. |

## Kill and advance criteria

Advance only if a buyer-authorized or public representative fixture can be evaluated and at least one expert review confirms that the register found a material issue they would otherwise need to discover manually.

Kill if:

- structured artifact preparation consumes more effort than the review saves;
- an incumbent produces the same cross-artifact decision register;
- findings are mostly false positives or restatements;
- buyers require continuous meetings, private access, estimates, and implementation rather than the bounded register;
- no willingness-to-try signal appears after an authorized external validation opportunity.

## Current consequence

Do not expand the probe, build UI, add integrations, set pricing, contact buyers, or publish an offer. Preserve as a candidate proof while the next admissible frontier tests external value or finds a stronger buyer job.
