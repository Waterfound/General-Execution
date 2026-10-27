# WRM — Agent402 paid-demand predicate reconciliation — 2026-10-27

Status: **COMMERCIAL_INFORMATION_GAIN_RESTORED / PAYMENT_ROUTE_DECLINED / NO_CHARGE / NO_PRODUCT_SELECTED / PASSIVE**

Observed Waterfound revenue: **USD 0**

## Correction

The 2026-10-26 Agent402 channel screen correctly classified a generic paid purchase as buyer-side rail validation, but it applied that conclusion too broadly to the already-authorized `demand-radar` product.

The authorized call is not a generic tool purchase. Its documented output is a ranked read of unmet discovery events and explicit tool requests recorded by Agent402. Therefore it can answer a currently missing commercial predicate: **which unresolved jobs have repeated independent demand signals inside this machine-buyer channel?**

This does not make the signal WTP. It does make the call commercially discriminating enough to justify the previously authorized one-time USD 0.005 spend once an already-funded, task-scoped payer is available.

## Exact admitted call

```text
GET https://agent402.tools/api/demand-radar?sort=count&limit=50&minCount=1&qualifiedOnly=true
```

Authority ceiling: exactly one successful charge, maximum **USD 0.005**.

The execution checkpoint at `WRM-DEMAND-RADAR-EXECUTION-CHECKPOINT-20261024.md` remains the controlling payment boundary. No wallet creation, funding, auto-reload, account installation, second call or unrelated credential use is admitted.

## Primary-source findings

Agent402's live tool documentation and pinned source identify two different half-cent products:

| Product | Commercial predicate | Output boundary | Authority |
| --- | --- | --- | --- |
| `demand-radar` | What agents requested or failed to find | ranked wish clusters, source mix, distinct callers, time span, qualification, explicit-request vs discoverability vs mixed, noise flag | one call already authorized |
| `bestsellers` | What outside wallets actually bought from the host | per-tool distinct buyers, sales, revenue, diversity, ticket, share and trend; internal canary traffic excluded | **not authorized** |

Primary sources:

- https://agent402.tools/tools/demand-radar
- https://agent402.tools/tools/bestsellers
- https://github.com/MikeyPetrillo/Agent402/blob/c6c4da497349bf1020c75f7632640bce8653d038/src/tools/x402-kit.js
- https://github.com/MikeyPetrillo/Agent402/blob/c6c4da497349bf1020c75f7632640bce8653d038/src/sales-ledger.js

The documented `demand-radar` qualification bar requires multiple day-scoped callers plus either more than one signal source or sufficient time span. Repeated submissions from one caller do not qualify. Each row distinguishes:

- `explicit-request`: agents proactively requested the capability;
- `discoverability`: searches missed, so the capability may already exist and need better retrieval rather than a new build;
- `mixed`: both signal classes;
- `noise`: obvious operator or CI traffic, flagged rather than silently removed.

That structure is materially better than an unqualified search-count feed. It can eliminate discoverability-only clusters, single-caller repetition and obvious tests before any build.

The separate `bestsellers` endpoint is stronger for paid job composition because it ranks external purchases by distinct wallets. Its product page explicitly says the free aggregate totals omit per-tool identities, and its source excludes internal canary/burner/heartbeat traffic. But it is a separate paid product and no authority exists to buy it.

## Why the authorized call now passes the information-gain test

The call can support a bounded selection decision without pricing claims:

1. **Close** every cluster classified only as discoverability when an adequate native or indexed substitute exists.
2. **Close** noise and unqualified clusters.
3. **Screen** qualified explicit-request or mixed clusters against public/native/free substitutes.
4. **Select at most one** cluster only if Waterfound can produce a lawful, read-only, source-pinned proof using public or synthetic fixtures.
5. **Kill** the selected cluster if a substitute meets the same acceptance predicate or the job requires outreach, private access, credentials, publication, payment handling, regulated assurance or unavailable human work.

The call still cannot establish:

- willingness to pay;
- completed external purchases for a returned cluster;
- Waterfound-specific willingness to try;
- sustainable price;
- buyer identity or contactability;
- ROI, operator-hours saved or monetary risk reduction;
- seller discovery or first revenue.

A returned cluster is buyer/problem evidence only. It must not be reported as demand revenue or WTP.

## Waterfound decision and resulting state

On 2026-10-27, Waterfound declined establishing a crypto wallet for this route and directed the mission to find another way. This is a channel constraint, not a pending human gate.

The exact `demand-radar` call remains analytically useful, but it is now **PASSIVE / NOT ACTIONABLE** unless a future non-crypto, already-authorized payment mechanism becomes available without wallet creation, wallet funding, credits purchase, new financial onboarding, or repeated user action. The mission must not ask Waterfound again for an x402 wallet or treat the declined route as blocking overall commercial progress.

The unpaid 402 challenge was already verified on 2026-10-24. Repeating it adds no information. No new wallet, credits purchase, payment instrument, or credential repurposing is authorized.

## Execution contract after the gate clears

The next admissible execution must:

- call the exact URL once;
- use a fresh idempotency key;
- refuse any quote above USD 0.005;
- preserve the unmodified response, payment quote and settlement receipt privately;
- record only non-secret derived evidence in the commercial dossier;
- screen all qualified rows against substitutes;
- select no more than one narrow job;
- make no second paid call;
- perform no outreach, public listing, seller registration, account installation, new permission grant, contract acceptance, payout/KYC or Privacy P0 activation.

If the call fails without settlement, one idempotent retry may replay the same purchase only when the payment client confirms the first request did not settle or the service documents replay under the same idempotency key. Ambiguous settlement means stop and reconcile; it never authorizes another charge.

## Current commercial decision

- Agent402 channel: **PASSIVE / REAL_MACHINE_RAIL / DISTRIBUTION_UNPROVEN / CRYPTO_WALLET_ROUTE_DECLINED**
- Demand-radar call: **COMMERCIALLY_USEFUL / NOT_ACTIONABLE_WITHIN_CURRENT_NON_CRYPTO_CONSTRAINT**
- Bestsellers call: **USEFUL_BUT_NOT_AUTHORIZED**
- Product candidate: **none**
- External WTP for Waterfound: **none**
- Revenue: **USD 0**
- Infrastructure: **SUPPORT_ONLY**
- Privacy producer: **inactive; no authorization verified**

No generic Agent PR Recovery & Approval Ledger build is admitted. Its absence from the inspected first-party Agent402 catalog is not differentiation against the full live marketplace, and no paid/unmet signal currently names it.

## Kill criteria

Close this Agent402 discovery path after the authorized call if any one holds:

- no qualified non-noise cluster remains;
- remaining clusters are discoverability-only;
- adequate substitutes satisfy the same narrow job;
- all plausible clusters require forbidden publication, private access, financial onboarding, regulated assurance or paid upstreams;
- no cluster fits a public/synthetic read-only proof;
- the response cannot be reconciled to the documented qualification fields.

Continue machine-admissible commercial discovery elsewhere if the call remains blocked; do not label the whole Revenue Mission `HUMAN_GATE`.

No payment, wallet creation/funding, credits purchase, public registration, outreach, publication, contract, KYC, private ingress, dispatcher/state write, persistent-runtime activation or Privacy P0 activation occurred.
