# WRM — Unattended agent operations: first-hand pain vs substitutes (2026-10-11)

**Evidence class:** public, unverified first-hand community statements + primary vendor documentation. **No customer interview, paid intent, market size or product validation.** This is a *buyer/problem* discovery result, not permission to build.

## First-hand observations (do not generalize)
- 2026-10-09 public report: https://www.reddit.com/r/ClaudeAI/comments/1x1cltw/i_ran_an_autonomous_coding_pipeline_for_two_weeks/
  - Author reports an autonomous coding pipeline producing 67 agent-authored PR merges in two weeks, then being shut down after 129 maintenance PRs, 3,000 GitHub Actions minutes exhausted in about 3.5 days, and a two-day silent stoppage; reports separating untrusted-content-reading agents from privileged actors. **These are self-reported, not independently audited metrics.**
  - Replies independently describe silent backup/scheduled-job failures, local-runner migration after exhausting Actions allowance, dead-man's switches, budget alerts, and privileged-boundary concerns. These are anecdotes, not customer demand or proof of representativeness.
- 2026-09-20 public report: https://www.reddit.com/r/ClaudeCode/comments/1wl1zr8/how_long_do_your_prs_take_you/
  - One developer reports repeated agent/reviewer repair loops and longer time to merge in a Go repository; no controlled baseline, no monetary attribution, no purchasing intent.
- 2026-09-07 author describes a CLI that detects headless permission-related CI hangs and false-green outcomes: https://www.reddit.com/r/ClaudeCode/comments/1wa5rcj/i_built_a_tiny_cli_that_finds_claude_code_jobs_in/
  - **This is also a competing solution**, not just a pain report.

## Substitution checks against the observed jobs
1. **Missing scheduled runs / heartbeat monitoring** is already a commercialized category: Cronitor explicitly monitors scheduled agent tasks, missing runs, delayed runs, outputs and custom cost metrics (https://cronitor.io/cron-job-monitoring); multiple independent alternatives exist. **KILL generic dead-man's-switch as an original wedge.**
2. **GitHub Actions budget exhaustion alerts** already exist natively. GitHub documentation describes included-usage alerts at 90%/100% and configurable budgets/limits (https://docs.github.com/en/billing/concepts/budgets-and-alerts). **KILL generic Actions budget-warning product.**
3. **PR recovery next-action synthesis** is strongly substituted by pr-shepherd (https://github.com/jonathanong/pr-shepherd), as independently documented in WRM-PR-SHEPHERD-SUBSTITUTION-20261011.md. **KILL generic PR digest.**
4. **Headless permission-prompt misconfiguration** has at least one free purpose-built scanner (https://github.com/Onur45500/hangnone). **Do not assume unique demand for a permission-hang checker.**

## Residual commercial question (not a product decision)
A recurring pain may be **accepted-outcome assurance**: an unattended agent pipeline can report a healthy heartbeat, completed checks or many PRs while failing to produce the *intended* accepted result, consuming resources or crossing authority boundaries. Existing monitors cover much of this, so a hypothetical differentiator would require:
- exact user-defined acceptance predicate;
- independently fetched read-only source/result evidence, not self-reported agent status;
- explicit distinction between no execution, execution without accepted delta, genuine external gate, and unauthorized transition;
- no invasive control-plane migration, low integration friction;
- demonstrable safe decision beyond existing native tools, Cronitor, pr-shepherd, and other monitors.

This is **HYPOTHESIS_ONLY**. It is not evidence that buyers will pay or that we should build it. The founder's own engineering experience is not independent customer demand.

## Ratchet next step
Before any new code, identify at least **two independent, identifiable payer roles** describing *the same* costly accepted-outcome failure, not just general agent frustration. Then check a first-party incumbent's exact product contract for that failure and test whether independent evidence is available without customer credentials. If these predicates fail, discard the accepted-outcome assurance idea and prioritize vertical workflow automation or specialized operational intelligence. Do not contact prospects without authorization.

Commercial delta: documented a specific pain class with dated first-hand reports, falsified three tempting generic wedges via actual substitutes, and narrowed the surviving question to accepted outcomes. **Demand, WTP, pricing, ROI, customer count, and revenue remain UNKNOWN/NONE.**
