# WRM Cloud/SaaS SLA Credit Preflight — commercial screen

**Date:** 2026-10-26  
**Mission:** Waterfound Revenue Mission / WRM-T1  
**Candidate:** a read-only preflight that correlates public provider incidents with official SLA terms, calculates likely service credits, and warns customers before claim deadlines  
**Decision:** `PAIN_AND_EXACT_WTP_CONFIRMED / WEDGE_OCCUPIED / PRIVATE_TELEMETRY_AND_CONTRACT_REQUIRED / HIGH-TOUCH-ENTERPRISE / NO_BUILD / CLOSED`

## Commercial predicate

Can a public-data SLA credit preflight recover or credibly estimate money for cloud/SaaS customers without private access, contractual interpretation, delegated claim authority, or ongoing human operations?

**Answer: no.** The problem and willingness to pay are unusually strong, including success-fee pricing tied to recovered credits. But the exact product is already commercialized. A defensible claim also depends on customer-specific contracts, architecture, resource identifiers, telemetry, invoices, impact evidence, and provider support channels. Public status pages alone cannot establish eligibility.

## Buyer/problem evidence

- AWS requires a service-credit claim through its Support Center, within a defined deadline, with incident timing and affected-resource information.
- Google Cloud SLAs require customer notification within short windows and calculate credits per project, region, instance, or service.
- Microsoft credit requests require tenant identifiers, the outage incident, affected subscriptions, and proof that the customer encountered the outage.
- A current Azure operator report describes finance and support teams struggling through the claim process after a production outage.
- A GCP operator explicitly asked for automation across many services because manually watching health pages, scraping logs, and opening support cases is burdensome.

The job is economically real: missed deadlines or incomplete evidence can forfeit credits already embedded in the customer contract.

## Exact willingness to pay

Unlike several prior WRM candidates, this category has explicit commercial pricing:

- **Complaya** charges an annual platform fee plus a **15–20% success fee** on credits or savings recovered. Its product extracts SLAs, monitors 190+ providers, compiles evidence, files claims, and tracks recovery.
- **Breachr** advertises a **10% success fee** when it detects a breach and estimates credit.
- **Opsio** sells managed SLA monitoring, credit calculation, claim filing, appeals, and reporting under flat monthly service tiers.
- These offers target procurement, finance, FinOps, and DevOps teams with measurable recovered dollars.

This confirms exact-category WTP. It does not leave an unoccupied product wedge.

## Direct substitutes

### Complaya

Complaya already performs the entire proposed workflow:

1. extract SLA terms from customer contracts;
2. monitor cloud and SaaS providers;
3. correlate violations to the customer's services and regions;
4. compile logs and evidence;
5. file claims;
6. reconcile recovered credits;
7. charge a success fee only on recovered value.

It supports AWS, Azure, GCP, Oracle, Salesforce, Microsoft 365, Google Workspace, Slack, ServiceNow, and many other vendors.

### Opsio

Opsio offers SLA Management as a Service with:

- definition of service-level objectives;
- continuous measurement;
- service-credit calculation;
- claim filing within vendor windows;
- appeals of denied claims;
- monthly and audit-ready reporting.

This is a managed-service substitute with human delivery contacts and enterprise governance.

### Breachr

Breachr reads contracts, monitors failures, produces claim evidence, estimates credits, and uses success-based pricing. It also offers direct audit help for customers needing more than software.

### Ontracko

Ontracko publishes vendor-specific SLA guides and free calculators for GCP, Cloudflare, Box, Elastic, Salesforce, Carta, dbt Cloud, Aiven, and others. These pages already occupy the low-friction public-data/SEO version of the wedge.

## Evidence boundary

A public provider status incident proves only that the provider acknowledged a service event. It generally does not prove:

- the customer's exact product or plan was covered;
- the customer's region, project, tenant, subscription, or resource was affected;
- the architecture met the SLA's redundancy conditions;
- customer-side configuration did not cause the failure;
- provider exclusions do not apply;
- the outage duration under the provider's contractual measurement method;
- the customer's monthly spend for the affected service;
- the correct credit tier;
- the claim was filed inside the applicable window.

Official requirements make private evidence unavoidable:

