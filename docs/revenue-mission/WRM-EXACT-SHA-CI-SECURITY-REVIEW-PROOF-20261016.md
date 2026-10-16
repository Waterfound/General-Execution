# WRM exact-SHA CI security review proof — 2026-10-16

## Commercial decision

`ACTIVE_CANDIDATE / NARROW_SERVICE_PROOF / NO_PRODUCT_SELECTION`

Refine the prior chronic-failure triage hypothesis to the sharper paid job:

> Independently review one changed GitHub Actions workflow at one exact 40-character commit SHA; verify scope, authority, input handling and matching CI evidence; return a one-page pass/fail report, required fixes and residual risk without changing code or accessing production.

This is not a monitoring product, security dashboard, generic maturity audit, penetration test, cloud assessment, or certification.

## Direct buyer evidence

On 2026-10-16, a current Upwork buyer listing requested this exact review-only outcome for a private Azure project:

- one workflow at exact SHA `2c4c47a1394453d15258d0c3665ce3574639e406`;
- confirmation that only the intended workflow changed and only approved read-only commands remained;
- exclusion of deployment, migration, restore, database writes, secret access, identity enumeration, artifact upload, debug output and raw error output;
- safe input validation;
- CI results matched to the reviewed SHA;
- one-page pass/fail report, required fixes and remaining risk;
- sanitized artifacts only, with no code change, production access, password or token request;
- USD 250 fixed price, one-time, expert level;
- 20–50 proposals, two interviews and two invitations shown.

This proves a buyer-posted budget and competitive interest for the exact job class. It does **not** prove completed payment, buyer legitimacy beyond the listing, selection of Waterfound, repeat demand, achievable margin, or willingness to hire a machine-produced report.

## Public fixture

- Repository: `Waterfound/General-Execution`.
- Reviewed commit: `3ed68361757b32d9797ca9bd6bcee7727062e5fd`.
- Parent-relative scope: exactly one added file, `.github/workflows/portfolio-backup-contract.yml`.
- Review inputs: exact commit diff, workflow source, GitHub Actions run receipts and job-step summaries.
- No workflow, repository setting, token, account, cloud resource or production system was changed.

## One-page review result

### Verdict

`FAIL_CLOSED_PENDING_HARDENING`

The reviewed workflow is test-only and the exact commit's four recorded workflow runs succeeded. It should not receive an unqualified security pass because two source-level controls are implicit or mutable.

### Acceptance checks

| Check | Result | Exact evidence |
|---|---|---|
| Reviewed object is bound to one exact SHA | PASS | `3ed68361757b32d9797ca9bd6bcee7727062e5fd` |
| Only intended workflow file changed | PASS | Parent-relative file list contains only `.github/workflows/portfolio-backup-contract.yml` |
| Commands are bounded to dependency install and one focused test | PASS | `pip install -e . pytest`; `pytest -q tests/test_portfolio_backup.py` |
| Deployment, migration, restore, database write or cloud command introduced | PASS — none found | No such step, action or credential reference in reviewed YAML |
| Secret access, identity enumeration, artifact upload, debug or explicit raw-error collection introduced | PASS — none found | No `secrets`, identity/API enumeration, upload action or debug flag in reviewed YAML |
| Untrusted event input interpolated into shell | PASS — none found | Only fixed matrix values `3.11`, `3.12`, `3.13` reach action input; no event-context expression reaches `run` |
| Token permission is explicitly least-privilege | FAIL | No workflow/job `permissions` key; effective token authority depends on repository default |
| Every action implementation is immutable | FAIL | `actions/checkout@v5` and `actions/setup-python@v6` are movable major-version tags, not full commit SHAs |
| CI results match reviewed commit | PASS | Exact-commit receipts show four successful workflows; the reviewed PBR workflow has successful jobs on Python 3.11, 3.12 and 3.13 |

### Required fixes before an unqualified pass

1. Add explicit workflow-level `permissions: contents: read` so the test job does not inherit a broader repository default.
2. Replace both action tags with reviewed full-length commit SHAs, retaining version comments for maintenance.

### Defense-in-depth, not pass blockers

- Set `persist-credentials: false` on checkout because later steps do not need Git authentication.
- Add `timeout-minutes` to bound stuck dependency installs or tests.
- Replace unconstrained dependency resolution with the project's approved reproducible dependency policy if the workflow becomes a release or privileged gate.

### Residual risk

The workflow intentionally installs and executes repository-controlled Python code on a hosted runner. For public fork pull requests, GitHub documents that `pull_request` runs receive a read-only `GITHUB_TOKEN` and no ordinary repository secrets; same-repository and push runs still depend on declared/default permissions. Explicit read-only permissions reduce consequence but do not make untrusted dependency or test execution harmless. A static source review also cannot prove runtime network behavior or package-registry integrity.

### Keep-merged opinion

The commit's workflow is already automatically dispatchable on matching pull requests and on pushes to its named branch, so “merged but undispatched” is not an accurate state. Keeping it present while applying the two source fixes is low risk relative to deployment workflows because it contains no secrets or cloud mutation steps and its recorded exact-commit runs passed. This is a bounded opinion for the reviewed SHA, not a guarantee about repository settings, future tags, dependencies or later commits.

## Substitute and differentiation screen

