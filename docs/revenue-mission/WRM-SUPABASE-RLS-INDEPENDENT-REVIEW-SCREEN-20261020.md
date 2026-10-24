# WRM screen — independent Supabase RLS isolation review

**Screened:** 2026-10-20  
**Decision:** `REJECT_BEFORE_BUILD / DIFFERENTIATION_AND_ACCESS_FAIL`  
**Mission state:** `NO_PRODUCT_SELECTED` / revenue USD 0

## Narrow job considered

Produce an independent, version-bound release-gate report proving that a Postgres/Supabase multi-tenant application prevents cross-tenant read and write access.

## Buyer/problem evidence

The outcome is bought separately:

- An Upwork listing posted 2026-10-13 requests an independent Postgres/Supabase multi-tenant isolation review for USD 400 fixed price.
  - https://www.upwork.com/freelance-jobs/apply/Independent-Security-Reviewer-Postgres-Supabase-Multi-Tenant-Isolation_~022110101986016604654/
- A listing posted 2026-10-16 requests two security-review passes for a multi-tenant Next.js/Supabase SaaS, up to USD 2,300 fixed price.
  - https://www.upwork.com/freelance-jobs/apply/Security-review-multi-tenant-Next-Supabase-SaaS-two-short-passes-Dec-and-Feb_~022111318108844743446/
- Other current listings request independent Supabase RLS/payment review and tenant-isolation review inside regulated or sensitive SaaS work.
  - https://www.upwork.com/freelance-jobs/apply/Independent-security-payments-review-PostgreSQL-Supabase-RLS-Stripe-fixed-price_~022108759957105993149/

This establishes paid demand for the outcome. It does not establish demand for an autonomous report without recognized reviewer expertise or access to the real permission model.

## Substitute and differentiation screen

Primary/current sources:

- Supabase documents database tests, `supabase test db`, advanced pgTAP helpers and a worked multi-tenant RLS example.
  - https://supabase.com/docs/guides/database/postgres/row-level-security
  - https://supabase.com/docs/guides/local-development/testing/pgtap-extended
- Securify publishes a free, open-source, read-only scanner that discovers Supabase exposure and actively tests unauthorized read/write access, with severity and remediation output.
  - https://securifyai.co/supabase-rls-scanner-open-source-supabase-security-audit-tool/
- THE SWARM sells a EUR 1,500 fixed Supabase RLS audit covering every table/view/function, role-based API attack simulation, findings, corrected policies, automated tests and re-test.
  - https://theswarm.at/supabase-rls-audit/

Observed market boundary:

- machine checks and dynamic RLS replay are available free;
- commercial providers bundle human interpretation of the actual product permission model, private access, remediation, retest and accountability;
- no evidence establishes a Waterfound-specific advantage in certification, reputation, proprietary test coverage or privileged context;
- competing on lower price alone would not be a defensible differentiation.

## Access and truthfulness constraints

Representative value depends on some combination of:

- read-only private repository access;
- database schema and policy access;
- a Supabase project membership or staging environment;
- test identities for real roles;
- interpretation of the buyer's intended permission model;
- credible reviewer history and a report the buyer trusts.

Those inputs are legitimate customer/provider gates. A synthetic fixture could demonstrate generic capability but would not answer the missing commercial predicate, because official and free substitutes already demonstrate the same class of mechanics.

Waterfound must not imply certified penetration-testing status, prior client experience, independent human attestation or security assurance that has not been earned.

## Decision

`REJECT_BEFORE_BUILD / DIFFERENTIATION_AND_ACCESS_FAIL / NO_PRODUCT_SELECTED`.

No probe, product, proposal, outreach, pricing, account creation, credentials, customer data or publication is admitted. Revenue remains USD 0.

## Next admissible frontier

Continue buyer/problem discovery. Prefer a separable paid deliverable where:

1. the valued outcome is not primarily professional reputation or regulated attestation;
2. the first useful proof can be produced from public or synthetic data;
3. named free and commercial substitutes do not already cover the core predicate;
4. value can be measured before pricing or outreach.