| Provider | Customer-specific evidence |
|---|---|
| AWS | Support case, timestamps, affected resources, region/instance basis, SLA-specific details |
| Microsoft/Azure | Tenant GUID, incident ID, affected subscriptions, proof of impact, billing route |
| Google Cloud | Project/region/instance or service scope, customer logs/metrics, timely support request |

## Narrow residual test

The remaining public-only product would be:

> a free alert and calculator that says an acknowledged incident may be claimable and links to the official SLA and deadline.

That residual is not a defensible revenue product:

1. Ontracko already publishes vendor guides and calculators.
2. Public status aggregators already alert on incidents.
3. Without customer telemetry, any dollar estimate is conditional and cannot be presented as money owed.
4. Recovering value requires private onboarding, contract ingestion, integration, claim authority, and reconciliation.
5. The monetizable market is enterprise and sales-led; Complaya asks prospects to book a demo, while Opsio bundles managed delivery.
6. Success-fee billing requires contractual acceptance, payment onboarding, audit of recovered credits, and dispute handling.
7. Claims and appeals are provider-facing external actions and can become legal/contractual disputes.
8. A synthetic fixture could validate arithmetic but not recovery, approval rate, operator-hours saved, or net revenue.

## Value-proof ledger

| Evidence class | Result |
|---|---|
| Problem evidence | Strong and current |
| Exact-category WTP | Confirmed by platform and success fees |
| Machine-readable public inputs | SLA terms and public incidents available |
| Customer-specific eligibility | Requires private contracts, telemetry, invoices, and architecture |
| Competitive differentiation | Failed; exact workflow already commercialized |
| Public/synthetic proof | Can test arithmetic only |
| Recovered credit | None |
| Operator-hours saved | Not measured |
| Claim approval rate | Not measured |
| Revenue | USD 0 |

## Kill criteria

The candidate is closed before build because it fails:

- **Differentiation kill:** Complaya, Opsio, Breachr, and Ontracko already cover both the enterprise and public/free forms.
- **Evidence kill:** public incidents cannot prove customer eligibility.
- **Autonomy kill:** useful operation requires private integrations, delegated authority, contracts, billing, claim filing, and exception handling.
- **Distribution kill:** the paying segment is enterprise and demo/sales-led rather than self-serve.
- **Value-proof kill:** no machine-admissible public fixture can establish an approved credit or recovered money.

No SLA parser, status scraper, calculator, dashboard, claim template, monitoring agent, provider integration, or sales asset is admissible for this candidate.

## Re-entry criteria

Re-open only if one of the following is independently observed:

1. an authorized customer supplies its exact SLA, bill, architecture, and incident telemetry for a bounded read-only audit;
2. a provider offers a public machine-verifiable claim API that eliminates delegated support access;
3. a materially underserved provider/segment lacks both calculators and recovery services, with at least two buyers requesting coverage;
4. a channel partner supplies distribution, contracts, and claim authority without requiring ongoing Waterfound operation;
5. a paid pilot permits measurement of claim preparation time, approval rate, recovered credit, and net value after fees.

## Sources

- AWS Compute SLA: https://aws.amazon.com/compute/sla/
- Google Compute Engine SLA: https://cloud.google.com/compute/sla
- Google Cloud Storage SLA: https://cloud.google.com/storage/sla
- Microsoft credit request requirements: https://learn.microsoft.com/en-us/partner-center/billing/request-credit
- Azure buyer pain report: https://www.reddit.com/r/AZURE/comments/1ol4mo0/azure_sla_credit_process_is_a_nightmare_has/
- GCP automation request: https://www.reddit.com/r/googlecloud/comments/1lu9xbn/anyone_automated_sla_tracking_and_autoclaiming/
- Complaya product: https://www.complaya.ai/
- Complaya pricing: https://www.complaya.ai/prices
- Complaya terms: https://complaya.ai/terms-of-service
- Complaya cloud product: https://complaya.ai/platform/cloud
- Opsio SLA service: https://opsiocloud.com/sla-as-a-service/
- Breachr: https://www.breachr.dev/
- Ontracko GCP calculator: https://ontracko.com/sla/gcp
- Ontracko vendor coverage example: https://ontracko.com/sla/cloudflare

## Governance

No customer contract, invoice, tenant, telemetry, resource identifier, provider login, support case, claim, appeal, delegated authority, outreach, demo, account, payment, subscription, legal representation, spend, or Privacy P0 activation occurred. This is a read-only commercial-discovery closure. Revenue remains USD 0.
