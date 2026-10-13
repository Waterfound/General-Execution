# RMA-DIST-001 — Real paid workflow: public-data technical proof (2026-10-12)

**Candidate only. No buyer contract, product freeze, customer data, payment, rollout, merge, Work, credentials, external outreach or scheduler.**

## Why this is more than another synthetic monetization mock

An actual buyer publicly specifies a **USD 500 fixed-price, read-only audit** of an operating Google Sheets / Apps Script / Windows Python / serial-connected machine controller. Buyer-reported constraints include **390,000+ Sheets API calls**, **347,000+ value reads**, **40,000+ value updates** over 30 days, **4–5 minutes** of preparation latency and a desire to assess a 2x-machine expansion.

Primary buyer source:
https://www.upwork.com/freelance-jobs/apply/Automation-Engineer-Needed-Audit-Google-Sheets-Apps-Script-Python-Windows-Machine-Controller_~022105471245779183596/

**Evidence:** Actual posted budget and first-hand pain specification are observed. This is neither proof that Waterfound was hired nor that a seller identity/account is authorized. Public listing visibility is **not** verified current proposal eligibility, and the source code and timing traces needed to complete the buyer's requested audit are **private/unavailable**.

Adjacent distinct posted work:
- USD 500 Python REST automation job, generic / heavily competitive: https://www.upwork.com/freelance-jobs/apply/Automate-Website-with-API_~022107450255782019417/
- USD 75 Python messy-dataset cleaning job, no accessible real client dataset: https://www.upwork.com/freelance-jobs/apply/Data-Analyst-with-Python-Data-Cleaning-Analysis-Insights_~022102371915206715322/

These show posted budget for related skilled work, **not recurring SaaS WTP** or repeat buyers for a narrowly identical service.

## Specific independently testable buyer-value claim

Can a trustworthy technical audit establish root cause from only the buyer's 30-day totals? **No.** Google Sheets quotas are rate-windowed: documented per-minute rates are 300 reads/writes per project and 60 per user per project. An evenly distributed **347,000** calls across 43,200 minutes needs only **9 calls/minute** at the minimally possible peak; the same total could also include a severe spike. Thus the monthly volume does **not** establish minute quota exceedance or explain the reported 4–5 minute latency. Nor can exact unclassified call counts be obtained by subtracting independent *lower bounds*. An overconfident vendor would incorrectly claim a confirmed root cause.

Official sources:
- https://developers.google.com/workspace/sheets/api/limits
- https://developers.google.com/workspace/sheets/api/guides/batch
- https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchGet
- https://docs.cloud.google.com/apis/docs/monitoring

### Substitution screen (not parity)

1. **Google Cloud API Dashboard / Cloud Monitoring:** documented first-party request counts, response/error and latency metrics already cover much of generic API usage monitoring. Do **not** claim diagnostic telemetry is a differentiated product.
2. **Google Sheets batch requests/batchGet:** built-in features already consolidate API calls; no special proprietary optimization invented here.
3. **Sheetgo / Coupler.io:** documented scheduled spreadsheet integrations exist; substitutable workflow automation, though they do not by themselves prove ability to diagnose a serial hardware controller.

Only a **cross-stack, correlated, source-cited RCA and low-touch remediation plan** might be differentiated. It needs actual controller/Apps Script execution traces and a permitted independent acceptance benchmark. No root cause, performance gain or incumbent superiority is claimed.

## Engineering actually committed

`experiments/wrm/distribution/paid_workflow_probe.py`: network-free, stdlib-only source-bound numeric proof; distinguishes buyer-reported lower bounds, published Google quota, a mathematically possible even distribution, hypothetical batching reductions, and explicit unverified hypotheses. Hypothetical project economics retain fee and labor assumptions; no price or WTP freeze.

`experiments/wrm/distribution/test_paid_workflow_probe.py`: **16/16 passed locally against the exact uploaded blob SHA**; test both opposite burst counterexamples, disallow fake inferred quota/latency root cause, avoid subtraction of lower bounds, reject invalid economic parameters, prohibit buyer/revenue claims.

Exact blob IDs from independent local git-blob computation and GitHub retrieval:
- Source `0a291cb58e05069c7e2fd68fc4fbca7680f65c0a`
- Tests `cc34f589f6f46a0eec8ca68f593911634f650ce6`

An isolated worktree composed this exact source + test with sibling PR #56's code and PR #59's source-parity code and executed **55/55 tests PASS** locally. This is NOT a merge, GitHub CI, live webhook integration or owner-verified unattended execution. Sibling candidate heads were not altered.

Reproduce:
```sh
cd experiments/wrm/distribution
python -W error::ResourceWarning -m unittest -v test_paid_workflow_probe.py
python paid_workflow_probe.py
```

## Hypothetical USD 500 one-project sensitivity, not earnings

At eight **hypothetical** USD 0.15 Connects, USD 40 hypothetical nonlabor variable/support allocation, USD 15/hour hypothetical effort cost, platform fee assumptions 0/10/15%:
- Remaining before modelled labor: USD **458.80 / 408.80 / 383.80**.
- Break-even delivery hours: **30.59 / 27.25 / 25.59** respectively.
- Excludes refunds, legal cost, taxes, FX, verification, customer data and acquisition effort not modeled. The job is **not contracted**. No estimate of a real job's required engineering hours exists.

Official platform acquisition/fee policies:
https://support.upwork.com/hc/en-us/articles/43342677368467-Use-bots-and-other-automation-properly
https://support.upwork.com/hc/en-us/articles/211062898-Understanding-and-using-Connects
https://support.upwork.com/hc/en-us/articles/211062538-Learn-about-the-Freelancer-Service-Fee

Unapproved automated Upwork proposals and personal-data scraping remain prohibited. Publication/paid account creation/KYC/outreach remain out of scope.

## Commercial Ratchet handoff — no shared writer

- **PAYER_BUDGET_SIGNAL_OBSERVED:** YES, independently sourced USD 500 first-hand posted work, including measurable operational pain.
- **REAL_BUYER_ACCEPTANCE_PROVEN:** NO; no lawful client code/logs or exact independent truth-labeled target.
- **DIFFERENTIATION_VERIFIED:** NO; first-party telemetry and API batching already substitute generic components.
- **BUYER_WTP_FOR_WATERFOUND:** UNKNOWN.
- **LOW_TOUCH_ACQUISITION_VERIFIED:** NO; platform account and acquisition permissions blocked.
- `RMA_DIST_PAYER_WORKFLOW_EVIDENCE_VERIFIED`: **NOT MET** (requires much more than posted budget).
- `RMA_DIST_001_FIRST_REVENUE_PATH_READY`: **NOT MET**.
- `RMA_DISTRIBUTION_OPERATIONAL_VERIFIED`: **NOT MET**.

**Decision:** `GO_FOR_NEXT_PROOF` of a narrow read-only audit outcome only after a lawful representative input/trace and independent correct answer are available, otherwise `HOLD_MISSING_EVIDENCE`. Product-selection authority belongs to CR-001 / PR #46. The source-bound proof is an input to its Commercial Progress Ratchet PR #48, not a new selector. No user action now.

**Next independent direct commercial frontier:** seek another first-hand paid operational-audit case with openly licensed workflow traces, an independently verified root-cause outcome, and two directly testable substitutes. If unavailable, do not build generic dashboards or expand the payment mock.

**Durability:** draft branch and this checkpoint are resumable references, not an actual recurring wake. UFP mission readiness and owner receipt **not demonstrated**.
