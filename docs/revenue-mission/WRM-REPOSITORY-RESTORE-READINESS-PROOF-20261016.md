# WRM repository restore-readiness proof — 2026-10-16

## Decision

Keep **clean-room repository restore acceptance** as a narrow `SECONDARY` candidate. It has stronger buyer/problem evidence than the prior generic agent-ledger and SBOM screens, but not yet direct demand or willingness-to-pay evidence for this exact repository-scoped offer. Do not price, publish, or contact buyers yet.

The falsifiable job is:

> Given a buyer-controlled Git backup artifact and an expected ref inventory, prove in a disposable environment whether the artifact can be restored with intact Git objects and refs, while explicitly reporting repository data that the artifact cannot cover.

This is not a backup product, dashboard, or generic governance layer.

## Evidence boundaries

| Layer | Current evidence | Claim allowed |
|---|---|---|
| Problem | GitHub documents that backup methods cover different data; migration archives omit data and have no supported documented GitHub restore path. | Recoverability cannot be inferred from artifact existence alone. |
| Market | Upwork describes paid DR validation work, including controlled restore exercises and validation reports. | Buyers pay for broader recovery validation services. |
| Substitute | GitProtect provides repository/metadata backup, test restores, cross-restore, sandbox-to-production, and audit-ready reports. | Managed backup customers already have a strong native substitute. |
| Product proof | The local probe verifies a Git bundle, restores it into a disposable mirror, runs strict object checks, reconciles expected refs, hashes the source artifact, and emits JSON evidence. | The narrow Git-object/ref predicate is machine-testable without production writes. |
| Demand / WTP | No direct buyer request for the repository-scoped offer was found. | None. Broader DR rates are not WTP for this wedge. |
| ROI / revenue | Not measured. | None. |

## Smallest proof

`experiments/repository-restore-readiness/probe.py` accepts a local Git bundle and optional `refs/...=<object-id>` expectations. It:

1. verifies the bundle;
2. restores it into an automatically deleted temporary mirror;
3. runs `git fsck --full --strict`;
4. compares expected and observed refs;
5. records artifact SHA-256, timestamps, elapsed time, checks, and limitations;
6. fails closed when an expected ref is absent or different.

The proof never writes to the source bundle or any remote. The synthetic tests create a disposable repository with two branches and a tag, prove the pass path, then prove a missing-ref failure.

## Differentiation and substitution

The only plausible differentiation is an independent, tool-neutral acceptance report for teams that already possess DIY/exported artifacts and do not want to install or replace their backup system. This is narrower than full DR consulting and avoids competing as another backup scheduler.

The wedge is **not** differentiated for buyers already using GitProtect or an equivalent product with test restore and audit reports. It also does not cover issues, pull requests, settings, packages, Actions artifacts, or LFS objects without separate evidence inputs and tests.

## Kill and promotion criteria

Kill or close the candidate if any of these becomes true:

- no direct repository-recovery buyer signal appears after a bounded demand screen;
- target buyers predominantly use managed tools that already produce equivalent restore evidence;
- buyers require private credentials or production writes before the predicate can be tested;
- the requested outcome is full application/service DR rather than repository artifact acceptance;
- the proof cannot be extended to metadata coverage without becoming another backup platform.

Promote to `ACTIVE` only after at least one independent buyer signal requests or budgets a repository-scoped restore validation/report and identifies a gap not met by its current backup tool. A real buyer artifact, credential, installation, outreach, publication, contract, or payment remains a Waterfound gate.

## Sources inspected

- GitHub, “Backing up a repository” (accessed 2026-10-16): https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository
- GitProtect, “Disaster Recovery Testing For DevOps” (accessed 2026-10-16): https://gitprotect.io/blog/become-the-master-of-disaster-disaster-recovery-testing-for-devops/
- GitProtect GitHub Marketplace listing (accessed 2026-10-16): https://github.com/marketplace/gitprotect-io
- Upwork, “Disaster Recovery Planning (DRP) Freelancers” (accessed 2026-10-16): https://www.upwork.com/hire/disaster-recovery-planning-freelancers/

## Next commercial predicate

Search only for direct repository-specific requests or procurement language that requires an independent restore exercise, ref/metadata completeness evidence, or audit-ready recovery proof. Do not expand implementation until that predicate is answered.
