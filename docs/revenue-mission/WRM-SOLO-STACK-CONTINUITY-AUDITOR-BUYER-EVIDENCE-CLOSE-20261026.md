# WRM Solo Stack Continuity Auditor — buyer-evidence closure

Date: 2026-10-26

## Decision

**STANDALONE_CLOSED / FEATURE_RETAINED / ADJACENT_WTP_ONLY / DISTRIBUTION_MISMATCH / NO_FURTHER_BUILD**

The continuity problem is real. The evidence does not support the narrower repository-to-recovery auditor as a paid standalone product under Waterfound's One Machine / Full Autonomy constraint.

The proof remains useful as a bounded component or free diagnostic. It is no longer a SECONDARY commercial product candidate.

## Natural buyer/problem evidence

### Direct pain exists

1. A 2021 Hacker News question came from a one-person SaaS operator reporting more than USD 120,000 annual revenue and a stack spanning bank, cloud, API, Stripe, Git, database, analytics, DNS, and operational workflows. The founder explicitly asked whether a company or service could help with transition or even orderly shutdown. The thread received only two points and three comments; the actionable response was manual process documentation, cancellation dry-runs, screenshots, printed instructions, and family password access.
   - <https://news.ycombinator.com/item?id=27775899>

2. A June 2023 Indie Hackers question asked who would keep servers, domains, and customer-dependent SaaS operating after a solopreneur's death. It received five likes and two comments. The responses were indifferent or assigned continuity responsibility to customers unless the founder had already arranged a takeover.
   - <https://www.indiehackers.com/post/what-happens-to-your-saas-and-your-customers-when-you-as-a-solopreneur-pass-away-436466ed66>

3. A September 2026 r/SaaS discussion asked how solo founders with paying customers handle illness, vacation, support, and maintenance when buyers resist a single point of failure. The concrete advice was a runbook, shared ownership of critical accounts, health checks, alerts, tested backups, a status page, an offline-day drill, and later limited contractor coverage. No respondent requested or identified repository-derived continuity scoring.
   - <https://www.reddit.com/r/SaaS/comments/1vpclxw/business_continuity_for_solo_founders_after/>

4. In a detailed continuity interview, a solo infrastructure-product founder described the implemented solution: give a trusted friend GitHub access and instructions to open-source the product, then give family the 1Password emergency sheet. This is a natural manual substitute with very low tooling cost.
   - <https://wpproducttalk.com/podcast/beyond-the-grave-safeguarding-your-business-legacy/>

### Adjacent willingness to pay exists, but not for the exact job

A March 2026 Killswitch case study reports 30 paying customers at USD 99/year for a broader encrypted digital-estate/dead-man-switch product. This establishes adjacent WTP for secure legacy delivery. It does not establish WTP for repository metadata reconciliation.

The same founder identifies the binding commercial problem as procrastination and reluctance to confront mortality, not missing technical features. Reported acquisition work includes long-form content, frequent short videos, affiliates, niche influencers, and a search for a B2C SaaS sales co-founder. Product Hunt generated about 40 upvotes and almost no conversions.

- <https://saasbrowser.com/en/case-studies/1193580/killswitch>

This distribution requirement conflicts with the mission's near-zero Waterfound involvement constraint.

## Evidence classification

| Predicate | Result |
|---|---|
| Problem exists for solo SaaS operators | Supported by repeated public discussions |
| Existing behavior | Manual documentation, password managers, trusted people, runbooks, drills, contractors |
| Adjacent paid demand | Supported for encrypted legacy/dead-man-switch delivery |
| Demand for repository-to-recovery audit | Not observed |
| WTP for repository-to-recovery audit | Not observed |
| Autonomous low-touch acquisition | Contradicted by adjacent founder's reported education/content burden |
| Capability | Synthetic and one public fixture pass after bounded correction |
| Customer outcome / ROI | None |
| Revenue | USD 0 |

## Kill-criteria application

The standalone candidate meets two predeclared closure criteria:

1. **No repeated public evidence of payment for repository-to-recovery reconciliation.** Repeated pain exists, but paid evidence belongs to a broader encrypted delivery product.
2. **Acquisition requires routine founder education.** The adjacent paid operator reports that motivating users to confront the problem is harder than the software and is pursuing content, affiliates, influencers, and sales help.

It also faces strong low-cost substitution: the observed operators use documentation, password managers, shared access, trusted successors, drills, and limited contractors.

## Disposition

- Stop product expansion, pricing work, dashboards, provider integrations, hosting, and telemetry.
- Preserve the verified read-only code and evidence as a possible free diagnostic or component of a future continuity product with independently proven demand.
- Do not present adjacent Killswitch customers as demand for this feature.
- Do not claim saved time, reduced risk, successful recovery, ROI, demand, or WTP.
- Re-entry requires direct evidence that buyers already pay for repository-derived continuity verification, or a higher-value product where this diagnostic removes a measured bottleneck.

## Mission state

- Candidate status: `PASSIVE / STANDALONE_CLOSED / COMPONENT_ONLY`.
- Next frontier: select a different narrow job with stronger existing buyer behavior and machine-compatible distribution.
- Human gate: none.
- Privacy P0 producer binding: untouched and inactive.
