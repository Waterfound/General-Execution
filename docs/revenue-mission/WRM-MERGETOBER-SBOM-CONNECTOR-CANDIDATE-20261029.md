# WRM Mergetober SPDX/CycloneDX connector candidate — 2026-10-29

## Decision

**Admit one narrow Mergetober proposal candidate, but stop before public issue creation or code.**

Candidate job-to-be-done:

> Turn a local SPDX or CycloneDX software bill of materials into stable, searchable Cognee documents for components, dependencies, licenses, hashes and already-present vulnerability records, without following external URLs or requiring credentials.

This is a prize-channel candidate, not a Waterfound product wedge. It is selected because the current TestSprite surface remains saturated by author-owned defects while Mergetober offers a larger current prize pool and explicitly permits new integration proposals.

## Official payoff and admission rules

Official organizer evidence:

- Campaign: 1–31 October 2026.
- Prize pool: USD 5,000.
- USD 2,000 top-contributor prize.
- Twenty USD 100 prizes selected randomly from entrants with a merged PR submitted through the form.
- The PR must be opened in October.
- Only integrations are eligible.
- Existing issues require assignment first; new integrations may be proposed through a new issue.
- No code or PR may be started before assignment. Violating that rule can ban the participant.
- Each PR requires its own public real-world blog post.
- Solo submission; prize belongs to the GitHub account that authored the PR.
- Winners may need to provide payment/shipping details and handle tax/customs.

Primary source:

- https://www.wemakedevs.org/hackathons/mergetober/rules
- https://www.wemakedevs.org/hackathons/mergetober/resources

This proves a conditional prize route. It does not prove assignment, merge, selection, payment, or realized revenue.

## Canonical issue availability reconciliation

The live GitHub API was queried for every open issue carrying both `INTEGRATIONS` and `hackathon` in `topoteretes/cognee` on 2026-10-29.

Observed result:

- 100 open labeled issues returned on the first complete page.
- **All 100 have at least one assignee.**
- Several external indexes still rendered stale “No one assigned” snapshots.
- Candidate examples that looked free in search results—Todoist, Substack, Box, YouTube, Rollbar, Mixpanel and Pipedrive—are assigned and/or already have competing PRs.
- The Box issue is assigned to `GunaPalanivel` and already has PR `topoteretes/cognee-community#380`.
- TestSprite's current open hackathon issues likewise retain original-author provenance or prepared patches.

Therefore Waterfound must not claim or implement an existing labeled issue.

## Duplicate and substitute check

Searches across the current `topoteretes/cognee` issue/PR corpus and `topoteretes/cognee-community` PR corpus found:

- no issue titled or scoped as an SPDX connector;
- no issue titled or scoped as a CycloneDX connector;
- no SBOM connector PR;
- adjacent security connectors for OSV, deps.dev, CISA KEV and Dependabot, which enrich advisories but do not ingest a customer's local bill of materials.

Generic JSON ingestion is the primary internal substitute. The proposed connector is only differentiated if it preserves SBOM-native identities and relationships instead of treating the document as arbitrary JSON. If maintainers judge generic JSON sufficient, kill the candidate immediately.

## Standards evidence and narrow format boundary

Primary standards:

- SPDX is an international standard; its current specification is 3.0. SPDX models components, provenance, licenses, vulnerabilities and relationships:
  - https://spdx.dev/use/specifications/
  - https://www.omg.org/spec/SPDX/3.0
- CycloneDX 1.7 explicitly models components, services, dependencies, compositions and vulnerabilities:
  - https://cyclonedx.org/docs/1.7/json/
  - https://github.com/CycloneDX/specification/blob/master/schema/bom-1.7.schema.json

Proposed v0 boundary:

- Local files only; no crawling and no external-reference fetches.
- CycloneDX JSON 1.5–1.7.
- SPDX 2.3 JSON plus SPDX 3.x JSON-LD when the official `@graph` shape is present.
- Full-snapshot semantics: every run replaces one scoped SBOM corpus, so removed components disappear through Cognee's existing orphan cleanup.
- Stable component key preference: `purl` → SPDX ID / CycloneDX `bom-ref` → deterministic document-local fallback.
- One root document plus one searchable document per component/service/vulnerability.
- Dependency relations rendered deterministically in each component document; do not claim exact native graph-edge preservation unless Cognee's accepted integration contract provides it.
- Hard size/count bounds and deterministic validation errors.
- Never follow URLs or read paths referenced inside the SBOM.

## Repository compatibility screen

Read-only repository:

- `topoteretes/cognee-community`
- screened head: `377205d3bbef65cc3443671007d342dc9af15701`

Observed connector contract:

