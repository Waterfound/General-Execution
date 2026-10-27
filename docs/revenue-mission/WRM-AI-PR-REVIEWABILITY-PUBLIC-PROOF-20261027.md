# WRM-T1 AI PR Reviewability Packet — Public PR Proof

Date: 2026-10-27

Status: `TWO_REAL_PUBLIC_FIXTURES_CLASSIFIED / THREE_SCHEMA_GAPS_CORRECTED / DISTINCT_CAUTION_OBSERVED / MATERIALITY_UNPROVEN / DEMAND_AND_WTP_UNPROVEN`

## Commercial predicate

Can the narrow reviewability packet add a useful, evidence-bound decision to a real AI-authored pull request beyond the provider's native checks and review state?

This proof uses only public, read-only GitHub data. It does not contact the repository owner, change the pull request, install an app, or treat public activity as customer demand.

## Source-pinned fixture

- Pull request: <https://github.com/nspcc-dev/neofs-sdk-go/pull/902>
- Repository: `nspcc-dev/neofs-sdk-go`
- Author: GitHub Copilot coding agent
- Pinned head: `3a349502e105fafdbd861b760827d216c31c8cfc`
- Observed public state: 2026-10-27 at `15:49:02Z`
- Changed files: five files under `client/`
- Native checks at observation: `neofs-sdk-go tests = action_required`; `DCO check = action_required`
- Native review state: an approval followed by `CHANGES_REQUESTED`
- Inline review threads returned by GitHub: none
- Agent's own residual statement: in-stream wrapping had no end-to-end cancellation test
- Agent's own validation statement: `go vet` and `TestWrapCtxErr` passed, but the linter itself had not been run

The normalized fixture is `tools/revenue_mission/fixtures/public_neofs_sdk_go_pr_902_20261027.json`.

## What the first real fixture falsified

The synthetic schema missed two states present in the public PR:

1. **Review-level blocking without an inline thread.** `CHANGES_REQUESTED` can remain material even when the review-thread list is empty.
2. **Declared uncertainty outside a path heuristic.** The PR explicitly disclosed a missing end-to-end scenario, while none of its paths matched the prototype's static high-risk prefixes.

The smallest correction was made:

- accept and preserve `review_decision`, blocking on `changes_requested`; and
- accept and preserve `declared_uncertainties` independently of inferred path risk.

No provider client, dashboard, scoring system, workflow runtime, or additional instrumentation was added.

## Observed packet result

The pinned fixture produces `BLOCK` with:

- unsupported claim: `go vet and TestWrapCtxErr pass` is not independently supported by the named public test workflow because that workflow is `action_required`;
- blocker: native review decision remains `changes_requested`;
- blocker: public checks are non-passing;
- blocker: no explicit post-merge human owner is represented;
- residual uncertainty: the disclosed lack of an end-to-end cancellation test; and
- residual uncertainty: no linked agent session is present in the export.

The first bounded next action remains: obtain passing evidence for the claimed validation.

## Merge-validity control fixture

A second source-pinned fixture tests the opposite error: falsely blocking a PR whose native process accepted it.

- Pull request: <https://github.com/getsentry/sentry-for-ai/pull/45>
- Pinned head: `9de6d96a10d590a4af2c44e4ed9747d9bea67e7a`
- Human review: approved
- Public checks: `Validate Skill Tree`, `Secret Scan`, and `Warden`, all successful
- Inline review threads: none
- Native terminal outcome: merged on 2026-03-09 at `15:57:23Z`

The first prototype would have returned `BLOCK` solely because no explicit post-merge owner appears in the public export. That is not a defensible hard blocker for an otherwise approved, green, merged contribution. Missing human ownership is now preserved as an uncertainty; it does not independently create a blocker. The control fixture therefore returns `HUMAN_VERIFY`, with one verified claim and no blockers.

This produces a third schema correction: **unknown ownership is a verification question, not proof of inadmissibility**. Four deterministic tests now pass: two synthetic and two source-pinned public fixtures.

## Differentiation result

### Added beyond a native status glance

- separates an agent's validation claim from independently observed public checks;
- preserves an admitted test gap even though static path risk does not identify it;
- combines review-level state, checks, evidence gaps, uncertainty, and ownership into one bounded action.

### Differentiation remains unproved

For the active PR, the packet's final `BLOCK` agrees with native GitHub: checks require action and a changes-requested review exists. For the merged control, the packet adds `HUMAN_VERIFY` for missing ownership/session provenance even though native review and checks passed. That is a distinct caution, but its buyer value and materiality are unproved; it may simply be friction.

The wedge remains falsifiable: if representative buyers do not treat ownership/session provenance as decision-relevant, or if further accepted PRs repeatedly yield only this caution, close it rather than expanding implementation.

## Evidence classification

- **Capability:** a provider-neutral packet can represent this public PR without discarding review-level blocks or explicitly declared uncertainty.
- **Observed outcome:** one active blocked PR agrees with native state; one approved, green, merged PR is not falsely blocked.
- **Competitive differentiation:** distinct synthesis and a distinct caution observed; commercial materiality not observed.
- **Demand evidence:** none.
- **Willingness-to-try:** none.
- **Willingness-to-pay:** none.
- **ROI:** none.
- **Revenue:** US$0.

## Next highest-information test

Use one further source-pinned AI-authored PR with passing checks and approval, preferably with explicit session provenance or an ownership convention. The packet must either:

1. surface a material evidence/uncertainty/ownership condition not visible in the native disposition, without falsely blocking a valid change; or
2. agree that no distinct decision exists and count that result against the wedge's kill criterion.

Do not add more schema or heuristics unless that fixture exposes a named commercial predicate that cannot be represented by the current packet.

## Authority boundaries

- No outreach, comment, review, reaction, account installation, or external PR mutation occurred.
- No public commercial publication, payment/KYC, contract, paid spend, or irreversible commitment occurred.
- No Privacy P0 activation occurred.
- No global writer lease, state dispatcher, SQLite database, dispatcher bundle, or `DISPATCH_FENCE` was touched.
