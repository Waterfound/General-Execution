# WRM — SBOM Veracity and Completeness Screen — 2026-10-16

Status: **SCREEN_NEGATIVE / DIRECT_BUYER_EVIDENCE_ABSENT / GENERIC_VALIDATION_COMMODITIZED / NO_BUILD / NO_PRODUCT_SELECTED**

This screen tests whether independent, read-only SBOM validation is a commercially admissible Waterfound wedge. It uses public sources only. It is not a security assessment, compliance opinion, legal interpretation, customer validation, or evidence of revenue.

## Narrow job considered

Given a public repository, release artifact, and supplied SPDX or CycloneDX SBOM:

1. validate the document against current minimum-element and schema requirements;
2. determine whether declared components and dependency relationships are structurally usable;
3. flag absent or degenerate dependency graphs and undeclared completeness;
4. bind findings to the exact release/SBOM artifacts;
5. emit a factual acceptance memo without modifying the repository or claiming regulatory compliance.

This job is machine-testable on public artifacts and would not require credentials before proof.

## External problem evidence

- The joint **2026 Minimum Elements for an SBOM** guidance adds current fields, practices, and processes for producers, procurers, and operators.  
  https://www.cisa.gov/topics/information-communications-technology-supply-chain-security/sbom
- OWASP guidance recommends reconciling inventories with final packages or container images rather than treating manifests alone as shipped truth.  
  https://cheatsheetseries.owasp.org/cheatsheets/Dependency_Graph_SBOM_Cheat_Sheet.html
- A 2026 empirical study of 78,612 wild SBOMs reports 52.9% with no dependency edges and another degenerate regime with mostly isolated components. This is research evidence of artifact-quality problems, not buyer demand or willingness to pay.  
  https://arxiv.org/abs/2607.22140

## Buyer evidence search result

Targeted current searches did **not** surface a paid buyer requesting an independent SBOM completeness/veracity memo, artifact-to-SBOM parity test, or dependency-graph acceptance report. The marketplace result that mentioned a software bill of materials used the term for infrastructure purchasing inventory, not software-supply-chain SBOM validation.

Regulatory relevance and research prevalence do not substitute for an observable payer, available opportunity, willingness to try, or Waterfound WTP.

## Direct substitutes

| Substitute | Relevant public capability | Commercial effect |
| --- | --- | --- |
| `interlynk-io/sbomqs` | Scores SBOM quality and compliance; supports CISA 2026, NTIA, BSI, FSCT and other standards; exposes CLI/library automation and shareable results. | Directly substitutes generic minimum-elements, field-quality, identifier, signature and compliance checks. |
| FOSSA NTIA SBOM Validator | Free online CycloneDX validator with minimum-requirements checks and dependency-graph visualization/validation. | Commoditizes basic upload-and-report validation. |
| CycloneDX specification and tools | Models direct/transitive dependency graphs plus composition completeness states including complete, incomplete and unknown; provides a large tool ecosystem. | Makes graph/completeness representation a standard feature, not a proprietary differentiator. |
| SPDX/OpenSSF conformance tools | Existing conformance checkers validate minimum fields and standard structure. | Substitutes schema/minimum-elements checking. |
| Syft, cdxgen, Microsoft SBOM Tool and other generators | Generate inventories from repositories, directories, archives, containers and binaries at different lifecycle phases. | Substitutes much of discovery and artifact scanning. |
| SBOM-unifier research implementation | Deterministically merges and enriches heterogeneous SPDX outputs across tools. | Weakens generic multi-generator enrichment as a unique claim. |

Sources:

- https://github.com/interlynk-io/sbomqs
- https://github.com/interlynk-io/sbomqs/blob/main/docs/reference/compliance-standards.md
- https://fossa.com/resources/regulatory-compliance-tools/ntia-sbom-validator/
- https://cyclonedx.org/specification/overview/
- https://cyclonedx.org/tool-center/
- https://openssf.org/blog/2023/03/02/how-to-make-high-quality-sboms/
- https://arxiv.org/abs/2608.30708

## Commercial interpretation

A residual technical problem exists: schema-valid SBOMs may still be inaccurate or incomplete relative to the shipped artifact. However:

1. generic conformance and minimum-element validation are already free or open source;
2. graph presence, quality scoring, completeness declarations, and multi-tool comparison already have dedicated tooling;
3. artifact-to-SBOM parity work moves into build reproduction, security review, supplier assurance, or regulated procurement consulting;
4. no current paid buyer was found for a standalone independent memo;
5. legal/compliance positioning would require qualified judgment beyond a narrow factual checker.

The screen therefore fails the buyer-first admission rule. A synthetic comparator would answer a technical predicate that existing tools already address while leaving the commercial predicate unanswered.

## Decision

Do not build:

- a generic SBOM schema/minimum-elements validator;
- a CISA 2026 checklist or compliance score;
- a dependency-edge presence/degeneracy dashboard;
- a multi-generator merge/enrichment tool;
- a generic public-repository SBOM quality memo;
- a regulatory-compliance claim.

Re-entry requires all of:

1. a fresh, identifiable payer explicitly requests independent artifact-to-SBOM parity or completeness verification;
2. exact release artifacts and SBOMs are public or explicitly authorized;
3. the buyer defines an objective acceptance predicate not already answered by `sbomqs`, FOSSA, CycloneDX/SPDX validation, or ordinary artifact scanners;
4. the work remains factual and does not require legal/compliance opinion;
5. the opportunity is available, low-contention, and can be proven privately before outreach or payment onboarding.

## Evidence classification

- **Capability:** public sources were sufficient to falsify generic validation before implementation.
- **Observed outcome:** current standards and substantial public quality problems exist.
- **Differentiation:** generic SBOM validation is falsified as unique.
- **Demand:** regulatory relevance only; direct paid buyer evidence absent.
- **Waterfound willingness to try / WTP / revenue:** none / none / USD 0.
- **Mission posture:** continue buyer/problem discovery; no human gate.
