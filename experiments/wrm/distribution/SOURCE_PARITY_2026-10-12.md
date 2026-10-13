# RMA-DIST-001 — Primary-source paid-opportunity falsification (2026-10-12)

**Mode:** bounded public read-only research + zero-I/O source parity checks. **Candidate only**, not a product selection, commercial publication, buyer contact, invoice or recurring admission. Existing GE PR #46 owns product selection, PR #48 owns Commercial Progress Ratchet, PR #54 owns the original offline billing mock, and PR #56 owns recovery hardening. This sibling branch is based on exact PR #54 head `c7dfb23eaa236c38822d5879fe18f7eb91df0642`, without touching any of those writers.

## Why this check matters commercially

A paying-looking source is **not** a currently obtainable buyer. Two apparent distribution paths fail on independent primary-source inspection:

1. A publicly indexed $30 fixed-price Upwork permit-portal scraper job contains detailed acceptance work (all records and 20 fields, owner fallback, contact details, Google Sheet, unattended execution). The current linked Upwork page explicitly says **"This job is no longer available."** Its historical posted budget is evidence of the job category, not an open opportunity or a paid Waterfound contract. **KILL CURRENT BUYER OPPORTUNITY.** The private complete 20-field specification, lawful representative input corpus and authorized account/API are unavailable. The 20-field deliverable is not build-ready.
   - Historical indexed listing: https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/
   - Canonical page: same URL, now unavailable.
   - Upwork official bot policy: https://support.upwork.com/hc/en-us/articles/43342677368467-Use-bots-and-other-automation-properly
2. Algora still presents ProjectDiscovery `nuclei#6674` and `nuclei#6532` as **open $100 bounties** at https://algora.io/projectdiscovery/bounties?status=open; their canonical GitHub issues are **closed**:
   - https://github.com/projectdiscovery/nuclei/issues/6674
   - https://github.com/projectdiscovery/nuclei/issues/6532
   - **KILL THESE TWO CURRENT BOUNTY CANDIDATES.** Treat marketplace labels as leads requiring reconciliation, not as authoritative availability or guaranteed payment. No upstream contributions or claims attempted.

## Evidence-backed acquisition policy

- Upwork states unauthorized bots can be restricted and approved API scope does **not** authorize spamming proposals or scraping. Without an authorized account/API, automated Upwork acquisition is blocked: https://support.upwork.com/hc/en-us/articles/43342677368467-Use-bots-and-other-automation-properly
- Upwork Connects cost $0.15 USD each, with variable Connects required per listing: https://support.upwork.com/hc/en-us/articles/211062898-Understanding-and-using-Connects
- Freelancer Service Fee is **0–15% per contract**, the actual rate unknown until proposal/offer: https://support.upwork.com/hc/en-us/articles/211062538-Learn-about-the-Freelancer-Service-Fee
- Paid GitHub Marketplace app requires verified organization publisher and at least 100 GitHub App installs or 200 OAuth users: https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app
- Vercel Hobby explicitly excludes commercially deployed projects: https://vercel.com/docs/limits/fair-use-guidelines

## Bounded economics (not earnings, not product pricing)

The separate offline falsifier `/mnt/data/rma_dist_wave4/buyer_channel_falsifier.py` was run locally with 27/27 tests PASS and preserves hypothetical fixed-job sensitivity. Using a historical **$30 posted price**, hypothetical **8 Connects × $0.15**, $1 other variable costs and hypothetical $15/h total delivery opportunity cost, fee sensitivities 0%, 10%, 15% leave respectively **$27.80 / $24.80 / $23.30** before labor, taxes, FX, acquisition/support and refunds. Break-even delivery effort before labor cost is **111.20 / 99.20 / 93.20 minutes** respectively. None are observed profits and the job is not available now. **Do not combine these with the USD monthly SaaS subscription scenarios of PR #54.**

## Executed code and verification

- `source_parity.py`: deterministic, static-source-snapshot gate; primary closure overrides stale marketplace discovery; no network/personal data, payment, publication or authority.
- `test_source_parity.py`: **10/10 local PASS**, Python 3.13.5. Original 29 tests on the separate stacked PR #56 candidate were independently replayed and passed.
- The 27-test broader local channel/economic falsifier remains in its own local checkpoint, not versioned in this PR. This PR claims **only 10 newly versioned tests**; the 29 predecessor tests are separate. No CI check reported or accepted here.
- Git blob SHAs of source and tests locally match the GitHub copies: `451ac638f5652af081bc3a79fea34936dc4d41df` and `163f37fc4ddc86298288f0d5216152f06ac6dc98`.
- The output `current_screen` reports **three screened offers, zero currently available**, not **zero global opportunities**. Never infer a market-wide negative from this bounded screen. Snapshot requires fresh verification before making acquisition decisions.

## Channel ranking: factual gates, not a simulated conversion ranking

1. **CONDITIONAL:** Direct, legitimate inbound self-service with a merchant-approved commercially permissible host once CR-001 identifies a product and buyer proof. No live host/provider selected.
2. **CONDITIONAL:** OSS technical content / voluntary integrations as distribution; cannot by itself collect payment. Publication gate.
3. **BLOCKED FOR INITIAL PAID LISTING:** GitHub Marketplace paid app until verified organization + install/users threshold + commercial onboarding.
4. **BLOCKED FOR NEAR-ZERO-HUMAN ACQUISITION:** unattended Upwork proposals/scraping without explicit approved scoped API and separate contact authority.
5. **KILL STALE ENTRIES:** the two specific Algora listings with canonical closed issues; not a claim all bounties are closed.

## Ratchet handoff and terminal criteria

- `RMA_DIST_001_RESEARCH_VERIFIED`: **PARTIAL / source-backed** for this narrow public channel screen; no product-linked channel eligible.
- `RMA_DIST_001_ENGINEERING_VERIFIED`: **candidate source-parity tests ONLY**; billing mock remains separate PR #54/#56.
- `RMA_DIST_001_FIRST_REVENUE_PATH_READY`: **NOT MET**. CR-001 has no validated differentiated product or externally proven WTP; this screen found no current buyers among three sampled leads.
- `RMA_DISTRIBUTION_OPERATIONAL_VERIFIED`: **NOT MET**. No customer, real paid invoice, transfer, unattended wake or release.

**Next high-value frontier owned by CR-001:** verify a genuinely open buyer-paid job with lawfully reusable representative inputs, independently checkable acceptance outputs, at least two direct substitute screens and plausible near-zero-human acquisition. Until that exists, defer additional pricing/product UI engineering. RMA-DIST can produce independently verified source-parity evidence without modifying CR-001.

**UFP status:** no admitted RMA-specific recurring owner or actual wake receipt. A committed PR is a checkpoint, not autonomous execution. No credentials, work, paid spend, releases, upstream PRs, merges, runtime activation, new scheduler or external contacts.
