# WRM — Stripe silent-entitlement proof — 2026-10-18

## Decision

`CANDIDATE_KILLED / DIRECT_SUBSTITUTE_CONFIRMED / CAPABILITY_SUPPORT_ONLY / NO_PRODUCT_SELECTED`

## Narrow job-to-be-done

Before launch, identify Stripe webhook paths where a paid-access mutation can affect zero application users while the endpoint still acknowledges successful delivery, leaving billing and access state silently divergent.

This excludes implementation, credentialed Stripe inspection, live payment testing, remediation, and broad security review.

## Buyer evidence

- Upwork's **Subscription Provisioning Repair** listing estimates 10–20 hours and explicitly asks how the provider would handle identity mismatches between billing and entitlement systems.
- A separate Upwork pre-launch review asks for Stripe webhook checks for missed or duplicate events and a written severity-ranked report.
- Upwork contains existing fixed-scope offers for Stripe billing health checks and silent billing/access-state failure audits.

This establishes a repeated paid problem and an existing service category. It does not establish willingness to try or pay Waterfound.

## Public representative fixture

Repository: `RyanAbir/saas-billing-starter` at exact commit `6c851ae68489d367c71c37af03ebc1dcf22c4888`.

The README identifies Stripe test mode. The public code was read without credentials or mutation.

Observed source path:

1. `updateUserByStripeIdentity` returns `0` when neither Stripe customer ID nor user ID matches.
2. `handleCheckoutSessionCompleted` and `handleSubscriptionUpdated` return that zero count without raising an error.
3. The webhook route returns `NextResponse.json(...)` with the default HTTP 200 for both paths.
4. No durable retry queue is present in the inspected repository tree.

Stripe's official webhook documentation states that HTTP 200 indicates successful delivery. Therefore, the bounded code-level consequence is that Stripe can record delivery as successful while application access remains unchanged.

This is not evidence that a real customer paid, that money was lost, or that the public project is deployed in production.

## Proof result

The deterministic probe flags two `BLOCKER` paths:

- `checkout.session.completed`;
- `customer.subscription.updated`.

The negative control adds a durable retry queue to both structured paths and produces zero findings.

Verification: 2/2 unit tests pass; repeated output SHA-256 is `cfa9f67f2264484732bbb124c10c32d2dfc72ed6ab3bfbf69e5c1eb2e256594b`.

Sources:

- [public repository](https://github.com/RyanAbir/saas-billing-starter/tree/6c851ae68489d367c71c37af03ebc1dcf22c4888)
- [Stripe webhook handling](https://docs.stripe.com/webhooks)
- [subscription provisioning repair buyer](https://www.upwork.com/freelance-jobs/apply/Backend-Developer-Subscription-Provisioning-Repair_~022109677926557203542/)
- [pre-launch Stripe review buyer](https://www.upwork.com/freelance-jobs/apply/Pre-launch-security-review-Supabase-Next-Stripe_~022097269113797358975/)
- [billing health-check substitute](https://www.upwork.com/services/product/development-it-a-stripe-and-subscription-billing-health-check-of-your-saas-2095573148150399838)

## Independent public-fixture replication

Repository: `SummonIQ/tuniq` at exact commit `6eff1b2e529a3ef3561a1942db7ae7b1d6e0a643`.

The complete public tree contained no separate queue, worker, retry, or dead-letter implementation. Its Stripe route exposed three independently checkable paths that can acknowledge HTTP 200 with no access-state mutation:

- `checkout.session.completed` skips its mutation block when any required identity field is absent;
- `customer.subscription.updated` does not treat zero matched users as an error;
- `customer.subscription.deleted` does not treat zero matched users as an error.

The same probe flags all three paths. The expanded suite passes 3/3 tests, including the first fixture and its negative control. Repeated second-fixture output SHA-256 is `dddcd886386e5e91d6d8f4de70be1bb32827674d62594e166cc03c55f9d8a3ff`.

This replication establishes a reusable technical detector shape across two source-pinned public repositories. It does not establish production occurrence, customer harm, or commercial value.

## Substitute falsification

The product boundary is not commercially distinct:

- an Upwork Stripe/subscription health check already covers checkout, lifecycle, webhooks, idempotency, entitlements, failed payments, plan changes, and the code granting or revoking access; it delivers a prioritized report without implementation or live-charge testing for USD 695–2,995;
- another Upwork no-write billing/webhook audit explicitly covers silent access drift, missed retries, stale subscription status, paid users blocked, evidence packets, and safe fix paths for USD 149–899;
- AxonBuild publishes the exact diagnostic mechanism: a Stripe webhook can return 200 while the database remains unchanged, including identity mappings that match no user.

These are direct substitutes for the outcome tested here. A smaller automated report would be a delivery-method or price difference; no buyer evidence shows it is a sharper unresolved job.

## Evidence classification

| Predicate | Status |
|---|---|
| Technical capability | Proven on one public, source-pinned fixture. |
| Material issue | Code-level paid-access divergence path proven; real-world occurrence unproven. |
| Buyer/problem evidence | Repeated jobs and existing paid service offers. |
| Differentiation | Falsified; direct no-write billing/access-drift substitutes exist. |
| Human time / revenue saved | Unknown. |
| WTT / WTP for Waterfound | Unknown. |
| Revenue | USD 0. |

## Kill and advance criteria

The technical advance criterion was met on a second fixture, but the commercial kill criterion was also met by direct substitutes. Reopen only on independent evidence of demand for an automated source-only product that incumbent audits do not satisfy.

## Current consequence

Close the candidate. Preserve the probe and both public-fixture outputs only as `SUPPORT_ONLY` capability. Do not build UI, integrations, pricing, outreach, or publication. Continue commercial discovery toward an outcome with direct buyer evidence and material differentiation.
