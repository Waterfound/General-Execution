# WRM Repository Procurement Evidence Packet — screen

Date: 2026-10-26

## Decision

**PAIN_AND_WTP_CONFIRMED / EXACT WEDGE FALSIFIED / HUMAN_REVIEW_AND_CONTRACT_RISK / NO_BUILD / CLOSED**

Candidate job tested:

> Generate a low-cost procurement evidence packet for a solo B2B SaaS vendor from repository-visible evidence, reducing enterprise security-questionnaire work without claiming certification.

The buyer problem is valuable and paid. The repository-only solution is neither sufficiently complete nor safely autonomous. It was closed before implementation.

## Buyer/problem evidence

- A recent r/SaaS operator reports a third security questionnaire in one quarter, 150–300 questions each, consuming two to three days per questionnaire: <https://www.reddit.com/r/SaaS/comments/1qwznbv/saas_founders_selling_to_enterprise_how_do_you/>
- Another recent founder report describes 150–300 questions and one to two days of work whenever enterprise procurement starts: <https://www.reddit.com/r/SaaS/comments/1ux1jwa/founders_who_sell_to_enterprise_how_are_you/>
- Excalidraw stated in June 2025 that it pursued SOC 2 after repeated security questionnaires: <https://news.ycombinator.com/item?id=44362165>
- An operator with SOC 2 Type II reports that customers still require their own questionnaires even when the answers exist in SOC 2 and CAIQ material: <https://news.ycombinator.com/item?id=29098897>

These observations support real coordination cost and deal friction. They do not quantify the value attributable to a repository-derived packet.

## Paid substitutes and saturation

The category already has multiple evidence-backed automation systems:

| Substitute | Publicly documented capability |
|---|---|
| Vanta | Automated evidence collection, Trust Center, policy/control mapping, and AI questionnaire automation; the Plus tier includes 25 questionnaires/year |
| Conveyor | Knowledge-graph-backed questionnaire and RFP answers plus trust-center document sharing |
| HyperComply | Knowledge base from policies, audit reports, prior questionnaires and documents; AI autofill with human review |
| SafeBase / Drata | Trust Center, controlled evidence sharing and AI questionnaire assistance |
| Complies | Published low-cost entry from USD 119/month, importing CSV/text questions into an answer workflow |

Primary sources:

- <https://www.vanta.com/pricing>
- <https://www.vanta.com/products/questionnaire-automation>
- <https://www.conveyor.com/products/security-questionnaire-automation>
- <https://www.hypercomply.com/>
- <https://aws.amazon.com/marketplace/pp/prodview-v4iwswtkpxj6k>
- <https://complies.ai/security-questionnaire-software>

The visible price range and bundled products demonstrate WTP for the category, not differentiation for this candidate.

## Why repository evidence is insufficient

A repository can support truthful evidence about matters such as dependency manifests, workflow pinning, visible security policies, test configuration, and selected infrastructure-as-code. It generally cannot establish:

- actual production access and identity controls;
- encryption configuration and key custody;
- data retention, deletion, subprocessors, or data residency;
- incident-response operation and historical exercises;
- employee/contractor screening or security training;
- signed agreements, insurance, audit scope, or certification;
- whether written policies operate in practice; or
- answers scoped to a particular customer's architecture and data flow.

Therefore an automatically generated packet would be either thin and easily substituted or would require unsupported inferences. Unsupported affirmative answers could become contractual misrepresentations.

## Human-review incompatibility

Current practitioner evidence emphasizes a curated, approved knowledge base and human review before submission. A recent security discussion warns that incorrect questionnaire answers can become contractual problems: <https://www.reddit.com/r/cybersecurity/comments/1x7gtar/automating_security_questionnaires/>

This means the value-producing terminal step is not safely machine-admissible: an authorized representative must validate organization-specific claims before they are sent to a buyer. Customer-specific questionnaire intake and delivery would also require outreach, document exchange, and often NDA/contract handling.

## Falsification and disposition

The candidate fails three admission predicates:

1. **Differentiation:** evidence-backed questionnaire automation and trust centers are already crowded, including a published USD 119/month option.
2. **Completeness:** repository-visible facts cover only a minority of common questionnaire controls.
3. **Autonomy:** truthful submission requires organization-specific human review and may carry contractual consequences.

Disposition:

- no prototype, parser, trust center, questionnaire model, template pack, or pricing work;
- no claim that repository evidence proves compliance or security posture;
- no customer document ingestion, NDA, publication, outreach, or account creation;
- re-entry only if a narrower non-contractual job is found where repository evidence alone answers a buyer's complete predicate and existing tools do not.

## Evidence state

- Buyer pain: supported.
- Category WTP: supported.
- Exact-job demand/WTP: unverified.
- Product proof: intentionally not built.
- Customer outcome / ROI: none.
- Revenue: USD 0.
- Status: `PASSIVE / CLOSED / NO_BUILD`.
- Human gate: none; the candidate was rejected before a gate became current.
- Privacy P0 producer binding: untouched and inactive.
