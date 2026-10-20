# WRM GitHub Actions Cost-Waste Audit Screen — 2026-10-20

## Decision

**State:** `REJECT_BEFORE_BUILD / NATIVE_AND_EXACT_SUBSTITUTES_CONFIRMED / NO_PRODUCT_SELECTED`

Do not build the proposed read-only GitHub Actions cost-waste audit. The first commercial predicates failed: bounded current-market search found only adjacent demand embedded in broader DevOps work, while GitHub and multiple free/open/commercial tools already provide workflow-level cost visibility, waste detection, estimates, and optimization recommendations.

No customer outreach, public publication, repository installation, credential request, paid spend, pricing, contract, or financial onboarding was performed.

## Narrow job-to-be-done tested

> Given GitHub Actions workflow files and recent run metadata, produce a read-only evidence report that attributes modeled spend, identifies avoidable executions and expensive runner/matrix choices, and ranks changes by conservative savings potential before any workflow is modified.

The smallest possible proof would parse public workflow YAML, expand matrices, apply official runner rates, combine public run durations, and emit findings such as unnecessary triggers, redundant matrices, repeated failures, missing concurrency cancellation, cache misses, and oversized runners.

## Buyer/problem evidence

### What was observed

- A current Upwork healthcare SaaS listing asks for an AWS Cloud Infrastructure & DevSecOps Architect and includes GitHub Actions plus cloud cost monitoring and optimization. This supports the broader problem, but the buyer is purchasing architecture and implementation, not an isolated read-only Actions audit.
  - https://www.upwork.com/freelance-jobs/apply/AWS-Cloud-Infrastructure-DevSecOps-Architect-Healthcare-SaaS-HIPAA_~022104656882946626024/
- GitHub reports that Actions operates at very large scale and provides official pricing calculators, usage reports, budgets, and cost centers. Cost visibility is a real operational concern, but the official 2026 pricing update says 96% of customers should see no bill increase and only a minority of users are materially affected.
  - https://github.com/resources/insights/2026-pricing-changes-for-github-actions
- Public discussion includes teams reporting meaningful avoidable Actions spend, but discussion is not willingness-to-pay evidence for Waterfound.

### What was not observed

The bounded current search did not find a public buyer asking to purchase only a read-only GitHub Actions cost-waste report. Visible demand instead bundles diagnosis with CI/CD ownership, cloud architecture, migration, remediation, or managed runners.

**Evidence classification:** problem evidence exists; standalone buyer and WTP evidence do not.

## Native coverage

GitHub's own Actions metrics documentation says organization owners can:

- view usage for each workflow;
- understand the cost of running Actions;
- identify optimization opportunities such as workflow refactoring or runner changes;
- compare GitHub-hosted and self-hosted runner minutes and run volumes.

Sources:

- https://docs.github.com/en/actions/concepts/metrics
- https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions
- https://docs.github.com/en/billing/how-tos/products/estimate-spending
- https://docs.github.com/en/billing/concepts/cost-centers
- https://github.com/pricing/calculator

This native coverage requires organization/billing access for authoritative private spend, which also means a third-party audit cannot quantify actual savings from public YAML alone.

## Exact and adjacent substitutes

### Exact read-only calculators and auditors

- **depmedic** prices pasted workflow YAML in-browser, expands matrices, applies official runner pricing, projects monthly spend, and offers an audit/CI doctor for waste and fixes without requiring administrative billing access.
  - https://depmedicdev-byte.github.io/budget.html
  - https://depmedicdev-byte.github.io/calculator.html
- **ci-cost** reads `.github/workflows/*.yml`, identifies optimization opportunities, estimates savings, and can generate improved workflows.
  - https://github.com/mariotavarez/ci-cost
- **github-actions-optimizer** analyzes workflow costs, identifies expensive workflows, and emits optimization suggestions.
  - https://github.com/eylulsenakumral/github-actions-optimizer
- **cicd-optimizer** finds wasted minutes and cost across GitHub Actions and GitLab CI, includes configurable price models, auto-refactor suggestions, and a dashboard.
  - https://github.com/mrckurz/cicd-optimizer
