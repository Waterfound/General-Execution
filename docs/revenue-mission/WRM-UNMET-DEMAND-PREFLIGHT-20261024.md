# WRM unmet-demand preflight — 2026-10-24

Status: `FREE_AGGREGATE_CONFIRMED / FOUR_QUALIFIED_CLUSTERS / IDENTITIES_PAYWALLED / PAYMENT_GATE / NO_PRODUCT_SELECTED`

## Commercial predicate

Can public evidence identify a narrow, independently requested machine job that is strong enough to justify a substitute screen and the smallest read-only proof?

## Primary evidence

Agent402's free `GET /api/wishes` feed returned a live aggregate envelope with:

- 4,451 total wishes;
- 1,369 distinct clusters;
- build threshold 5;
- qualification minimum 3 distinct day-scoped callers;
- qualification minimum 24 hours (or two signal sources);
- 4 qualified clusters.

A later free read returned 4,458 wishes and 1,374 clusters, consistent with a live feed. Query parameters such as `limit`, `minCount`, `qualified`, and `include` did not disclose cluster identities. This is expected behavior, not a parsing failure: Agent402's first-party demand-radar documentation explicitly calls `/api/wishes` a “counts only” beacon.

The paid `GET /api/demand-radar` route exposes cluster text, counts, source mix, caller count, first/last seen, span, qualification, signal type, threshold gap, and noise flags. Its documented query is:

```text
https://agent402.tools/api/demand-radar?sort=count&limit=50&minCount=1&qualifiedOnly=true
```

Price: USD 0.005 per successful call over x402 or MPP; no free tier. The documentation says failed HTTP 4xx+ calls are not charged for x402/MPP/credits, and an `Idempotency-Key` replays a successful retry without charging again.

Sources:

- https://agent402.tools/api/wishes
- https://agent402.tools/tools/demand-radar
- https://docs.cdp.coinbase.com/x402/buyer/discover-services
- https://huggingface.co/datasets/tanod/x402-bazaar-endpoint-demand
- https://bazaar.saylorinnovations.com/insights

## What public substitutes can and cannot answer

The CC-BY Tanod endpoint dataset and public Agent Bazaar market page expose existing x402 supply and paid-call counts. They are useful for substitute and concentration checks after a job is known, but they do not reveal searches that found nothing or explicit unserved tool requests. On 2026-10-24 Agent Bazaar reported 38,856 resources but only 242 with at least 20 unique payers; this reinforces the need to select from demonstrated unmet demand rather than add another catalog entry.

## Candidate falsification performed

A public GitHub issue in `openai/openai-agents-python` requests built-in x402 tool-call payment support. That is genuine problem evidence, but the generic adapter/governance wedge is rejected before implementation because direct substitutes already exist, including AsterPay's OpenAI Agents adapter, Agoragentic's OpenAI Agents adapter, Sardis framework integrations, SpendVeto, multiple x402 spend-policy packages, and a Nano-specific OpenAI Agents adapter.

Primary issue and substitute evidence:

- https://github.com/openai/openai-agents-python/issues/5183
- https://pypi.org/user/asterpay/
- https://pypi.org/project/agoragentic/
- https://github.com/EfeDurmaz16/sardis
- https://github.com/revanthrajeev/spendveto
- https://github.com/dhyabi2/openai-agents-nano-x402

Conclusion: `GENERIC_OPENAI_AGENTS_X402_ADAPTER_REJECTED / SUBSTITUTE_CROWDING`.

## Evidence classification

| Claim class | Result |
| --- | --- |
| Capability | Public feeds and substitute evidence can be read without new credentials. |
| Observed outcome | The free unmet-demand board currently reports four qualified clusters, but withholds their identities. |
| Competitive differentiation | None selected. The generic adapter candidate failed its substitute screen. |
| Demand evidence | Aggregate qualified demand exists; the actual jobs and signal types remain unknown. |
| WTP | Not established for any Waterfound product. Existing endpoint payments are market observations, not Waterfound demand. |
| ROI | Not measured. |

## Kill and proceed rules

- Do not build from the aggregate count alone.
- Reject any revealed cluster dominated by `discoverability` rather than `explicit-request` unless a distribution-only job is separately justified.
- Reject a cluster if direct native/free substitutes cover the requested outcome.
- Reject a cluster whose qualification depends on one caller, operator/CI noise, or a short repeated burst.
- Only prototype after one qualified cluster survives source, substitute, lawful-input, recurring-human-dependency, and machine-deliverability checks.

## Exact bounded gate

The cheapest remaining experiment that reveals the four qualified job identities is one USD 0.005 demand-radar call with `qualifiedOnly=true`, `limit=50`, and a unique idempotency key.

This requires separately authorized payment capability (wallet or pre-existing Agent402 credits). No wallet creation, funding, credential use, payment, account installation, or paid call is authorized by the Revenue Mission envelope, so none was attempted.

After authorization, record the unmodified response, reconcile the settlement receipt, screen every returned cluster against public substitutes, and select at most one candidate. The paid response would be research evidence only; it would not authorize product publication, outreach, account installation, or further spend.
