# WRM PNCP Marketplace Feed — commercial screen

**Date:** 2026-10-26  
**Mission:** Waterfound Revenue Mission / WRM-T1  
**Candidate:** a paid Apify Actor that exposes filtered Brazilian PNCP procurement opportunities as a normalized, schedulable dataset for suppliers and integrators  
**Decision:** `BUYER_WTP_CONFIRMED / OFFICIAL_API_AVAILABLE / EXACT_ACTORS_ALREADY_LIVE / MARKETPLACE-DEMAND_WEAK / CHANNEL-BUYER_MISMATCH / NO_BUILD / CLOSED`

## Commercial predicate

Can Waterfound create differentiated, low-touch revenue by packaging public PNCP procurement data as a paid Apify Actor?

**Answer: no on current evidence.** The underlying Brazilian supplier problem has demonstrated willingness to pay, and Apify can collect usage-based revenue with low operator involvement. However, the exact Actor already exists in multiple implementations, with very low observed usage. The paying Brazilian buyer segment is served through WhatsApp, email, dashboards, document analysis, and bid-management workflows rather than developer-oriented Actor APIs.

## Why this candidate was attractive

The hypothesis initially matched several mission constraints:

- official public data;
- lawful and socially useful procurement transparency;
- no private customer access required for a basic feed;
- deterministic filters and source links;
- marketplace-provided usage metering and payouts;
- machine-operated recurring execution;
- no routine Waterfound involvement after publication.

Apify supports pay-per-event/pay-per-usage pricing and pays creators 80% of Actor revenue before platform costs. Its official materials state that some independent creators earn meaningful monthly recurring revenue. That validates the channel generally, not this Actor.

## Official source

The PNCP provides REST APIs intended for automated consultation and integration of public-procurement data under Brazil's Lei 14.133/2021. A basic feed can therefore use the official API rather than scraping pages.

This also makes the raw-data layer easy to reproduce and weak as a moat.

## Exact Apify substitutes

### Monitor de Licitações PNCP (Brasil)

Actor: `mateusalvescps/pncp-licitacoes-monitor`

- filters by keyword, UF, value, agency, and modality;
- positioned for daily alerts;
- price: USD 5 per 1,000 tenders found;
- observed store stats on 2026-10-26: 2 total users, 1 monthly active user, zero ratings;
- last modified 16 days before observation.

### Contratos públicos do Brasil (PNCP): quem ganha e quanto

Actor: `italosilveira/pncp-contratos-brasil`

- returns signed contracts, winning company, buyer, value, subject, signature date, and term;
- filters by state, keyword, and minimum value;
- price: USD 4 per 1,000 contracts;
- observed store stats on 2026-10-26: 2 total users, 1 monthly active user, zero ratings;
- last modified 3 days before observation.

### Additional direct Actors

Search also surfaced:

- `gbrum/radar-licitacoes-pncp` — open PNCP opportunities for n8n and datasets;
- `kman-br/licitacoes-br` — USD 0.90 per 1,000 returned tenders with rate-limit handling.

The exact marketplace wedge is therefore already occupied by multiple recent implementations.

## Buyer demand and WTP outside Apify

Brazilian suppliers demonstrably pay for procurement monitoring and workflow products:

- market comparisons cite PNCP-monitoring plans around R$97–R$197/month and broader suites above that range;
- Painel PNCP, LicitaPNCP, BidSys, OneLicita, Atlas Público, Nocton Radar, Licinexus, Pregonix, and others sell alerts, semantic matching, document analysis, competitor intelligence, pipeline management, and proposal support;
- official Contrata+Brasil already sends WhatsApp opportunity alerts to MEI suppliers.

This validates the market but reveals the channel mismatch. The paying buyer wants a ready operational outcome, typically through WhatsApp, email, or a web dashboard. The Actor customer is a developer or integrator, and current direct Actor usage is minimal.

## Residual differentiation test

Potential residuals considered:

