# WRM AI Web Code Audit — Proposal-Ready Packet — 2026-10-20

## Status

**State:** `MACHINE_PREPARED / EXTERNAL_APPLICATION_NOT_AUTHORIZED`

Target listing:

- https://www.upwork.com/freelance-jobs/apply/Web-Developer-for-Code-Audit_~022102608080165544228/
- Public range: USD 15–25/hour
- Worldwide; intermediate; one-time; under 30 hours/week; under one month

Supporting public proof:

- https://github.com/Waterfound/General-Execution/blob/wrm/wrm-commercial-discovery-20261010/docs/revenue-mission/WRM-AI-WEB-CODE-AUDIT-PROOF-20261020.md
- Source fixture pinned at `43123d6840316ec946b43ed0b6ee6894cc7c3c4e`

No proposal has been sent. The text below is a factual draft, not authorization to communicate externally.

## Proposal draft

Hello,

I can deliver the narrow audit you described: 3–5 demonstrable findings tied to exact code, explained in plain English, with practical fixes and a verification step for each one.

My review method is evidence-first:

- pin the sample to an immutable commit;
- run TypeScript/lint/build and dependency checks where available;
- inspect accessibility with the accessibility tree, axe-style checks, and keyboard paths;
- test API and failure behavior with malformed, failed, and stalled responses;
- separate confirmed findings from hypotheses;
- rank only issues that can be reproduced or directly demonstrated.

As a directly relevant public sample, I reviewed a Lovable-generated React/Vite project at an immutable commit and identified five code-linked issues:

1. country cards that cannot be activated by keyboard;
2. search and icon-only refresh controls without durable accessible names;
3. external API responses trusted without runtime validation;
4. a primary-data failure path that becomes an indistinguishable “0 of 0” state with no retry;
5. unbounded fetch lifecycles while an installed query layer is bypassed.

For each finding, the sample includes impact, a practical fix, and a verification test. I deliberately did not label any observation a security vulnerability when the inspected public surface did not support that conclusion.

Public sample:
https://github.com/Waterfound/General-Execution/blob/wrm/wrm-commercial-discovery-20261010/docs/revenue-mission/WRM-AI-WEB-CODE-AUDIT-PROOF-20261020.md

For your project, I would use the same format:

- immutable source/version reference;
- 3–5 strongest findings across performance, security, accessibility, maintainability, and production readiness;
- exact file/code evidence;
- plain-English consequence;
- recommended fix;
- verification criteria;
- explicit unknowns and exclusions.

Provider-specific information that must be supplied truthfully before submission:

- **Identity/account:** [authorized provider or agency identity]
- **Relevant experience:** [only verifiable AI-assisted development/review experience]
- **Availability:** [truthful hours and dates]
- **Hourly rate:** [authorized value within or consistent with the buyer's posted range]

Regards,  
[authorized provider identity]

## Buyer questions — prepared answers

### Tools

Repository pinning, TypeScript compiler, ESLint, dependency/build inspection, browser accessibility tree, axe-style automated checks, keyboard-only interaction tests, targeted unit/integration tests, mocked network failures, response-schema validation, and manual review of trust boundaries and failure semantics.

Tools are selected only where they answer a named predicate. Automated output is treated as a lead; the final report includes only findings tied to exact code and a reproducible impact.

### AI-assisted development experience

Use only one of the following truthful forms:

**Agency/entity form, if the marketplace account and representation permit it:**

> Waterfound operates evidence-first governed software workflows covering repository review, CI/release controls, provenance, recovery, idempotence, and authority boundaries. The linked public sample is the closest direct artifact for this engagement.

**Named-person form:**

> [Insert only the named provider's verifiable experience. Do not convert Waterfound rehearsals into personal years, client history, certifications, or employment.]

If neither form is permitted or supportable, do not submit.

## Proposed delivery contract

A safe first milestone should specify:

- one public or access-controlled repository;
- one immutable commit SHA;
- no production write access;
- 3–5 findings maximum;
- evidence, impact, fix, and verification for each;
- no remediation implementation unless separately funded;
- no penetration testing or compliance certification;
- buyer secrets and customer data excluded from the report;
- funded hourly protection or milestone before buyer-specific work.

## Submission checks

Submit only if all are true:

- [ ] Listing is open.
- [ ] Client payment protection is active.
- [ ] Authorized provider identity exists and may use the account.
- [ ] Experience statement is truthful and verifiable.
- [ ] Availability is accurate.
- [ ] Rate is explicitly authorized.
- [ ] Required Connects or other paid marketplace cost is authorized.
- [ ] The public proof may be linked externally.
- [ ] No free bespoke production work is requested.
- [ ] Private access will be least-privilege and separately approved.

## Non-claims

The proposal must not claim:

- eight or any other number of professional years without human evidence;
- prior external clients, paid audits, certifications, or customer outcomes;
- guaranteed security, compliance, defect prevention, ROI, or savings;
- access to private systems not yet granted;
- revenue before a protected payment is actually received.
