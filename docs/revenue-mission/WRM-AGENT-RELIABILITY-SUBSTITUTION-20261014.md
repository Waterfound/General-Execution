# WRM — Agent reliability and recovery substitution screen (2026-10-14)

Status: `GENERIC_RESIDUAL_KILLED / LOW_COST_MARKET_CONFIRMED_COMMODITIZED / CROWDED_BOUNTY_CHANNEL_REJECTED / MICRO_HYPOTHESIS_ONLY / NO_PRODUCT_SELECTED`  
Observed Waterfound revenue: **USD 0**

## Commercial question

Does the remaining WRM hypothesis — a same-input diagnostic that injects duplicate, retry, timeout, crash and partial-failure conditions, then verifies authoritative terminal state — remain differentiated enough to justify a synthetic candidate proof?

## Direct commercial substitute

Source: https://www.dipankar.co/services/agent-reliability-and-recovery/

Dipankar Sarkar advertises a scoped **AI Agent Reliability and Recovery Engineering** engagement that already covers the complete generic job:

- trace real failed and duplicated runs;
- model workflow states and external effects;
- classify actions as safe to retry, deduplicable, compensable or requiring human confirmation;
- implement persisted checkpoints, idempotency keys, check-before-act, compensation and bounded per-call retries;
- inject timeouts, crashes and partial failures at every step;
- replay runs and verify that external systems finish with no duplicates or orphaned effects;
- deliver replay tests, state model, idempotency strategy, monitoring and an operator recovery runbook;
- require operator acceptance against agreed terminal-state criteria.

The listed engagement starts at **USD 25,000 / GBP 20,000 fixed scope**, including implementation, tests, evaluation, documentation and handover. This is public category-pricing evidence, not Waterfound WTP or proof of this provider's realized sales.

This substitute is deeper than the proposed generic WRM diagnostic because it includes both proof and remediation. It also requires code, logs, a non-production environment and test versions of external systems, so it does not eliminate a hypothetical zero-access micro-screen — but it removes the broader service as a unique Waterfound claim.

## Platform substitutes and adjacent native capability

### Evaluation platforms

Sources:

- https://laminar.sh/article/best-ai-agent-evaluation-platforms
- https://www.langchain.com/langsmith/evaluation

Laminar's current comparison states that agent evaluations can deterministically verify authoritative resulting state — for example, whether the correct order was refunded exactly once — and compare the same cases across versions. It lists Laminar, LangSmith, Langfuse, Maxim and others as platforms for datasets, traces, custom evaluators, simulations and CI regression analysis.

LangSmith advertises full-trajectory capture, custom Python or TypeScript evaluators, offline and online evaluation, CI integration and same-dataset comparisons across agent versions. These platforms do not by themselves prove turnkey fault injection into arbitrary external systems, but they substitute for the generic dataset, trace, grader and regression portions of the proposed proof.

### Runtime-native fault tolerance

Source: https://www.langchain.com/blog/fault-tolerance-in-langgraph

LangGraph now provides node-level retry, timeout and error-handler primitives and explicitly frames side-effecting multi-step workflows as the fault-tolerance problem. This weakens a generic claim that merely recommends retry boundaries, timeouts or recovery handlers.

## Buyer/problem evidence retained

Prior paid listings already established adjacent pain:

- invoice automation requested duplicate prevention and tests for duplicate and failed extraction;
- an insurance claims agent buyer reported lost submissions on 429/529 responses, malformed outputs, loops, higher cost and latency.

Those listings were allocated, highly contested and dependent on private systems. They establish problem salience, not demand for Waterfound or availability of a test customer.

## Low-cost substitution and realized transaction evidence

Source: https://www.upwork.com/services/product/development-it-a-broken-n8n-make-or-zapier-workflow-fixed-2105984848028958507

An Upwork Project Catalog seller publicly offers repair of broken n8n, Make or Zapier workflows at **USD 50 / USD 120 / USD 250**. The offer explicitly covers silent failures or double runs, wrong or missing data, webhook/API/authentication failures, rate limits, timeouts, a tested repair and a plain-English summary; Standard and Advanced also include error handling and failure alerts.

The page shows a five-star review dated **2026-10-01** for the completed job **“AI Automation Specialist – Existing Workflow Automation & Error Handling”**: “Amazing work. Everything we expected and wanted has been delivered.”

This is realized purchase evidence in the exact low-code workflow-reliability category. It does **not** establish Waterfound demand or WTP, the transaction amount actually paid, repeat purchasing, diagnostic-only demand, or provider economics.

## Fresh buyer/job evidence: pre-demo agent QA

Source: https://www.upwork.com/freelance-jobs/apply/n8n-Automation-Specialist-Review-Existing-Agents_~022107505844883771824/

A recent contract-to-hire listing asks for review of existing n8n agents and architecture, stress tests across normal and edge cases, checks of error handling, retries, fallbacks, prompts, tool calls, integrations, data flows, reliability and security, followed by a short prioritized report and a **Demo Ready / Not Demo Ready** verdict. Fixes are explicitly scoped separately.

This validates a buyer-described pre-demo QA job, but not an available Waterfound opportunity: proposal and hiring counts were not visible through read-only retrieval, and applying would require external outreach, work examples, location/time-zone and availability disclosures, plus access to private existing agents. No application or contact was made.

