# WRM GitHub Actions Waste Auditor — commercial screen

**Date:** 2026-10-26  
**Mission:** Waterfound Revenue Mission / WRM-T1  
**Candidate:** a no-install, read-only report that inspects GitHub Actions workflow files and public run history to identify avoidable CI minutes, queue delay, and likely cost reduction  
**Decision:** `PAIN_AND_ADJACENT_WTP_CONFIRMED / EXACT_WEDGE_NOT_DIFFERENTIATED / PRIVATE_TELEMETRY_REQUIRED / NO_BUILD / CLOSED`

## Commercial predicate

Can a repository-only, no-install GitHub Actions auditor produce sufficiently differentiated and economically provable value for a high-value buyer while preserving Full Autonomy and avoiding credentials, account installation, or human review?

**Answer: no.** The commercial pain is real, but the proposed observation boundary excludes the paid buyer's decisive evidence. Public repositories are useful fixtures, yet standard GitHub-hosted runners for public repositories remain free. Paid optimization depends on private usage, runner SKU, cache behavior, retry and cancellation history, queue time, and billable execution data. Accessing those data requires organization/repository authorization or installation.

## Buyer/problem evidence

- GitHub explicitly bills private-repository Actions usage beyond included quota and publishes current usage/billing concepts. GitHub's 2026 pricing update reduced hosted-runner rates while introducing a cloud-platform charge, reinforcing that CI consumption is an economic line item.
- A current r/devops discussion reports a small shop with 16 developers spending about USD/EUR 1,000 per month on TeamCity plus self-hosted/cloud agents and consuming about 50 build/deploy hours per day. This is buyer-reported pain, not evidence for this exact product.
- RunsOn publishes a customer statement that its runner replacement reduced CI cost by 90%; that is adjacent willingness to pay for an execution substitute with observed bills, not willingness to pay for a static audit.
- Research over 838 workflows from 396 Java repositories found low energy per individual pipeline but meaningful aggregate repeated consumption. A 2026 empirical caching study over 952 repositories found repeated maintenance and diverse cache patterns. These support the existence of optimization work, not a monetizable repository-only report.

## Native substitute

GitHub now provides both Actions usage metrics and Actions performance metrics at repository and organization level:

- usage minutes by workflow/repository;
- job and workflow run times;
- queue times;
- failure rates;
- identification of high-usage workflows and bottlenecks.

GitHub also exposes billable job execution minutes for individual workflow runs and documents `concurrency.cancel-in-progress` as the native mechanism for cancelling superseded work.

This directly answers much of the proposed report's descriptive predicate inside the existing control plane.

## Commercial substitutes

The field is already dense and includes:

- **CICube:** GitHub Actions monitoring, cost analysis, optimization insights, and a read-only integration.
- **Runless:** observes GitHub Actions performance, reliability, and cost without workflow-file changes.
- **CICosts:** cost visibility, trends, optimization opportunities, and API access.
- **MinuteMeter:** free/MIT per-run and per-job cost reporting with budget flags on pull requests.
- **Actions Usage Report:** uses workflow timing data and published runner rates to report actual billable minutes and PR cost.
- **Datadog CI Visibility, Trunk, and BuildPulse:** established pipeline/test observability, flaky-test detection, bottleneck analysis, and optimization.
- **RunsOn, Depot, WarpBuild, Blacksmith, and BuildPulse Runners:** convert optimization into observed runtime/cost outcomes by replacing runner compute.

The proposed static report would be less informed than native metrics and incumbent telemetry, while offering no execution-layer savings itself.

## Exact wedge test

### Residual hypothesis

A no-install preflight could inspect public workflow YAML for:

- missing cancellation/concurrency controls;
- overly broad triggers or missing path filters;
- repeated dependency installation without visible caching;
- excessive or duplicated matrices;
- runner choice and obvious long-running jobs;
- retry patterns visible in configuration.

### Why the residual fails

