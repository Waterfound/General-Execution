# WRM persistent-runtime adoption — evidence-first preflight
Status: CANDIDATE_ONLY / NOT_ACTIVATED
Authority: Waterfound authorized Execution Protocol real run and bounded development/verification on 2026-10-09. This does not itself authorize scheduler activation, runtime repin, paid spend, credential/provider changes, public commercial release, or merge.

## Reuse instead of new infrastructure
- General Execution Durable Execution: existing atomic durable transition and recovery boundary.
- AB-001 PR #34: bounded event-driven continuation with fail-closed authority stops.
- AB-NRA-001 PR #36: merged native persistent-runtime host candidate; its source documentation explicitly excludes live host activation.
- WRM-T1 PR #38: merged evidence-first projection; does not establish customer ROI.
- WRM-T1 PR #42: design candidate for read-only trace ingestion; no canonical adoption.
- WRM-T1 PR #43: commercial execution and near-zero-One-Man gates candidate.

## Exact execution admission gate
Before any live WRM cycle, obtain machine-readable proof of:
1. current persistent-runtime source pin and host identity;
2. scheduler trigger, actual active/inactive state, execution lease and available free quota;
3. WRM-specific namespace, credentials, permitted paths and read/write scopes;
4. bounded transition cap, timeout, event receipt durability and recovery across interruption;
5. fail-closed stop at human/authority/credential/spend/external evidence/condition/scheduled/terminal boundaries;
6. dry-run and read-only rehearsal on exact current source, with trace hashes and independent verification;
7. no interference with FAE ACTIVE work or shared runtime budgets.
If any is missing, report UNKNOWN, remain NOT_ACTIVATED, and continue candidate-level work.

## Minimal WRM cycle (proposed, not live)
Observe current authorized WRM state -> reconcile receipts and constitution -> select one ACTIVE frontier -> run one bounded authorized transition -> persist immutable receipt -> re-observe fresh state -> verify -> checkpoint -> repeat only while admitted. Do not silently turn a conversational instruction into a background process.

## Acceptance
- Reproducible candidate tests for duplicate triggers, idempotence, lease expiry, crash recovery, stale source, human gate, provider unavailable, quota exhaustion and unauthorized spend.
- Exact SHA, workflow run ID, terminal state and receipts for any real host proof.
- Explicit separate authorization for scheduler activation or persistent-runtime repin after all preflight gates are GREEN.
- If genuine authority gate remains, batch minimal Waterfound action once, not repeated routine operations.

## Current factual status
Host candidate integrated; live WRM scheduler activation NOT VERIFIED. Commercial customer WTP, first revenue and ROI NOT ESTABLISHED. Do not claim unattended WRM running.