## Public bounty channel screen: Go-Hybrid

Sources:

- https://github.com/limitlessprojects/Go-Hybrid/blob/f99d6d0b37722de206015be9e1c59b04e827c794/BOUNTY.md
- https://github.com/limitlessprojects/Go-Hybrid/blob/f99d6d0b37722de206015be9e1c59b04e827c794/GUARANTEES.md

A read-only source review at exact commit `f99d6d0b37722de206015be9e1c59b04e827c794` screened a public Hybrid compiler soundness bounty as a possible machine-deliverable revenue channel.

Verified economics and competition:

- the advertised pool is **USD 500 per cycle**, split across ten ranked contributions: USD 75, 60, 50, then USD 45 for places four through ten;
- payout occurs only after maintainer reproduction; theories, duplicates, known issues and already-fixed findings receive no payment;
- exact amounts may be changed before cycle close, and no escrow or prefunding proof is stated;
- the Hall of Fame already records many October 2026 soundness, harness and tooling contributions, including several multi-finding contributors;
- latest-main reproduction and a minimal accepted-but-unsound `.hy` program are mandatory.

The checker source and corpus were inspected rather than bulk-scanned. The obvious closure-escape case is expressly documented as the contested A5 perimeter, while task/send boundaries inside closures now receive a dedicated fail-closed pass. Recently landed fixes also cover shadowing, call-return aliases, const mutation, pointer allocation, composite sharing, non-owned moves, method/function confusion, multi-value shapes, managed-gate ambiguity and related families.

Decision: **`REJECT_AS_ACTIVE_REVENUE_CHANNEL`**. The expected value is too low for continued speculative hunting: maximum advertised first place is USD 75, duplicate and rapid-fix risk are high, funding is not independently verified, and no novel accepted-but-unsound reproduction was found. Reopen only if a minimal, latest-main, previously unknown repro is already produced during otherwise useful research. No issue, claim, account action, disclosure or payment setup was made.

## Decision

### `KILL_AS_UNIQUE_DIFFERENTIATOR`

Do not build or market:

- generic AI-agent reliability diagnostic;
- generic same-input replay or duplicate test service;
- generic state/effect classification;
- generic idempotency, retry, compensation or recovery roadmap;
- generic fault-injection suite plus operator runbook;
- generic trace/dataset/evaluator dashboard;
- generic low-cost n8n, Make or Zapier audit/repair;
- generic pre-demo QA/readiness report without a distinct, measurable outcome.

The high-value reliability/recovery service is already offered commercially, evaluation platforms and runtimes provide substantial native components, and low-cost workflow repair has both public substitutes and realized transaction evidence.

### Residual: `MICRO_HYPOTHESIS_ONLY / NO_BUILD`

Only this narrower job remains logically possible:

> Given one lawful, representative workflow artifact and one buyer-defined ambiguous-success failure, produce a zero-install, read-only counterexample showing whether two executions of the same input can create divergent or duplicate authoritative terminal state, with a deterministic evidence bundle and an incumbent baseline.

This residual is materially narrower because it excludes implementation, remediation, monitoring and ongoing operations. The low-price angle is no longer differentiated: public offers start at USD 50 and include tested repair. It is not yet a product: no available buyer has requested this specific counterexample, no willingness to try or pay exists, and no evidence shows that the USD 25,000 service, low-cost repair market or existing evaluation tooling is too heavy for a buyer who would purchase the micro-screen.

## Admission predicate

Build the smallest synthetic/public proof only after all are true:

1. an available buyer states one costly ambiguous-success, duplicate or interrupted-retry failure;
2. the buyer accepts a public, synthetic or explicitly authorized fixture as representative;
3. the authoritative terminal-state predicate is deterministic and observable;
4. the same fixture can be run against a named incumbent/native baseline;
5. the desired output is diagnosis/evidence rather than implementation;
6. the buyer expresses willingness to try the bounded proof;
7. no outreach, publication, credentials, private access, contract, payment onboarding or spend is needed to complete the proof.

## Kill criteria for the micro hypothesis

Kill it if any of these hold:

- the buyer needs remediation or a runbook, which the direct service already covers;
- a custom evaluator in LangSmith/Laminar or an ordinary integration test produces the same result at comparable friction;
- the failure cannot be reproduced without private code or external-system access;
- the buyer will not treat a synthetic/public fixture as decision-relevant;
- no buyer expresses willingness to try;
- the output remains a generic checklist rather than an authoritative state counterexample.

## Evidence state

- Capability: Waterfound has governed execution and recovery/idempotence rehearsal evidence, not a buyer-specific diagnostic.
- Buyer/problem: adjacent paid listings and one realized category transaction exist.
- Category willingness to pay: **observed for low-code workflow repair**, amount actually paid unknown; this is not Waterfound WTP.
- Competitive differentiation: generic reliability/recovery and low-cost workflow audit/repair are **falsified as unique**.
- Direct bounty channel: **rejected as an active revenue path** after source inspection; no qualifying repro or expected-value case was established.
- Narrow product proof: **not admitted**.
- External demand for Waterfound: unverified.
- Willingness to try/pay, ROI, fair price and revenue: unverified / USD 0.

No customer contact, public commercial publication, account installation, credential use, private-data access, payment setup, spend, runtime activation or merge was performed.