- **GitHub Next CI coach** is a daily agentic workflow that analyzes GitHub Actions for efficiency and cost-reduction opportunities.
  - https://github.com/githubnext/agentics/blob/main/workflows/ci-coach.md

### Installed/commercial operational substitutes

- **ActionsCost** provides workflow cost breakdown, automated tracking, and budget alerts through a GitHub App.
  - https://www.actionscost.com/
  - https://www.actionscost.com/pricing
- **Pipetrics** attributes modeled cost to repositories, workflows, jobs, runners, outcomes, and billing categories, and prioritizes unnecessary runs, repeated failures, cache misses, matrices, concurrency, and runner choices.
  - https://pipetrics.com/
- **BuildPulse** combines runner usage analytics, CI/test analytics, faster lower-cost runners, and bottleneck/flaky-test diagnosis.
  - https://buildpulse.io/
  - https://buildpulse.io/pricing

These products span the proposed report from static YAML estimates through authoritative run analytics and implemented cost reduction.

## Competitive falsification

The candidate fails differentiation:

1. **Native data answers the core attribution predicate.** GitHub already exposes workflow-level usage and cost-oriented optimization metrics to authorized owners.
2. **Exact free substitutes answer the public/read-only predicate.** Existing tools parse workflow YAML, expand matrices, price runs, find waste, and suggest changes.
3. **Commercial substitutes own the private operational workflow.** They ingest actual runs, monitor budgets, diagnose bottlenecks, or replace runners.
4. **Authoritative ROI needs private data.** A public-only audit cannot know included allowances, private workflow frequency, rerun patterns, negotiated pricing, self-hosted infrastructure cost, or actual billing attribution.
5. **Demand is bundled.** The current buyer evidence seeks DevOps ownership and remediation rather than a standalone memo.

Waterfound's internal experience with exhausted Actions capacity is an observed operator problem, not evidence of external demand, generalized savings, or WTP.

## Kill criteria and result

| Kill criterion | Result |
|---|---|
| At least two current buyers explicitly purchase the report as a bounded standalone deliverable | **Failed** — none found in the bounded current search |
| Native GitHub views do not already expose workflow-level cost/usage | **Failed** — native metrics explicitly do |
| No free exact substitute can price YAML and identify waste | **Failed** — several exact tools exist |
| A synthetic proof would answer a still-open commercial predicate | **Failed** — it would reproduce established static analysis |
| Conservative savings can be verified without private billing/run access | **Failed** — public inputs support modeled estimates only |

Because the buyer and substitution predicates failed, implementation is not admissible under the Commercial Progress Ratchet.

## Established vs. unknown

### Established

- Actions spend and CI efficiency can be material for some teams.
- GitHub provides native workflow usage/cost metrics and billing controls.
- Free/open tools already estimate costs and detect common waste from workflow files.
- Commercial platforms provide deeper run analytics, alerts, diagnosis, or cheaper execution.

### Unknown — do not claim

- Whether any buyer would pay Waterfound for an independent audit.
- Actual customer savings, operator-hours saved, latency reduction, avoided rework, or incident reduction.
- Accuracy of modeled costs against a private organization's invoice.
- Whether an independence/compliance requirement creates a narrow defensible segment.

## Possible future refinement, not selected

A distinct service would require buyer evidence for an independent, vendor-neutral **verified savings attestation** that reconciles invoices, usage exports, workflow semantics, and post-change measurements. That service necessarily requires authorized private billing/run data and human commercial engagement. It is not justified by current evidence and is outside the public/synthetic proof stage.

## Portfolio consequence

- Mark **GitHub Actions Cost-Waste Audit** `PASSIVE / REJECTED`.
- Build no parser, dashboard, calculator, or new telemetry.
- Keep existing Waterfound CI evidence as `SUPPORT_ONLY`.
- Preserve `NO_PRODUCT_SELECTED`, revenue `USD 0`, and no WTP/ROI claim.
- Continue discovery at buyer/problem evidence or currently funded work; reject the next candidate on its first failed predicate.