- package under `packages/connector/<name>/`;
- `README.md`, `pyproject.toml`, import package, examples and tests;
- document sources mark `DOCUMENT_SOURCE_ATTR`;
- full-snapshot sources use `write_disposition="replace"`;
- Cognee's existing `orphan_cleanup` removes rows absent from the next scoped snapshot;
- incremental sources use `merge`, `_deleted` and `hard_delete`, which are unnecessary for a local immutable snapshot v0.

No code was written because the official rules prohibit work before assignment.

## Proposed issue text

### Title

`[Feature]: Add SPDX/CycloneDX SBOM data-source connector (Mergetober)`

### Body

> ### Problem
>
> Cognee can ingest generic files, but an SBOM is a typed dependency inventory. Treating SPDX/CycloneDX as arbitrary JSON loses stable package identities, dependency relations, licenses, hashes and vulnerability-to-component links that an agent needs for questions such as “which runtime component depends on this package?” or “which shipped components carry this license or recorded advisory?”
>
> ### Proposed integration
>
> Add `packages/connector/sbom/` in `cognee-community`, following the document-source connector contract.
>
> - Auth: none; local files only.
> - Inputs: CycloneDX JSON 1.5–1.7, SPDX 2.3 JSON, and SPDX 3.x JSON-LD with the official `@graph` shape.
> - Output: a scoped root document plus stable component, service and vulnerability documents.
> - Identity: purl first, then bom-ref/SPDX ID, then a deterministic document-local fallback.
> - Relationships: deterministic dependency/contains summaries attached to the relevant documents.
> - Sync: full snapshot with `write_disposition="replace"`; removing an item from the next SBOM removes its stale Cognee document through existing orphan cleanup.
> - Safety: never fetch external references or paths embedded in the SBOM; bounded files/components and explicit validation errors.
>
> ### Acceptance checks
>
> - Official SPDX and CycloneDX fixtures parse offline.
> - Components, versions, purls, licenses, hashes, dependencies and embedded vulnerability records are searchable.
> - Duplicate refs and dependency cycles terminate deterministically.
> - Malformed/unsupported documents fail before partial publication.
> - A second snapshot that removes a component removes its stale document without affecting another scoped SBOM.
> - README includes a runnable local example and explains the difference from generic JSON ingestion.
> - Unit tests require no account, token, network or paid service.
>
> I searched open/closed Cognee issues and cognee-community PRs for SPDX, CycloneDX and SBOM and found no existing connector proposal or implementation. If this fits the integration roadmap, please add the `INTEGRATIONS` and `hackathon` labels and assign it to me before implementation, per the Mergetober rules. @NMZivkovic

## Commercial evidence classification

### Capability

Waterfound can inspect the public architecture, standards and fixtures without credentials or spend. No implementation capability is claimed yet because coding before assignment is forbidden.

### Observed outcome

A live enumeration showed no unassigned official labeled issue. Duplicate search found no SPDX/CycloneDX/SBOM connector in the target issue or PR corpora. The public repository pattern supports a bounded local-file snapshot connector.

### Competitive differentiation

Differentiation from generic JSON is conditional on preserving SBOM-specific identity, scope and relations. Adjacent advisory connectors are complements, not substitutes. Maintainer rejection on “generic JSON is enough” kills the candidate.

### Demand / WTP

The organizer offers conditional prizes for merged integrations. No buyer interview, customer demand, product WTP or guaranteed payout is established.

### Revenue

Realized revenue: **USD 0**.

## Kill criteria

Kill without implementation if any occurs:

- maintainers do not assign the issue before an October PR can realistically be opened;
- a duplicate issue/PR appears;
- maintainers judge generic JSON ingestion sufficient;
- accepted scope requires hosted credentials, private SBOMs, external crawling or paid infrastructure;
- accepted scope requires exact dependency graph edges unsupported by the connector contract;
- a truthful public blog and submission cannot be completed within authority and deadline;
- expected payoff becomes non-positive after publication, payout and tax/onboarding requirements.

## Current bounded gate

Publishing the new GitHub issue and requesting assignment is external commercial publication/outreach. It is not authorized by the standing envelope. Coding is also forbidden by the event until assignment.

Exact action requiring Waterfound authority:

> Authorize publication of the prepared SPDX/CycloneDX Mergetober issue to `topoteretes/cognee`, limited to the title/body above and assignment request; no code, fork, PR, blog, account creation, payment/KYC, spend or contractual acceptance.

After assignment, implementation remains machine-admissible except for any separately required public PR/blog/submission and payout onboarding gates.

## Privacy boundary

No issue, comment, claim, fork, branch, PR, blog, registration, account, credential, payment/KYC, spend, contract or irreversible commitment was created. The Privacy P0 candidate was not activated or touched. No writer lease, dispatcher, SQLite, dispatcher bundle or `DISPATCH_FENCE` was used.
