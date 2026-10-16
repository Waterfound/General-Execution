# WRM CI chronic-failure triage proof — 2026-10-16

## Decision

`SECONDARY_CANDIDATE / NARROW_SERVICE_PROOF / NO_PRODUCT_SELECTION`

Preserve one narrow job-to-be-done for further falsification:

> When a GitHub Actions gate is repeatedly red, identify the repeated root cause, distinguish a broken precondition from a code regression, and recommend the smallest fail-closed correction before the team changes CI policy.

This is not a CI monitoring dashboard, cost-control SaaS, generic DevOps audit, or claim that approvals or engineering hours were saved. The smallest proof is the read-only diagnosis below.

## Public fixture and method

- Fixture: Waterfound `General-Execution`, pull request branch `wrm/wrm-commercial-discovery-20261010`.
- Observation window: the latest 100 GitHub Actions runs returned by the public branch endpoint on 2026-10-16.
- Unit: 25 distinct tested revisions, four workflows per revision.
- Root-cause check: latest failed job steps, decoded job log, workflow source, and immutable-evidence branch tree.
- No repository setting, workflow, credential, account, payment path, or external system was changed.

## Measured outcome

| Workflow | Runs | Success | Failure | Summed visible elapsed | Mean visible elapsed |
|---|---:|---:|---:|---:|---:|
| Candidate public/private egress assurance | 25 | 25 | 0 | 405 s | 16.2 s |
| Canonical Constitution Gate | 25 | 25 | 0 | 391 s | 15.6 s |
| Main integration gate | 25 | 25 | 0 | 725 s | 29.0 s |
| Durable terminal verification | 25 | 0 | 25 | 693 s | 27.7 s |

Observed across the sample:

- `Durable terminal verification` failed on every tested revision: 25/25.
- The latest failure installed the package, compiled the source, and ran the full 748-test regression successfully before failing.
- The first immutable-evidence read then failed because `runtime/provider-host/generalized-pilot/first-runtime-report.json` does not exist on `runtime/durable-asp-control`.
- The expected `terminal-verification-report.json` was consequently never created, and the unconditional upload step emitted a second error.
- Inspection of the fetched evidence branch found none of the required `runtime/provider-host/{generalized-pilot,fae-snapshot-pilot,processed-snapshots}` or `provider-inbox/...` paths.
- The same sample contained 25 successful `Main integration gate` runs, so the repeated red status is not evidence that the current revisions fail their ordinary integration regression.

The four workflows account for 2,214 seconds of summed visible run elapsed in this sample. That figure is an observation, not billed minutes: workflows overlap, GitHub's accounting may differ, and this public repository does not establish a monetary saving.

## Finding and bounded correction

### Finding

The durable verifier currently performs expensive downstream work before checking the immutable external evidence on which its special-purpose assertions depend. The evidence branch no longer supplies the pinned paths, so each new pull-request revision repeats a known precondition failure after a successful full regression.

### Lowest-risk correction candidate

Keep the gate fail-closed, but move the immutable-evidence fetch and explicit path-existence preflight immediately after checkout and before Python setup, dependency installation, compilation, and the full regression. Upload a report only when the verifier has produced one; preserve the preflight failure itself as the terminal signal.

This ordering would not manufacture a pass, weaken the evidence predicate, disable the gate, or alter branch protection. It would stop known-missing evidence before redundant downstream computation. Because the workflow belongs to a broader mission and its missing artifacts may encode an intentional authority stop, this commercial proof does **not** apply the correction.

## Evidence classification

- **Capability:** verified for read-only run aggregation, step/log inspection, source reconciliation, repeated-root-cause classification, and bounded fail-closed recommendation.
- **Observed outcome:** one chronic red gate isolated from three healthy gates; 25 repeated failures mapped to one missing immutable input; downstream work and secondary upload error identified.
- **Competitive differentiation:** not established. Native GitHub Actions metrics already expose run time, queue time, usage, and failure rate. Pipetrics already offers read-only failure, retry, step, cost, and optimization telemetry.
- **Demand evidence:** adjacent paid demand exists for one-off GitHub Actions review/assessment work, including publicly indexed fixed-price buyer requests. Exact demand for this evidence format and correction boundary is not observed.
- **Willingness to try / WTP:** not observed for Waterfound.
- **ROI / revenue:** not measured; USD 0.

## Substitute boundary

GitHub's native organization metrics are sufficient to identify frequently failing or resource-heavy workflows. Pipetrics is a direct low-cost substitute for ongoing telemetry and optimization discovery, including a free tier and a listed Pro price of USD 10/repository/month as observed on 2026-10-16. Therefore monitoring, visualization, retention, alerts, and cost attribution are `SUPPORT_ONLY` and cannot be the wedge.

The only surviving hypothesis is a one-time, install-free, evidence-to-correction review that converts a chronic failure into a source-pinned root cause and a safe change boundary. This remains a service hypothesis, not a product claim.

## Falsification criteria

Kill the candidate if any of the following is established:

1. a buyer can obtain the same source-pinned root cause and safe correction from native metrics or a low-cost telemetry tool without material expert synthesis;
2. paid requests are for broad implementation/on-call ownership rather than a bounded read-only diagnosis;
3. value cannot be demonstrated without private billing, organization-level permissions, or a production mutation;
4. recommendations collapse into a generic checklist rather than one reproducible defect and correction boundary;
5. no independent willingness-to-try signal appears after targeted demand validation.

Promotion requires a representative non-Waterfound workflow, consented or public, where the report finds a reproducible repeated defect not already explicit in the native view, plus direct willingness to try. Pricing remains prohibited until value and willingness-to-pay are measured.

## Sources

- GitHub Actions branch runs: https://api.github.com/repos/Waterfound/General-Execution/actions/runs?branch=wrm%2Fwrm-commercial-discovery-20261010&per_page=100
- Latest diagnosed failed run: https://github.com/Waterfound/General-Execution/actions/runs/38924103578
- Workflow source: https://github.com/Waterfound/General-Execution/blob/wrm/wrm-commercial-discovery-20261010/.github/workflows/durable-terminal-verification.yml
- GitHub, “Viewing GitHub Actions metrics for your organization”: https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/viewing-github-actions-metrics-for-your-organization
- Pipetrics, GitHub Actions cost monitoring and optimization: https://pipetrics.com/
- Upwork, “Azure & GitHub Actions Reviewer / DevOps Consultant”: https://www.upwork.com/freelance-jobs/apply/Azure-GitHub-Actions-Reviewer-DevOps-Consultant-hours-fixed-price_~022099290780222011710/
- Upwork, “Azure and GitHub Consultant”: https://www.upwork.com/freelance-jobs/apply/Azure-and-GitHub-Consultant_~022108173016046661145/

## Mission posture

- `ACTIVE`: targeted buyer/problem validation for the bounded one-time review, and search for a representative public non-Waterfound fixture.
- `SECONDARY`: this single Waterfound proof; sufficient for capability, insufficient for demand or differentiation.
- `SUPPORT_ONLY`: dashboards, collectors, persistent apps, alerts, cost models, additional WRM instrumentation, and workflow mutation.
- `HUMAN_GATE`: none. No outreach, publication, installation, payment, or authority expansion is currently required while machine-admissible validation remains.
