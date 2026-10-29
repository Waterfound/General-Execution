# WRM — Academic Reference Verification Artifact Screen — 2026-10-28

Status: **REPEATED_EXACT_BUYER_SIGNAL / MACHINE_TRIAGE_DIRECTLY_SUBSTITUTED / MANUAL_EDITORIAL_ACCEPTANCE / NO_BUILD**

Observed Waterfound revenue: **USD 0**

## Narrow job tested

Given a manuscript or reference list, produce a source-pinned table for each reference containing:

- authenticity/traceability state;
- corrected bibliographic metadata and DOI when confidently matched;
- unresolved or conflicting candidates;
- retraction/editorial-notice flags;
- duplicate references;
- in-text citations missing from the bibliography and unused bibliography entries;
- explicit provenance and no invented fields.

The initial hypothesis was that this bounded report might be delivered autonomously from a user-supplied document without privileged access.

## Current buyer evidence

The job is repeated and unusually explicit:

1. **US$10 fixed — Reference Verification and QA.** The buyer requests per-reference manual verification, corrected metadata, removal of confirmed fabricated references, in-text/list cross-checking and an Excel verification report with source and action fields.
   https://www.upwork.com/freelance-jobs/apply/Research-Assistant-Reference-Verification-and-Quality-Assurance_~022106339955276463099/

2. **US$100 fixed — Academic Referencing Check.** The buyer requests complete and correctly cited references throughout a submission-ready paper.
   https://www.upwork.com/freelance-jobs/apply/Academic-Referencing-Check-for-Paper_~022107608407092355730/

3. **US$5–15/hour — Legal and academic source verification.** The buyer requires exact page/date/quotation evidence, saved PDF or screenshot, accepts “not found,” and expressly forbids guessed or AI-produced citations.
   https://www.upwork.com/freelance-jobs/apply/Research-Assistant-Retrieve-and-Verify-Public-Legal-and-Academic-Sources-Accuracy-Critical_~022109020156379058238/

4. **US$30–250 — Mechanical APA standardization.** The buyer describes the task as purely mechanical: complete metadata, add DOI, align in-text citations and reference list across three manuscripts, and deliver tracking files.
   https://www.freelancer.com/projects/editing/apa-reference-standardization

5. **US$30–250 — Citation verification plus editing.** A completed project required verifying real/accessibile sources, removing or replacing fabricated references and delivering a submission-ready paper.
   https://www.freelancer.com/projects/academic-writing/finalizing-linguistics-research-citation

6. **Average displayed bid US$281 — comprehensive dissertation review.** Nine proposals were shown; reference verification included existence, bibliographic accuracy, DOI, claim support and fabricated-source detection, but the job also includes methodology, statistics and argument review.
   https://www.fi.freelancer.com/projects/data-analysis/comprehensive-msc-dissertation-review

Buyer/problem evidence is strong. It does not establish demand for Waterfound, completed payment to Waterfound, or a self-service product price.

## Direct substitution of machine-verifiable scope

The automatable core is already served:

- **Scite Reference Check** accepts a manuscript PDF and reports how every detected reference is cited, including retractions, editorial notices and contrasting findings.
  https://scite.ai/features
- Scite documents that the report maps manuscript citation statements to references; it also documents a known limitation: references without DOI or conventional scholarly metadata may be missed.
  https://scite.ai/blog/how-do-i-use-the-scite-reference-check
- Scite pricing begins at **US$12/month billed yearly**, with a free trial; its API exposes a reference-check endpoint.
  https://scite.ai/pricing
  https://scite.ai/api
- **Crossref Simple Text Query** matches pasted reference lists to DOIs, supports up to 1,000 references per submission and states there are no use limits.
  https://www.crossref.org/documentation/retrieve-metadata/simple-text-query/
- The public Crossref REST API exposes publisher metadata without sign-up, and the Retraction Watch dataset is available through the API and a daily-updated dataset.
  https://www.production.crossref.org/documentation/retrieve-metadata/rest-api/
  https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/
- A direct upload product already accepts TXT, DOCX and PDF manuscripts/reference lists.
  https://ref-check.org/Upload
- Wageningen University lists three free/open-source fabricated-reference checkers and explicitly warns that unresolved and non-DOI references still need manual review.
  https://support.wur.nl/esc/en/publish/preventing-and-detecting-fabricated-references?id=kb_article&sysparm_article=KB0018319

## Acceptance boundary

The paid tasks require more than metadata matching:

- inspecting original publisher or source records individually;
- confirming a DOI resolves to the intended work, not merely any record;
- verifying non-DOI books, chapters, law, policy and grey literature;
- deciding when absence of a match means fabricated versus unresolved;
- correcting the manuscript and in-text citations;
- judging whether a cited source actually supports a claim;
- exact page/quotation evidence;
- editorial style and domain judgment;
- responsibility for deletion or replacement decisions.

The US$10 buyer expressly requires manual review and prohibits treating automated tools as final evidence. Higher-priced jobs combine the report with editing, statistics, methodology or substantive fact-checking.

## Decision

Do **not** build a generic reference checker, DOI matcher, retraction flagger, fabricated-citation detector or manuscript reference dashboard.

A narrow automated triage would duplicate Scite, Crossref and free/open-source tools. It would not satisfy the buyers' manual/editorial acceptance predicate and could create false certainty around non-DOI or ambiguous sources.

Preserve the job as **SUPPORT_ONLY / service-demand evidence**. Re-enter only if a buyer explicitly purchases bounded automated triage, not complete verification, and a measurable gap against Scite/Crossref/free checkers is identified.

## Kill criteria reached

1. A direct commercial tool already uploads a manuscript and generates a reference report: **reached**.
2. Authoritative DOI and retraction data are available free: **reached**.
3. Free fabricated-reference checkers exist: **reached**.
4. Buyers require manual source inspection and editorial decisions beyond the machine artifact: **reached**.
5. The machine-only artifact has independent WTP above existing US$12/month substitution: **not observed**.

## Re-entry criteria

All must hold:

1. two current buyers request the same bounded automated artifact;
2. acceptance excludes claim-support judgment, deletion decisions and comprehensive manual assurance;
3. a public or consented fixture shows a decision-relevant gain over Scite and Crossref;
4. unresolved/non-DOI cases remain explicit unknowns;
5. privacy and document retention are disclosed and compatible with user expectations;
6. external contact, publication, account, contract and payment remain separately authorized.

## Evidence accounting

| Predicate | State |
| --- | --- |
| Buyer/problem evidence | Strong / repeated |
| Paid service evidence | Observed |
| Machine capability needed | No; direct substitutes answer the named predicate |
| Competitive differentiation | Falsified |
| Complete buyer acceptance automatable | Falsified |
| Waterfound WTT / WTP / revenue | None / none / USD 0 |
| Mission posture | Wedge closed; commercial discovery remains ACTIVE |

No manuscript was acquired or uploaded. No source was altered, no academic judgment was represented as final, and no outreach, proposal, account, publication, contract, payment/KYC, spend, runtime or Privacy P0 activation occurred.
