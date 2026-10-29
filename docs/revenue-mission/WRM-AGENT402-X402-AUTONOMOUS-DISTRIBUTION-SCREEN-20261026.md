# WRM — Agent402/x402 autonomous distribution screen — 2026-10-26

Status: **REAL_MACHINE_PAYMENTS / LOW-FRICTION_BUYER_RAIL / SELLER_DISCOVERY_BOOTSTRAP / MARKET_CONCENTRATION_HIGH / PAID_CALL_NOT_COMMERCIALLY_DISCRIMINATING / NO_SPEND / WATCH_ONLY**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Agent402 supply a lawful, unattended acquisition-and-delivery channel for a Waterfound machine product, with near-zero recurring human action and a falsifiable path to first revenue?

Waterfound previously authorized exactly one USD 0.005 Agent402 demand-radar call. This authorization is a ceiling, not an instruction to spend when the call cannot answer the missing commercial predicate.

## Canonical service facts

Agent402 is an open-source, self-hostable x402 + MCP service operated by Havok Holdings LLC. Its public documentation says:

- buyers can pay per call over x402/MPP or use a proof-of-work free tier;
- sellers can register an x402 API without signup or marketplace commission;
- the hosted router ranks tools from indexed sellers;
- ordinary Base distribution requires independent settlement history, with only a bounded unproven lane for some low-price routes;
- using the hosted service programmatically constitutes acceptance of its terms.

Primary sources:

- https://github.com/MikeyPetrillo/Agent402
- https://agent402.tools/terms
- https://agent402.tools/api/route
- https://agent402.tools/api/revenue
- https://agent402.tools/api/stats

The service is technically relevant to One Machine: purchase can be accountless, delivery is API-native, and seller listing need not require a conventional marketplace profile. This is capability and channel-fit evidence, not Waterfound demand.

## Observed commercial activity

Agent402's public revenue surface, read on 2026-10-26, reported:

- 6,119 indexed seller origins and 250,453 tool listings;
- 83,869 settlements through the host's gates, including the host's own activity;
- 774 distinct outside wallets that had paid the host on-chain;
- about USD 549.05 all-time external revenue on x402/MPP rails;
- 344 distinct external buyers and 24,336 external sales in the retained 30-day sales ledger;
- about USD 417.85 external revenue in that 30-day ledger;
- 597 distinct host tools sold externally;
- only 46 calls served through the Smart Order Router.

Sources:

- https://agent402.tools/revenue
- https://agent402.tools/api/revenue
- https://agent402.tools/api/stats

These figures prove genuine outside settlement and repeat machine purchases at the host. They do **not** prove that an arbitrary third-party seller receives meaningful traffic. The ratio between 6,119 indexed seller origins and 46 router-served calls is direct evidence of a severe distribution/bootstrap problem for a new listing.

The host also discloses that its top five outside wallets account for 62.4% of outside-wallet payments. Its raw top-tool counts combine free, paid, heartbeat and other traffic, so those counts cannot be treated as WTP by tool.

## Ecosystem authenticity boundary

A July 2026 population study of x402 on Base found extreme concentration and warned against reading settlement counts as adoption. Across the measured population it classified 21.20% of settlements as fictitious and 63.78% as internal settlement within a linked cluster; payer, recipient and value Gini coefficients all exceeded 0.98.

Source:

- https://arxiv.org/abs/2607.12575

This does not falsify Agent402's separately published external-only ledger. It does mean Waterfound must use outside buyers, external dollars and independent settlement graphs—not transaction count—as the commercial predicate.

## Why the authorized USD 0.005 call was not spent

A paid call would test buyer-side execution:

1. resolve a tool;
2. sign an x402 payment from a funded wallet;
3. receive a result and receipt.

It would not test the missing seller-side predicates:

- whether a buyer discovers a Waterfound route;
- whether the route is preferred over substitutes;
- whether an independent buyer pays;
- whether the router admits it beyond the unproven lane;
- whether net receipts exceed hosting, support, failure and settlement costs.

The public route/revenue surfaces already answer the channel screen more directly and at zero cost. No funded Agent402/x402 spending credential was independently verified in the current execution envelope, and creating or funding one would be a new financial onboarding/credential action. Therefore spending USD 0.005 would consume the one-call authorization without commercial information gain.

The authorization remains unconsumed. Reconsider only after a specific seller candidate survives differentiation and the paid call is a necessary end-to-end acceptance test for that candidate.

## Seller-path constraint

Self-serve registration is a public marketplace publication. Even without signup, it would publish a commercial route and bind operation to the hosted index/terms. That remains a genuine publication/contract gate.

More importantly, registration before a differentiated tool exists would not create demand. The router documents a cold-start requirement: a new seller normally needs independently funded settlement history to become a proven route. Waterfound must not manufacture that history through self-payments; Agent402 explicitly discounts seller-funded traffic, and the broader ecosystem evidence shows why raw self-generated settlements are not adoption.

## Candidate filter derived from the channel

Any future Agent402 candidate must satisfy all of these before registration or spend:

1. exact paid job is already visible in external-only demand, not inferred from free/top-tool volume;
2. incumbent Agent402 and indexed routes do not already provide the result at equivalent quality;
3. output is deterministic or source-pinned enough for unattended delivery;
4. marginal cost is below price under worst-case retries/refunds;
5. no personal data sale, deceptive finance claim, credential harvesting or prohibited use;
6. public/synthetic proof beats at least one incumbent on a named acceptance predicate;
7. a lawful hosting path exists using current permissions;
8. the route can bootstrap without self-funded fake demand;
9. Waterfound separately authorizes public registration and hosted-service terms;
10. payout custody, tax/KYC and withdrawal remain gated until revenue evidence justifies them.

## Decision

Agent402 is **not closed**: it is the first examined channel with a genuinely machine-native buyer rail, public external revenue evidence, accountless per-call purchase and self-serve seller listing.

It is not ACTIVE yet. Distribution to new sellers is unproven, router activity is tiny relative to indexed supply, and no differentiated Waterfound tool has external WTP evidence.

State:

- Channel: **WATCH_ONLY / PROMISING_RAIL / DISTRIBUTION_UNPROVEN**
- Paid demand-radar call: **AUTHORIZED_BUT_UNCONSUMED**
- Seller registration: **NOT_ADMITTED**
- Candidate build: **NONE**
- External demand/WTP for Waterfound: **NONE**
- Revenue: **USD 0**
- Current human gate: **none**, because machine-admissible candidate discovery remains.

## Reactivation criteria

Promote this channel only when a candidate has:

- one exact externally paid tool class with independent-buyer evidence;
- an incumbent parity matrix;
- a lawful synthetic/public proof;
- a measurable capability advantage;
- bounded hosting and failure economics;
- a registration payload ready for a single publication decision.

At that point the already-authorized USD 0.005 call may be used if it validates the exact paid delivery path and no new wallet/funding authority is required.

No wallet was created or funded; no payment was signed; no service terms were newly accepted; no seller route was registered; no public listing, outreach, provider installation, spend, payout, KYC, runtime activation, state-dispatcher write or Privacy P0 activation occurred.
