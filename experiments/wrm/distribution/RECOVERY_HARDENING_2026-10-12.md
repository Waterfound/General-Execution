# RMA-DIST-001 — isolated red/green recovery hardening (candidate)

**Scope:** stacked, reversible candidate on GE PR #54's exact commit `c7dfb23eaa236c38822d5879fe18f7eb91df0642`. Does not alter PR #46/48, shared ratchet, production, credentials, financial providers or runtime. Zero actual customers/payments/revenue.

## Reconciled predecessor
- GE PR #54: `candidate/rma-dist-001-20261012`, 24 previously passing local tests and synthetic rehearsal; no external CI certification.
- GE PR #46: product not frozen and actual buyer willingness-to-pay unknown; direct commercial research outranks further unsupported support engineering.
- GE PR #48: Commercial Progress Ratchet exists separately; no duplicated selector.
- Systems EP-FC-001 / UFP-001: static checkpoint + local restart is **not** recurring owner admission.

## Reproduced defects (RED)
Against PR #54's reconstructed local source + two new adversarial assertions:
1. A corrupted event for customer B caused `entitled(customer A)` to return false, despite A having an intact paid subscription. Cause: global reconciliation result was shared across all customers.
2. `reconcile(repair=True)` repaired corrupt projection, yet returned `healthy=false`, contradicting post-repair state.

**Red result:** 27 tests run, two expected failures, retained in the local `red.log`. The other three new assertions passed against predecessor.

## Minimal patch (GREEN)
- `reconcile(subscription_id=...)` checks one synthetic subscription only; global `reconcile()` retains portfolio-wide incident visibility.
- `entitled(sid)` reads subscription-scoped audit rather than blocking healthy customers on another's corruption.
- Explicit scope validation; scoped repair is forbidden to avoid unsafe partial repair. Only global, manual mock repair remains.
- Correct the repair receipt's `healthy` flag to describe the committed post-repair projection.
- No signature/authentication claims: SHA-256 event digests detect accidental modification in the synthetic ledger; they are **not** third-party origin authentication.

## Executed proof
```sh
cd experiments/wrm/distribution
python -W error::ResourceWarning -m unittest discover -p 'test*.py' -q
python run_rehearsal.py
```
Python 3.13.5; **34/34 tests PASS** (predecessor 24 + new recovery-hardening 5 + five local fixture assertions checked in separate worktree). The repository commit contains 24 predecessor tests + 5 in `test_recovery_hardening.py`; therefore **29 expected tests from this stacked PR's files**, not 34; 34 includes 5 additional standalone worktree-only assertions. These must be reported separately. On-branch regressions are to be re-run by the integration owner/CI. The isolated 128-seed deterministic permutation subtest includes duplicated webhook deliveries, cold SQLite reopen and final cancellation. A SQLite trigger induces a transactional abort and verifies no partial event insertion.

## Research verification
- GitHub paid Marketplace requires organization-owned verified publisher and >=100 GitHub App installs (or >=200 OAuth users): https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app
- Vercel Hobby is non-commercial: https://vercel.com/docs/limits/fair-use-guidelines
- GitHub Pages cannot host commercial SaaS / ecommerce storefront: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Cloudflare Pages Free documented 500 builds/month; production seller/terms/eligibility not established: https://developers.cloudflare.com/pages/platform/limits/
- Paddle base MoR headline 5% + USD 0.50 per checkout, and software-business restrictions: https://www.paddle.com/pricing ; https://www.paddle.com/help/start/intro-to-paddle/what-am-i-not-allowed-to-sell-on-paddle
- Stripe Brazil domestic-card headline 3.99% + BRL 0.39 (do not combine BRL fees with hypothetical USD economics): https://stripe.com/br/pricing

## Ratchet-facing disposition (no shared writer)
- `RMA_DIST_001_RESEARCH_VERIFIED`: source-backed channel screen; product-specific eligibility unverified.
- `RMA_DIST_001_ENGINEERING_VERIFIED`: LOCAL MOCK ONLY, source-bound regressions; not provider-verified.
- `RMA_DIST_001_FIRST_REVENUE_PATH_READY`: NOT MET — no product buyer proof, lawful production host/seller/processor binding, or real acquisition/activation.
- `RMA_DISTRIBUTION_OPERATIONAL_VERIFIED`: NOT MET — no recurrent owner proof, customer, charge, settlement or retained revenue.

## Remaining technical and authority gates
No external payment webhook signature verification, authoritative provider reconciliation, refunds/chargebacks, authenticated tenant identity, actual consent/cancellation UX, seller setup, lawful collection or GDPR/LGPD evidence. Do not bridge from this mock to production without complete separate authorization and proof. Existing commercial discovery work remains the next higher-gain admissible frontier. No scheduler/wake/owner admission occurred.