1. CNAE/CNPJ-based opportunity matching;
2. ME/EPP/MEI eligibility flags;
3. document bundle extraction;
4. amendment/version change detection;
5. deadline alerts;
6. winner and price intelligence;
7. API-ready daily deltas and deduplication.

These do not justify a build now:

- CNAE matching and alerts are already offered by Brazilian SaaS products and Contrata+Brasil.
- Document analysis, semantic matching, and workflow management are established paid features.
- Winner/contract intelligence already has an Apify Actor.
- Basic deltas and deduplication are implementation features, not independent buyer evidence.
- ME/EPP eligibility can depend on item-level rules and legal documents; an inferred flag must not be presented as definitive eligibility.
- The exact developer marketplace has not shown enough usage to justify another near-identical Actor.
- Publishing and monetizing on Apify requires a new account/plan, public listing, payout onboarding, and acceptance of platform terms—genuine later gates, not justified by current evidence.

## Value-proof ledger

| Evidence class | Result |
|---|---|
| Public data access | Confirmed through official PNCP APIs |
| Broad buyer pain | Confirmed |
| Broad market WTP | Confirmed in Brazilian SaaS subscriptions |
| Apify monetization capability | Confirmed |
| Exact Actor differentiation | Failed |
| Exact Actor demand | Weak: direct substitutes show 2 users / 1 MAU each |
| Exact-job WTP | Not demonstrated by observed Actor usage |
| Customer outcome | Not measured |
| Revenue | USD 0 |

## Kill criteria

The candidate is closed before implementation because it fails:

- **Differentiation kill:** at least four direct PNCP Actors already exist.
- **Channel-demand kill:** direct comparable Actors show negligible adoption.
- **Channel-buyer fit kill:** paying SMB suppliers buy WhatsApp/email/dashboard outcomes, not raw Actor execution.
- **Distribution kill:** reaching that buyer would require a public SaaS, messaging integration, marketing, and support.
- **Authority kill:** Apify publication, paid Creator plan, payout onboarding, and terms acceptance are not currently justified or authorized.

No PNCP client, scraper, Actor, dataset, schedule, WhatsApp/email integration, dashboard, account, paid plan, or publication is admissible for this candidate now.

## Re-entry criteria

Re-open only if one of the following is observed:

1. a direct PNCP Actor reaches credible paid usage or repeated requests;
2. two integrators request a specific missing machine-readable dataset;
3. a measurable amendment/version-diff job remains absent from PNCP and all named products;
4. an authorized marketplace account can test a differentiated Actor without new paid spend;
5. external users demonstrate willingness to pay for a bounded API output rather than alerts, consulting, or bid operations.

## Sources

- Official PNCP API objective: https://pncp.gov.br/manual/pt-br/latest/objetivo/index.html
- PNCP official portal: https://www.gov.br/pncp/pt-br/
- Apify monetization: https://docs.apify.com/actors/publishing/monetize
- Apify pricing and Actor models: https://apify.com/pricing
- Apify creator earnings: https://help.apify.com/en/articles/8684010-make-money-publishing-your-actors-on-apify-store
- Direct PNCP Actor: https://apify.com/mateusalvescps/pncp-licitacoes-monitor
- Direct contracts Actor: https://apify.com/italosilveira/pncp-contratos-brasil
- Additional radar Actor: https://apify.com/gbrum/radar-licitacoes-pncp
- Additional PNCP Actor: https://apify.com/kman-br/licitacoes-br
- Contrata+Brasil: https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/contrata-brasil
- BidSys: https://bidsys.com.br/
- Painel PNCP plans: https://www.painelpncp.com.br/planos
- Market plan comparison: https://licitacerta.com.br/sistemas-de-licitacao

## Governance

No supplier profile, CNPJ lookup, personal data enrichment, tender recommendation, eligibility representation, proposal, bid, account, Actor, schedule, WhatsApp/email message, public listing, paid plan, payout setup, terms acceptance, spend, or Privacy P0 activation occurred. This is a read-only commercial-discovery closure. Revenue remains USD 0.
