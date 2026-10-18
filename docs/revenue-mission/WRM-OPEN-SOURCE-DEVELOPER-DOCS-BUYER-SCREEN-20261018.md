# WRM — Open-source developer documentation buyer screen — 2026-10-18

## Decision

`SINGLE_BUYER_SIGNAL / NOT_ADMITTED_FOR_BUILD / NO_PRODUCT_SELECTED`

The narrow job is not generic documentation generation. It is:

> From an existing public TypeScript codebase, prove that a new developer can set up and run one representative workflow, then explain the architecture and product flow with code-led examples and simple diagrams.

This job is commercially plausible, but the evidence currently supports one paid buyer only. It does not yet justify a Waterfound product or service build.

## Buyer evidence

### Upwork — AI/LLM eval product documentation

Source: [TypeScript Developer and Architect – AI, LLM Evals, Open Source — For Technical Documentation](https://www.upwork.com/freelance-jobs/apply/TypeScript-Developer-and-Architect-LLM-Evals-Open-Source-For-Technical-Documentation_~022100405311307593398/)

Observed from the indexed listing on 2026-10-18:

- posted 2026-09-17;
- fixed price: USD 500;
- intermediate, one-time, worldwide;
- buyer asks for review of an existing TypeScript codebase and developer-first, code-led documentation;
- requested outputs include architecture diagrams, setup guidance, step-by-step workflows, and end-to-end examples;
- activity: 20–50 proposals, 6 interviews, 1 hire;
- buyer profile: US small company, USD 40K total spend, 78 hires, 15 active.

This is real paid demand and one realized hire. It is not an available opportunity: a hire already exists. The listing does not identify the repository, and work "directly with the founder" implies private acceptance criteria and coordination.

## Substitute boundary

Native and adjacent tools cover large parts of the output:

- [Postman](https://www.postman.com/api-platform/api-documentation/) automatically generates and updates API documentation from OpenAPI definitions and collections.
- [Swagger](https://swagger.io/solutions/api-documentation/) generates, visualizes, and maintains API reference documentation.
- [GitBook](https://www.gitbook.com/) and other AI-native documentation systems support drafting, organization, and maintenance of developer documentation.

They do not by themselves prove that a clean newcomer can execute the documented setup and representative workflow at an exact source revision. That verification boundary is the only plausible differentiation found in this screen.

## Evidence classification

| Predicate | Result |
|---|---|
| Capability | Waterfound can inspect public repositories and produce source-pinned evidence without new credentials. |
| Observed buyer outcome | One USD 500 contract received 20–50 proposals, 6 interviews, and 1 hire. |
| Competitive differentiation | Possible only at executable onboarding verification; generic reference generation is substituted. |
| Demand evidence | One buyer; insufficient repetition. |
| Willingness to pay | Observed for the buyer's broader milestone contract, not for a standalone verification proof. |
| Revenue | USD 0. |

## Admission and kill criteria

Admit a smallest read-only proof only if all are true:

1. a second independent paid buyer requests materially the same code-led onboarding/architecture outcome;
2. at least one current buyer is unallocated or explicitly open to an additional deliverable;
3. a public repository or buyer-authorized source snapshot is available;
4. the deliverable can be evaluated without private credentials, publication, outreach, paid tooling, or contractual acceptance;
5. the differentiator is executable onboarding verification, not prose or generated API reference.

Kill or refine the hypothesis if:

- no second independent buyer is found in the next bounded marketplace screen;
- buyer demand consistently requires private founder sessions or undisclosed repositories;
- buyers accept generated documentation without executable verification;
- a native tool produces the same source-pinned setup proof and architecture trace.

## Next admissible frontier

Search for one additional paid, independently posted buyer whose requested acceptance outcome is reproducible onboarding from a public or buyer-authorized repository. Do not build a documentation generator, contact the buyer, submit a proposal, or publish a sample before the admission criteria pass.