- GitHub's own guidance already recommends minimum `GITHUB_TOKEN` permissions and pinning actions to full commit SHAs.
- `zizmor` is a free, open-source static analyzer that detects excessive permissions, credential persistence, mutable/confusable references and template injection; some findings are auto-fixable.
- StepSecurity Community is free for public repositories and includes runtime monitoring plus automated SHA pinning and least-privilege permission remediation; private repositories are part of its paid platform.

Therefore static scanning, rule enumeration, SHA pinning and permission repair are `SUPPORT_ONLY`, not differentiation. The residual hypothesis is the exact-SHA evidence reconciliation and independent bounded judgment requested by the buyer: scope fidelity, negative-authority assertions, CI/SHA correspondence, pass/fail decision and residual-risk statement in one short deliverable.

## Second contextual fixture

To test whether the review adds anything beyond scanner findings, a second exact workflow-only commit was inspected:

- Commit: `b1836ee8da5357632e6436292aed66301d7940ed`.
- Scope: exactly one workflow modified, `.github/workflows/durable-launch-admission.yml`; two lines added.
- Change: fetch `main`, then require the pinned launch-admission source commit to be an ancestor of `origin/main` before executing it.
- Existing workflow authority: `contents: write`, receipt creation, commit and push to `runtime/durable-asp-control`.

### Second-fixture verdict

`FAIL_CLOSED_NO_EXACT_COMMIT_CI_EVIDENCE`

The two added commands are read-only and strengthen provenance by rejecting a pinned source not contained in current `main`. No new secret access, cloud mutation, artifact upload or write command was introduced by the diff itself. However:

1. GitHub returned zero associated pull-request workflow runs for the exact commit.
2. The modified workflow's trigger watches only new `launch-orders/*.json` and `constitutional-assessments/*.json` on its runtime branch; it does not include its own workflow path.
3. Therefore a source change to this write-capable workflow is not self-validating under its own trigger contract, and no CI result can be truthfully matched to the reviewed SHA.

Required correction boundary: add the workflow path to an appropriate non-mutating verification trigger or maintain a separate read-only verifier that exercises the workflow contract on workflow-source changes. Do not dispatch the write-capable runtime job merely to manufacture CI evidence.

This is decision-relevant context beyond the two generic scanner findings in the first fixture. A static YAML scanner can identify broad permissions and mutable action tags, but the exact-commit review also reconciled trigger coverage, associated run receipts, write authority and the distinction between safely verifying a mutation path and actually invoking it.

## Evidence ladder

| Predicate | State |
|---|---|
| Exact buyer-posted problem and budget | Observed: USD 250 fixed-price listing |
| Competitive attention | Observed: 20–50 proposals, two interviews shown |
| Public read-only delivery proof | Observed: two exact-SHA workflow reviews completed |
| Report finds decision-relevant issues | Observed: two source hardening blockers plus an exact-commit CI coverage gap on a write-capable workflow |
| Better than scanners alone | Partially observed: trigger/run/authority reconciliation added one contextual finding; no matched scanner run yet |
| Independent reviewer requirement accepts machine-assisted delivery | Unknown |
| Willingness to try Waterfound | Not observed |
| Waterfound WTP / sustainable fair price | Not established |
| Revenue | USD 0 |

## Kill criteria

Kill or reduce to `SUPPORT_ONLY` if any occurs:

1. the buyer outcome is satisfied by a scanner export without independent evidence reconciliation or judgment;
2. machine-assisted authorship cannot satisfy the independence/accountability requirement;
3. correct review requires private repository access beyond sanitized diff, CI links and reports;
4. a second representative fixture produces only generic scanner findings and no source-specific decision;
5. no additional direct buyer signal appears, or observed work consistently bundles implementation/cloud access that defeats the read-only low-touch boundary.

Promotion requires a second representative fixture plus external willingness to try. Pricing remains unselected: the USD 250 listing is buyer evidence, not a Waterfound price recommendation.

## Sources

- Upwork exact buyer listing: https://www.upwork.com/freelance-jobs/apply/Independent-Azure-GitHub-Actions-Security-Reviewer_~022106853401122567421/
- Reviewed exact commit: https://github.com/Waterfound/General-Execution/commit/3ed68361757b32d9797ca9bd6bcee7727062e5fd
- Matching PBR workflow run: https://github.com/Waterfound/General-Execution/actions/runs/37721751343
- Second reviewed commit: https://github.com/Waterfound/General-Execution/commit/b1836ee8da5357632e6436292aed66301d7940ed
- GitHub secure-use reference: https://docs.github.com/en/actions/reference/security/secure-use
- GitHub least-privilege token guidance: https://docs.github.com/actions/reference/authentication-in-a-workflow
- GitHub full-SHA pinning guidance: https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats
- zizmor quickstart: https://docs.zizmor.sh/quickstart/
- StepSecurity pricing and feature matrix: https://www.stepsecurity.io/pricing

## Mission posture

- `ACTIVE`: falsify the exact-SHA independent-review job against one additional representative public fixture and scanner parity.
- `SECONDARY`: this first public report and its evidence contract.
- `SUPPORT_ONLY`: the predecessor chronic-failure monitor, dashboards, collectors, persistent installation, automated remediation and generic security checklists.
- `HUMAN_GATE`: none currently. Outreach, proposal submission, account use, contract acceptance and private client access remain gated, but machine-admissible validation remains.
