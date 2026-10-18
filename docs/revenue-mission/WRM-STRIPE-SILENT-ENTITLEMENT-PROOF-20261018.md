# WRM — Stripe silent-entitlement proof — 2026-10-18

## Decision

`PUBLIC_PROOF_PASSED / CANDIDATE_NOT_SELECTED / EXTERNAL_VALUE_UNPROVEN`

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

## Evidence classification

| Predicate | Status |
|---|---|
| Technical capability | Proven on one public, source-pinned fixture. |
| Material issue | Code-level paid-access divergence path proven; real-world occurrence unproven. |
| Buyer/problem evidence | Repeated jobs and existing paid service offers. |
| Differentiation | Unknown; existing billing-health-check services are direct substitutes. |
| Human time / revenue saved | Unknown. |
| WTT / WTP for Waterfound | Unknown. |
| Revenue | USD 0. |

## Kill and advance criteria

Advance only if additional independent public fixtures show the same failure class and the bounded detector finds it with low preparation burden, or a buyer-authorized validation opportunity appears.

Kill if existing Stripe health checks or static analyzers provide the same source-linked finding; if the finding requires extensive manual interpretation; if the dominant buyer need is remediation rather than diagnosis; or if no willingness-to-try signal appears after an authorized opportunity.

## Current consequence

Do not build UI, integrations, pricing, outreach, or publication. The next admissible step is substitute falsification and a second independent public-fixture test, not expansion.
