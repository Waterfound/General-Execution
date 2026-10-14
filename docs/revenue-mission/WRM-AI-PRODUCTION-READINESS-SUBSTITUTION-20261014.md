# WRM AI production-readiness substitution screen — 2026-10-14

Status: `GENERIC_WEDGE_KILLED / RESIDUAL_HYPOTHESIS_ONLY / NO_PRODUCT_SELECTED`  
Observed Waterfound revenue: **USD 0**

## Question

Is a read-only production-readiness audit for an existing AI or document-extraction pipeline a differentiated first Waterfound product?

## Direct substitutes

Checked 2026-10-14 UTC using first-party vendor pages.

### ActiveWizards — Production AI Readiness Review

Source: https://activewizards.com/services/production-ai-audit/

ActiveWizards markets a fixed-fee, five-business-day review for one live or near-live AI system. Its advertised inspection surface includes retries, timeouts, fallback, checkpointing, session recovery, regression gates, observability, source attribution, approval boundaries, audit trails and rollback-related failure handling. Deliverables include a ranked gap map, architecture recommendations, stabilization path and blocker diagnosis.

This directly substitutes for a generic Waterfound “production reliability diagnostic” based on evidence gaps, recovery and governance.

### Bettag Systems — AI Production Readiness Consulting

Source: https://bett.ag/en/ai-production-readiness

Bettag advertises an initial consultation priced at **EUR 999**, followed by review of prompts, pipelines, telemetry, deployment and security controls. Deliverables include a readiness report, launch checklist, risk register, evaluation/monitoring recommendations and architecture notes. It explicitly covers regression fixtures, audit logs, incident runbooks and rollback.

This is direct public price evidence for the category, not willingness to pay for Waterfound.

### Teamvoy — LLMOps Readiness Audit

Source: https://teamvoy.com/llmops-consulting-services/

Teamvoy markets a paid, fixed-scope, 3–5 day LLMOps readiness audit covering evaluation coverage, trace depth, versioning, cost visibility and rollback. It produces a written gap list usable with any implementation partner.

This substitutes for a generic short audit plus remediation roadmap.

### LandingAI — field-level extraction provenance

Source: https://landing.ai/llms/audit-trails-in-document-ai-tracing-extracted-data-back-to-source-pages

LandingAI ADE advertises field-level source ranges, page and bounding-box grounding, reviewer confirmation/correction/escalation, immutable source-version preservation and audit-record construction. Its published bank case reports 40–60% less manual review for one implementation, with an explicit non-generalization caveat.

This directly substitutes for “map each extracted value back to its source” as a unique Waterfound feature. It does not by itself prove duplicate/revision/reprocessing correctness across an existing heterogeneous pipeline.

## Decision

### `KILL_AS_UNIQUE_DIFFERENTIATOR`

Do not build or sell these generic claims:

- AI production-readiness audit;
- ranked reliability/evaluation/observability/governance gap map;
- generic retry, recovery and rollback checklist;
- LLMOps evaluation/trace/versioning audit;
- field-level document-extraction provenance or review UI;
- remediation roadmap as the sole differentiated output.

Multiple specialists already advertise the same job, delivery window and outputs. One publishes a EUR 999 entry price, and the document-extraction platform publishes field-level auditability plus a buyer outcome.

### Residual hypothesis — `HOLD_UNPROVEN_NO_BUILD`

A narrower same-input diagnostic may survive:

> Given a buyer's existing multi-stage extraction pipeline and a lawful representative fixture containing duplicates, corrected source documents, model-version changes and interrupted retries, produce reproducible failure cases and determine whether the pipeline preserves correct terminal state, source binding and replay safety.

This differs from a checklist only if it executes buyer-specific failure cases and returns reproducible evidence that incumbent observability, lineage and readiness reviews do not already supply.

No buyer has requested this exact residual. No Waterfound-specific demand or WTP exists.

## Admission predicate

Admit a smallest read-only proof only when all are true:

1. a real buyer names duplicate, correction, reprocessing or interrupted-retry failure as a current costly problem;
2. public, synthetic or explicitly authorized representative inputs exist;
3. the buyer defines an observable terminal-state or provenance acceptance predicate;
4. the proof compares the same fixture against at least one incumbent/native baseline;
5. the opportunity is fresh, unallocated and low-contention;
6. no private code, production credentials, contract, outreach, payment onboarding or publication is needed before the proof is complete.

## Kill criteria

Kill the residual if:

- the buyer only wants a generic readiness checklist or architecture review;
- LandingAI/native extraction grounding already answers the acceptance predicate;
- ordinary data-lineage, LLM observability or CI tooling reproduces the same evidence at comparable friction;
- no same-input counterexample can be produced without private access;
- demand remains limited to marketplace listings already saturated or allocated;
- the output cannot measure a real outcome such as false terminal success, lost provenance, duplicate effects, unsafe replay or recovery failure.

## Evidence state

- Capability: Waterfound rehearsals establish governed execution and recovery/idempotence assertions, not this buyer-specific service.
- Buyer/problem: repeated paid listings support production-reliability demand.
- Competitive differentiation: generic readiness audit and field-level provenance are **falsified as unique**.
- Narrow product proof: not admitted; residual lacks buyer and representative fixture.
- Demand for Waterfound, willingness to try, Waterfound WTP, ROI, price and revenue: unverified.

## Next commercial frontier

Search for a fresh buyer explicitly reporting duplicate/revision/reprocessing/retry failure in an existing extraction pipeline, with a public or authorized fixture and objective terminal-state acceptance. Do not add audit instrumentation or build a generic readiness product while that predicate is absent.
