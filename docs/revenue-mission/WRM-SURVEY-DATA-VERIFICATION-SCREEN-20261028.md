# WRM — Survey Data Verification Buyer Screen — 2026-10-28

Status: **PAID_SERVICE_DEMAND_OBSERVED / DIRECT_FREE_AND_NATIVE_SUBSTITUTES / CUSTOM_JUDGMENT_DOMINATES / NO_BUILD / DISCOVERY_ACTIVE**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound offer a global, self-serve website that accepts a survey dataset plus explicit validation rules, checks duplicates, skip patterns, quotas and illogical responses, and returns a corrected file plus source-row audit report—without privileged platform access, invented corrections, specialist certification or recurring human operation?

This is one bounded job selected from current buyer-posted evidence. It is not a broad idea list.

## Buyer evidence

A Freelancer project advertised **USD 250–750** for verification of completed market-survey data. The requested work was to:

- cross-check answer validity, skip patterns and quotas;
- identify duplicates and illogical responses;
- document every correction;
- return the corrected file in its original format;
- provide a separate verification report.

Source: https://www.fr.freelancer.com/projects/data-cleansing/market-survey-data-verification

This proves budgeted marketplace intent for a custom service. It does **not** prove award, completed payment, repeat volume, willingness to use an automated Waterfound product, or willingness to upload potentially sensitive respondent data.

Adjacent fixed-price CSV services advertise auditable cleaning and validation at **USD 60–180**, but are generic data preparation rather than survey-logic assurance.

Examples:

- https://www.upwork.com/services/product/development-it-a-clean-validated-csv-with-an-auditable-change-report-2113740952289171078
- https://www.upwork.com/services/product/development-it-clean-consistent-excel-or-csv-data-with-a-clear-validation-report-2113690600085756952

## Native and direct substitutes

### DataSure

Innovations for Poverty Action provides DataSure as a free, open-source, local web application. It:

- accepts SurveyCTO data or uploaded CSV, Excel and Stata files;
- runs locally and opens in a browser;
- requires no programming for its intended users;
- checks duplicate identifiers, missing data, outliers, enumerator performance, GPS values, survey progress and backcheck discrepancies;
- tracks corrections with an audit trail.

Source: https://data.poverty-action.org/data-quality/datasure/

Repository: https://github.com/PovertyAction/datasure

The documented current version is 0.8.0, and the public package is MIT-licensed. Its explicit limitation is highly customized checks beyond the built-in modules.

### SurveyCTO

SurveyCTO lets teams configure automated value, outlier, frequency, mean and group-distribution checks. It runs them automatically, accumulates warnings, and exports a CSV quality-check report with human-readable warnings, machine identifiers, fields, values, row IDs and group IDs.

Source: https://docs.surveycto.com/04-monitoring-and-management/02-managing-for-quality/02.monitoring-quality.html

### Established research workflows

J-PAL documents skip-pattern, missingness, duplicate-ID, outlier, enumerator and fraud checks as standard high-frequency data-quality practice, with templates and implementation guidance.

Sources:

- https://www.povertyactionlab.org/resource/data-quality-checks
- https://www.povertyactionlab.org/resource/data-cleaning-and-management

IPA also publishes the mature Stata-based `ipacheck` toolchain for duplicates, missingness, constraints, outliers, comments, timing, survey summaries, enumerator performance and backcheck comparison.

Source: https://github.com/povertyaction/high-frequency-checks

## Residual hypothesis tested

The only plausible residual is **vendor-neutral post-collection validation of custom skip, quota and cross-field rules from user-supplied files**.

That residual does not yet justify a product proof:

1. the buyer asks for careful custom review, not a reusable rule format;
2. platform-native and open-source tools already cover the standard checks;
3. custom skip and illogical-response rules require a correct questionnaire specification and domain interpretation;
4. an arbitrary rule engine is generic data validation, not survey-specific differentiation;
5. no evidence shows that a buyer would replace the custom service with a Waterfound rule schema;
6. survey exports may contain sensitive or regulated respondent data, creating privacy and security obligations before commercial value is established.

A synthetic checker could trivially detect planted duplicates and rule violations, but that would prove only implementation capability. It would not answer the commercial predicate or outperform the existing tools.

## Decision

**KILL BEFORE BUILD.**

Do not build:

- a generic CSV cleaner;
- a duplicates/missingness/outlier dashboard;
- a SurveyCTO clone;
- a generic YAML/JSON rule engine presented as a survey product;
- a hosted upload service for respondent data;
- an automated “verified dataset” or research-quality claim.

Preserve the candidate as **SECONDARY** only for a sharper re-entry condition.

## Re-entry criteria

Re-enter only if all are true:

1. at least two independent buyers request the same post-collection rule artifact;
2. their acceptance criteria can be represented without bespoke domain interpretation;
3. a representative de-identified fixture and fixed truth set are available;
4. DataSure, SurveyCTO and generic validators cannot produce the required row-level decision;
5. local/browser-only processing can avoid transferring respondent data;
6. one measurable advantage is specified in advance—active review minutes, violation recall, provenance coverage or correction error rate;
7. the output remains a factual issue report, not a certification of statistical or research validity.

## Evidence ledger

| Predicate | State |
| --- | --- |
| Buyer/problem | One marketplace scope with USD 250–750 budget |
| Exact acceptance artifact | Corrected dataset + verification report |
| Standard-check capability | Already covered by free/open-source and native tools |
| Custom-rule differentiation | Unknown; not evidenced by buyer repetition |
| Public/synthetic capability proof | Not run because it cannot resolve the commercial predicate |
| Privacy-safe self-service path | Possible only with local/browser processing; not validated |
| Waterfound WTT/WTP | None |
| Quantified ROI/value | None |
| Revenue | USD 0 |

## Active–Secondary–Passive decision

- **ACTIVE:** find a bounded buyer artifact whose decisive output is not already covered by a free local tool or native platform.
- **SECONDARY:** custom post-collection survey logic, pending repeated buyer evidence and a common rule representation.
- **PASSIVE / SUPPORT_ONLY:** generic CSV cleaning, duplicate/missingness/outlier checks, dashboards, rule engines, hosting, runtime and telemetry.

## Next machine-admissible frontier

Continue with current buyer-posted scopes, but require **two repeated buyer signals for the same acceptance artifact** before any new proof. Prefer non-sensitive public or browser-local inputs and a deterministic output. Do not infer product demand from service budgets alone.

No dataset was uploaded or processed. No website, account, outreach, proposal, publication, checkout, card/crypto integration, payment/KYC, spend, contract, runtime activation, private producer activation, writer lease, dispatcher, SQLite write or DISPATCH_FENCE action occurred.
