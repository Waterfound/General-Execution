# RMA-DIST-001 — Offline distribution and monetization candidate

**STATUS: ISOLATED MOCK CANDIDATE ONLY. NOT A PRODUCT, PAYMENT PROCESSOR, OR SERVICE.**

Directly depends on existing WRM commercial evidence and the Commercial Progress Ratchet candidate in General Execution PR #48. It does *not* replace ratchet selection, create a new System, bind a recurring owner, deploy, or choose a commercial wedge.

## Scope

- `candidate.py`: provider-neutral **mock** subscription event projection and fail-closed entitlement gate; SQLite durable replay, duplicate event detection, ordering, reconciliation and manual local repair. No signature verifier or HTTP endpoint; cannot ingest production webhooks.
- Synthetic-only funnel: allowlisted stages and deterministic de-duplication. No real user IDs, IP addresses, cookies, referrers, email addresses, consent collection or marketing outreach.
- `simulated_economics`: isolated monthly steady-state USD assumptions and break-even arithmetic. Price is **not** selected and revenue is not measured.
- `run_rehearsal.py`: deterministic fixture run with fresh database and cold restart. It does **not** exercise a real recurrent owner, business, provider, customer, deployment or processor.
- No launch page: CR-001 has not validated a product/value claim; creating copy or a fake checkout would be misleading.

## Run with Python 3.10+ (zero external libraries)

```bash
cd experiments/wrm/distribution
python -W error::ResourceWarning -m unittest -v test_candidate.py
python run_rehearsal.py
```

## Explicit blockers

1. No validated buyer/WTP or differentiated product; ratchet commercial research remains higher priority than broad support infrastructure.
2. No compliant production hosting or approved checkout provider, seller identity, banking/KYC or commercial publication authority.
3. No real payment event signatures, verification against provider source, refunds/chargebacks, invoices/taxes, GDPR/LGPD lifecycle, refund policy, SLA, authenticated customer access, cancellation UX, incident escalation, fraud handling or true revenue reconciliation.
4. No mission-specific recurrent owner attestation or cold-restart production proof. SQLite synthetic replay is not unattended execution.

The mock uses a monotonically increasing synthetic revision that real processors do **not** necessarily provide. A future adapter must derive order from authenticated authoritative provider state and reconcile with provider APIs before production use. No projection may grant entitlement from unverified client-side or unauthenticated webhook events.

## Commercial Progress Ratchet contract (PR #48 candidate)

- `DIRECT_COMMERCIAL` research to identify a lawful, independently checkable job remains eligible and outranks `INTERNAL_SUPPORT`.
- This adapter can be considered `INTERNAL_SUPPORT` only when a **named missing commercial predicate** requires it; it is not a reason to freeze or launch a product.
- Distribution status is a sibling candidate record only. No shared state mutation, ratchet merge or canonical promotion.

## Privacy and authority

Mock-only synthetic identifiers prefixed `sim-`, offline SQLite temporary store, no network, no connectors, no real buyer data, no financial relationship. No secrets or private Systems topology. No automatic scheduled run.
