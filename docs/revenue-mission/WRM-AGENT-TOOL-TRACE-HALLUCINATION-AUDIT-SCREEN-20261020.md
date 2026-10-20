# WRM Agent Tool-Trace Hallucination Audit Screen — 2026-10-20

## Decision

**State:** `REJECT_BEFORE_BUILD / EXACT_SUBSTITUTE_CONFIRMED / NO_PRODUCT_SELECTED`

Do not build the proposed read-only proof. The commercial predicate failed before implementation: the narrow mechanism is already demonstrated publicly, while mature evaluation/observability products cover the surrounding release workflow. Keep Waterfound's existing provenance and authority-stop capabilities as `SUPPORT_ONLY`; they are not evidence of a differentiated product, customer demand, willingness to pay, or ROI.

No customer outreach, public publication, credential expansion, paid spend, pricing, contract, or external installation was performed.

## Narrow job-to-be-done tested

> Before releasing an agent that can invoke tools, show a reviewer which factual and state-change claims are supported by observed tool executions, and flag claims whose asserted action or result is absent from the trace.

Proposed falsifiable artifact: a read-only report over a synthetic trace that maps output claims to tool-call evidence and classifies each claim as supported, contradicted, or unsupported.

## Buyer/problem evidence

The problem is real, but the evidence supports a broader engineering/evaluation purchase rather than a standalone Waterfound product:

- A current Upwork listing for a **Senior AI Agent Engineer** states that every production release requires a hallucination audit and asks for agent architecture that distinguishes observed facts. This is direct buyer-language evidence that release-time hallucination auditing matters, but the requested unit of purchase is senior engineering delivery, not an independent claim-to-trace report.
  - https://www.upwork.com/freelance-jobs/apply/Senior-Agent-Engineer_~022101132790930983210/
- A current $100 fixed-price Upwork RAG/chatbot listing includes hallucination prevention and source-grounded responses inside a much broader application build. This is evidence of demand for the outcome but also price compression and bundling.
  - https://www.upwork.com/freelance-jobs/apply/Chatbot-Developer-RAG-Automation_~022106485931282141005/
- A current AI Solutions Architect listing prices a broader role at $100–$125/hour and explicitly includes golden datasets, LLM-as-judge, hallucination and regression detection, and CI/CD quality gates. Again, the buyer purchases integrated evaluation engineering.
  - https://haystackapp.io/jobs/a5ebb44b-53b8-4f07-885f-e7a21afdb342

**Evidence classification:** buyer/problem evidence exists; standalone demand and WTP for the proposed Waterfound unit do not.

## Exact and adjacent substitutes

### Exact core predicate

The March 2026 paper **“Tool Receipts, Not Zero-Knowledge Proofs: Practical Hallucination Detection for AI Agents”** presents NabaOS, which:

- generates HMAC-signed receipts for tool executions;
- classifies factual claims by their relationship to tool evidence;
- verifies direct claims against receipts and flags ungrounded claims;
- explicitly answers whether claims are supported by tool execution evidence;
- reports 91% hallucination detection with less than 15 ms overhead;
- releases its benchmark and Rust implementation as open source.

This is materially the same core predicate as the proposed Waterfound proof, with a stronger published mechanism and benchmark.

Source: https://arxiv.org/abs/2603.10060

### Mature workflow substitutes

- Langfuse records production traces, compares output claims with recorded input/context, provides managed hallucination evaluators, offline datasets and experiments, deterministic prescreens, CI-style aggregate metrics, annotation queues, and self-hosting. It explicitly treats grounded-context detection as comparing claims against evidence travelling with the trace.
  - https://langfuse.com/resources/engineering/hallucination-detection
- Noveum positions an integrated stack for tracing, evaluation, diagnosis, simulation, and guardrails, with 112 published scorers across 15 categories for production chatbots and multi-agent workflows.
  - https://noveum.ai/en/blog/hallucination-detection-production-ai-agents
- Yellow.ai documents automated agent testing in evaluation and simulation modes after knowledge-base, prompt, or workflow changes.
  - https://docs.yellow.ai/docs/platform_concepts/AIAgent/automated-agent-testing

These substitutes do not all provide cryptographic receipts, but they already own the adjacent buyer workflow: traces, evaluations, release regression checks, dashboards, and review queues.

## Competitive falsification

The proposed wedge fails differentiation for four reasons:

1. **The mechanism is not novel.** NabaOS directly binds claims to signed tool-execution receipts and publishes a benchmark and implementation.
2. **The operational surface is crowded.** Langfuse and other evaluation platforms already convert recorded context and traces into hallucination scores, experiments, and release gates.
3. **Observed buyer demand is bundled.** Current listings buy an engineer or an end-to-end evaluation framework, not a standalone ledger/report.
4. **Waterfound capability is not market proof.** Existing provenance, idempotence, recovery, and authority-stop evidence show governed execution capability only. They do not establish superior detection accuracy, lower review time, avoided incidents, customer demand, or willingness to pay.

## Kill criteria and result

| Kill criterion | Result |
|---|---|
| No public exact substitute for claim ↔ tool-execution evidence | **Failed** — NabaOS is an exact public substitute |
| Clear missing function in native observability/evaluation stacks | **Failed** — mature stacks cover traces, groundedness, experiments, release checks, and review |
| Evidence of a buyer purchasing this as a standalone deliverable | **Failed** — current demand is bundled into engineering or broader application work |
| A synthetic proof would answer a still-open commercial predicate | **Failed** — it would only re-demonstrate technical feasibility already established elsewhere |

Because the first failed predicate is decisive, implementation is not admissible under the Commercial Progress Ratchet.

## What is established vs. unknown

### Established

- Buyers care about hallucination control and release evaluation.
- Tool-trace-grounded claim verification is technically feasible.
- An exact public implementation and multiple mature adjacent platforms exist.
- Current public demand samples bundle this work into broader engineering/evaluation engagements.

### Unknown — do not claim

- Whether a regulated vertical would pay for independent signed attestation.
- Whether third-party audit independence, chain-of-custody, or cross-vendor neutrality creates a defensible wedge.
- Any operator-hours saved, latency reduced, rework avoided, monetary risk reduced, customer demand for Waterfound, or WTP.
- Whether Waterfound outperforms NabaOS or incumbent evaluators on accuracy, coverage, false positives, or reviewer effort.

## Possible future refinement, not selected

A narrower independent-attestation service might become distinct only if evidence shows a buyer needs all of:

- externally verifiable chain-of-custody rather than self-operated observability;
- domain-specific release criteria and accountability;
- private trace handling within a defined legal/compliance boundary;
- a signed reviewer conclusion accepted by a procurement, insurance, or regulatory process.

That thesis requires buyer interviews or an authorized private design-partner trace plus domain authority. It is not inferable from current public evidence and does not justify a synthetic build now.

## Portfolio consequence

- Mark **Agent Tool-Trace Hallucination Audit** `PASSIVE / REJECTED`.
- Keep existing Waterfound provenance and recovery machinery `SUPPORT_ONLY`.
- Preserve `NO_PRODUCT_SELECTED`, revenue `USD 0`, and no WTP claim.
- Resume machine-admissible discovery at buyer/problem evidence or current externally funded opportunities; reject on the first failed predicate.