1. **The public fixture is economically nonrepresentative.** Standard GitHub-hosted runners are free for public repositories, so public runtime cannot establish paid cost savings.
2. **Static configuration is not actual waste.** A missing cache or path filter can be intentional. YAML alone does not establish cache hit rate, changed-file distribution, superseded-run overlap, retry frequency, billable runner SKU, or queue impact.
3. **The paid buyer's evidence is private.** Private history, bills, usage exports, logs, and organization metrics require authorization or installation. That is a legitimate future gate, but it also eliminates the claimed no-install differentiation.
4. **Native metrics already identify the main descriptive problem.** The report would restate data GitHub exposes rather than produce a unique outcome.
5. **Free and paid substitutes already calculate actual cost.** A static inference would be weaker than MinuteMeter, Actions Usage Report, CICube, Runless, CICosts, or runner vendors using telemetry.
6. **Provable value would require a controlled before/after change.** Without installing, changing, and observing a representative private workflow, no operator-hours saved, latency reduction, cancellation savings, cache benefit, or monetary ROI can be claimed.
7. **The buyer segment conflicts with the access boundary.** Teams large enough to pay meaningfully for CI optimization are precisely those whose repositories and billing telemetry are private.

## Value-proof ledger

| Evidence class | Result |
|---|---|
| Capability | Repository YAML and public run summaries are machine-readable |
| Observed outcome | None; no representative private workflow changed or measured |
| Differentiation | Failed against native metrics and existing observability/cost tools |
| Demand | Adjacent demand for CI cost reduction exists |
| Exact-job willingness to try | Not observed |
| Exact-job WTP | Not observed |
| Operator-hours saved | Not measured |
| Mission latency reduced | Not measured |
| Avoidable rework reduced | Not measured |
| Monetary savings | Not measured |
| Revenue | USD 0 |

## Kill criteria

The candidate is closed before implementation because it fails three independent criteria:

- **Differentiation kill:** native and adjacent substitutes already provide more direct usage, performance, and cost evidence.
- **Value-proof kill:** a public/synthetic fixture cannot validate billable savings; the relevant private data are outside the authorized observation boundary.
- **Distribution/access kill:** the useful version requires a GitHub App, token, usage export, or customer-provided billing evidence, removing the proposed no-install advantage and introducing a genuine authorization gate before any representative proof.

No additional parser, dashboard, workflow scanner, or telemetry infrastructure is admissible for this candidate.

## Re-entry criteria

Re-open only if at least one of the following is independently observed:

1. a buyer provides a representative private Actions usage export and explicitly asks for an external audit that GitHub metrics do not answer;
2. a repeated, measurable waste mode is found that native GitHub metrics and named substitutes cannot detect;
3. an authorized private pilot permits before/after measurement of billable minutes and completion latency;
4. at least two unaffiliated buyers express willingness to try the exact read-only audit and one supplies a credible payment signal.

## Sources

- GitHub Actions billing and usage: https://docs.github.com/en/actions/concepts/billing-and-usage
- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub Actions metrics: https://docs.github.com/en/actions/concepts/metrics
- Viewing Actions metrics: https://docs.github.com/en/actions/how-tos/administer/view-metrics
- GitHub concurrency controls: https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs
- GitHub 2026 pricing changes: https://github.com/resources/insights/2026-pricing-changes-for-github-actions
- CICube: https://cicube.io/
- Runless: https://docs.runless.dev/
- CICosts: https://docs.cicosts.dev/
- MinuteMeter Marketplace listing: https://github.com/marketplace/actions/minutemeter-actions-cost
- Actions Usage Report Marketplace listing: https://github.com/marketplace/actions/actions-usage-report
- Trunk pricing: https://trunk.io/pricing
- BuildPulse: https://buildpulse.io/
- RunsOn testimonials: https://runs-on.com/testimonials/
- Buyer cost discussion: https://www.reddit.com/r/devops/comments/1jkgdiq/how_much_do_you_spend_on_cicd/
- CI frugality study: https://arxiv.org/abs/2410.15816
- 2026 caching study: https://arxiv.org/abs/2604.13129

## Governance

No customer data, account, token, GitHub App installation, private repository access, paid spend, outreach, publication, contract, KYC, runner migration, workflow mutation, or Privacy P0 activation occurred. This is a read-only commercial-discovery closure. The prior Solo Stack Continuity Auditor remains component-only; this screen does not reactivate it.
