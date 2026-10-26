# WRM Solo Stack Continuity Auditor proof — 2026-10-26

## Decision

**NARROW JOB SURVIVES SUBSTITUTION / SYNTHETIC PROOF PASS / DEMAND AND WTP UNVALIDATED / CANDIDATE_ONLY**

The surviving job is not a digital vault, dead-man switch, password manager, backup service, or generic governance dashboard.

> For a solo software founder, inspect a repository locally and identify repository-visible operational dependencies that are not covered by a documented successor or recovery route, without reading secret values or connecting to provider accounts.

The smallest read-only proof was built against a synthetic fixture. It emits a private metadata report plus a public SHA-256 attestation.

## Buyer and problem evidence

- KinSwitch identifies the solo-founder bus-factor problem explicitly: hosting, domains, payment processing, code repositories, client files, and infrastructure knowledge can become unreachable when the founder cannot act: <https://kinswitch.app/blog/the-solo-founders-emergency-plan-your-business-shouldnt-die-with-you>
- Its own guidance says the main maintenance risk is stale documentation after providers, passwords, and services change.
- GitHub's official deceased-user policy provides a path for account content but does not transfer login access: <https://docs.github.com/en/site-policy/other-site-policies/github-deceased-user-policy>
- AmberKey's July 2026 GitHub playbook documents the sharper technical gap: successors can handle public repositories but cannot access private repositories; sole-owner organizations, package registries, Actions secrets, deploy keys, and OAuth dependencies require a separate plan: <https://amberkey.app/docs/playbooks/github/>
- Stripe reported in May 2026 that high-performing solo-founded businesses are increasingly AI-native, global, and B2B, supporting a growing technical buyer segment: <https://stripe.com/blog/top-solo-founder-traits>

These sources establish a real problem and a plausible buyer segment. They do not establish demand for this exact auditor.

## Substitute reconciliation

### KinSwitch

KinSwitch stores encrypted notes/files and sends them after missed check-ins. Its founder-continuity workflow asks the user to write a manual infrastructure overview and review it quarterly. It does not publicly claim repository dependency discovery.

### AmberKey

AmberKey is the strongest adjacent substitute. Its free tier already provides a coverage map, client-side encrypted vault, printed recovery shares, export/import, fire drills, and per-service playbooks. Paid monitoring is US$79/year; the household tier is US$119/year: <https://amberkey.app/pricing/>

AmberKey instructs the user to inventory private repositories, sole-owner organizations, packages, Actions secrets, deploy keys, and OAuth identities. The observed public product surface does not claim to extract those signals automatically from a repository.

### Backups, password managers, and estate vaults

They solve storage, credentials, copies, or legal/delivery workflows. They do not prove that a current repository's operational dependencies are covered by a successor route.

## Differentiation that survived

The residual is **automatic, local, metadata-only discovery** that complements existing vaults:

1. scan code and workflow files without provider access;
2. record secret identifiers, never values;
3. identify schedules, external actions, domains, and provider signals;
4. compare observed dependencies with declared recovery controls;
5. output explicit gaps; and
6. emit a public digest that can attest to a private report without revealing it.

This is narrower than a continuity platform and materially different from asking the founder to remember every dependency.

## Proof result

The synthetic fixture contains:

- a scheduled GitHub Actions release;
- Vercel and npm signals;
- two secret identifiers;
- an external domain; and
- a partial continuity declaration.

Observed test result:

- **1/1 unit test PASS**;
- detected `NPM_TOKEN` and `VERCEL_TOKEN` identifiers without values;
- detected cron `17 3 * * 1`;
- detected `api.example.com`;
- detected Vercel and npm;
- identified missing private-repository recovery, restore-test evidence, and payment-processor recovery; and
- produced a 64-character SHA-256 public attestation.

This proves local extraction and gap comparison on one synthetic fixture only. It does not prove provider ownership, account access, backup validity, restore success, customer value, demand, or willingness to pay.

## Privacy and moral boundaries

- Read-only local input.
- No network calls in the proof.
- No GitHub/provider account installation.
- No secret-value collection.
- No credential escrow.
- No customer data.
- No death detection or automated release.
- No legal advice or representation that the report is an estate plan.
- A clean report must never be marketed as proof that recovery works.

## Value-proof plan

Before pricing, a representative authorized repository would need to measure:

1. dependencies found that the operator had not documented;
2. false positives and false negatives;
3. time required to produce the same inventory manually;
4. percentage of observed dependencies with a verified recovery route;
5. whether a second operator can complete a restore or handoff drill; and
6. report freshness after a real workflow/provider change.

No manual baseline will be fabricated. Only observable active minutes and natural comparable work count.

## Kill criteria

Close the wedge if any of the following occurs:

1. AmberKey, KinSwitch, GitHub, backup vendors, or a common open-source tool already performs equivalent automatic metadata discovery and recovery-gap comparison;
2. representative scans cannot achieve useful precision without provider credentials or secret values;
3. the report produces mostly generic checklist findings rather than repository-specific dependencies;
4. a second operator cannot use the findings to improve a real restore/handoff drill;
5. buyers treat the output as included free functionality of a vault/backup product; or
6. no external willingness-to-try signal appears after an authorized validation step.

## Current state

- Capability: **synthetic PASS**.
- Observed customer outcome: **none**.
- Competitive differentiation: **provisional; automatic local discovery survives initial substitution screen**.
- Demand evidence for exact job: **none**.
- WTP: **none**.
- Revenue: **US$0**.
- Status: **SECONDARY candidate**, not ACTIVE product and not HUMAN_GATE.
- Next admissible work: broaden public-fixture falsification and compare against open-source continuity/dependency scanners before any external validation gate.
- Privacy P0 producer: inactive and untouched.
