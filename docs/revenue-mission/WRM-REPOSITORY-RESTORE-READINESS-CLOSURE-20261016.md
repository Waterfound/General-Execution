# WRM repository restore-readiness closure — 2026-10-16

## Terminal decision

`CANDIDATE_KILLED / NO_PRODUCT_SELECTED`

Close both the repository-bundle restore-readiness wedge and its broader software-handoff/rebuild refinement as commercial candidates. Preserve the tested probe as `SUPPORT_ONLY` capability evidence; do not expand it into a product, backup platform, escrow service, or additional instrumentation.

## Predicate tested

Is there direct buyer evidence for an independent, repository-scoped restore acceptance report whose essential outcome is not already supplied by native backup tools, software-escrow verification providers, or ordinary DR consulting?

**Answer: no.**

## Evidence reconciliation

### Capability

The proof at `experiments/repository-restore-readiness/probe.py` passed synthetic clean-room tests for:

- Git bundle verification;
- disposable mirror restoration;
- strict object-integrity checking;
- expected branch/tag ref reconciliation;
- fail-closed handling of a missing expected ref;
- artifact hash and bounded evidence output.

This proves a narrow technical predicate only. It does not prove recoverability of issues, pull requests, settings, packages, Actions artifacts, LFS, secrets, infrastructure, data stores, deployment, or business service.

### Buyer/problem evidence

- Paid disaster-recovery work exists, but the located buyer language asks for system-wide procedures, credentials, backups, infrastructure rebuild, functional validation, handoff, and professional judgment.
- No direct paid request was found for the repository-only acceptance report after targeted searches across freelance jobs, consulting language, and repository backup/restore terms.
- Broader handoff demand is real, but its desired outcome is that another team can operate, deploy, and recover the complete system without the original supplier. That outcome necessarily expands beyond a read-only Git artifact.

### Direct substitutes

- GitProtect already provides GitHub/GitLab repository and metadata backup, granular and cross-platform restore, test restores, sandbox-to-production workflows, and audit-ready reporting.
- Software-escrow providers including Escode, Escrow London, and SES explicitly offer independent deposit verification, controlled build/rebuild testing, completeness checking, documentation, and continuity evidence.
- Source-code escrow verification is the established category for proving that deposited source material is complete and usable; the independent rebuild outcome is not an unserved Waterfound wedge.

### Demand, WTP, ROI, revenue

- Direct demand for this exact wedge: not observed.
- Willingness to try: not observed.
- Willingness to pay: not observed.
- Quantified buyer value or ROI: not measured.
- Revenue: USD 0.

Broader DR consulting rates and escrow-provider prices must not be attributed to the Waterfound probe.

## Kill-criteria result

| Criterion | Result |
|---|---|
| Direct repository-specific buyer signal | Failed |
| Gap not met by current backup tool | Failed for managed-tool buyers |
| Differentiation from escrow verification | Failed after broader handoff refinement |
| Read-only proof sufficient for buyer outcome | Failed; full recovery requires non-Git systems and privileged access |
| Autonomous low-touch path to value | Failed for the observed buyer outcome |

The candidate therefore cannot be promoted to `ACTIVE`. Additional metadata collectors, dashboards, integrations, or restore checks would be instrumentation around a commercially falsified wedge.

## Preserved value

Retain the probe and tests only as reusable internal/portfolio recovery evidence. They may support PBR or future authorized engagements, but they carry no current product, ROI, demand, WTP, or revenue claim.

## Sources inspected

- GitHub, “Backing up a repository”: https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository
- GitProtect GitHub Marketplace listing: https://github.com/marketplace/gitprotect-io
- GitProtect, “Disaster Recovery Testing For DevOps”: https://gitprotect.io/blog/become-the-master-of-disaster-disaster-recovery-testing-for-devops/
- Upwork, “Disaster Recovery Planning (DRP) Freelancers”: https://www.upwork.com/hire/disaster-recovery-planning-freelancers/
- Escode, “Software Escrow Testing & Verification”: https://www.escode.com/software-escrow/testing-and-verification/
- Escrow London, “Verification and Testing Services for Software Source Code”: https://www.escrowlondon.com/verification/
- SES, “Software Escrow Validation / Verification”: https://www.ses-escrow.co.uk/software-escrow-validation-verification

## Mission state

- Product selected: no.
- Revenue: USD 0.
- Current state: continue commercial discovery; do not classify the mission as `HUMAN_GATE` while machine-admissible research remains.
- Human action required: none.
