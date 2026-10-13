# RMA-DIST-001 — bounded first-revenue channel falsification

Scope: independently isolated candidate, derived from GE PR #56 at f31c582e1c98542a8aa618fb2cbbaa8d09e13f3d. No CR-001 selection or PR #48 ratchet mutation. No authority or commercial launch.

## Observed buyer budget, not product WTP

An Upwork buyer advertises USD 30 per accepted jurisdiction-specific building-permit scraper. The task requires complete pagination, missing-owner lookup, contractor company public-contact enrichment, 20 validated fields and unattended Windows execution. The full field-mapping rules are disclosed after hiring; no public acceptance fixture is available. Buyer job URL: https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/

## Legitimate customer acquisition gate

Upwork explicitly disallows unapproved automation, and an approved API is use-case limited; it does not grant permission for automated/spam proposals. Neither platform account nor outbound communication is authorized here. Upwork is BLOCKED for unattended acquisition under the present authority; this is not a conclusion that the buyer problem is economically worthless.
Official policy: https://support.upwork.com/hc/en-us/articles/43342677368467-Use-bots-and-other-automation-properly

Upwork contract-specific freelancer fees range 0%-15%; Connects cost USD 0.15 each. Neither actual fee nor required Connect count has been confirmed for this buyer job.
Official pricing: https://support.upwork.com/hc/en-us/articles/211062538-Learn-about-the-Freelancer-Service-Fee
https://support.upwork.com/hc/en-us/articles/211062898-Understanding-and-using-Connects

## Bounded hypothetical sensitivity (not actual margin)

Fixed source-observed job price: USD 30.00. Illustrative assumptions: 8 Connects, USD 1 miscellaneous variable cost and USD 15/hour all-in opportunity cost. Maximum all-in minutes (acquisition + delivery + testing + maintenance) before labor charge, excluding taxes, refunds, FX and other overhead:

| Platform fee scenario | Residual USD | Maximum minutes |
|---|---:|---:|
| 0% | 27.80 | 111.20 |
| 10% | 24.80 | 99.20 |
| 15% | 23.30 | 93.20 |

This does NOT establish actual profitability or rejection of the permit extraction job. It establishes the time/cost envelope under explicit unverified assumptions. Paid job != recurring SaaS demand.

GitHub paid Marketplace app is BLOCKED as first-revenue discovery/billing route because documented verified-publisher and 100 GitHub App installation prerequisites have not been satisfied: https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app

A free GitHub Marketplace Action is a separate CONDITIONAL_DISCOVERY_ONLY route with public-repo, release and terms requirements; it collects no payment by itself: https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace

## Reproducible local engineering evidence

The isolated local buyer_channel_falsifier.py (SHA256 a46714bb08bc317fc781c03550219bbc9585645621b6f991a9663a941f1b3428) and test_buyer_channel_falsifier.py (SHA256 e31de5c984ca2ce900345e2a1e0feb0bf20d6f4293480a66c007186eaa357e24) passed 18/18 local stdlib unit tests, Python 3.13.5. RED was 18 tests with three failures: unsupported self-attestation of a real sale and mutable prices misrepresented as externally observed. Fixed and GREEN 18/18. These exact sources are preserved in the local checkpoint package, not claimed as GitHub-versioned code or remote CI.

Verdict: KILL_UPWORK_UNATTENDED_ACQUISITION in current authority; HOLD_PERMIT_DELIVERY_UNPROVEN; NO_PRODUCT_SELECTED; FIRST_REVENUE_PATH_READY=false; revenue USD 0. New standalone infrastructure work is deprioritized versus CR-001 real-source deliverable evidence, currently PR #57. No contact, publication, paid spend, checkout, KYC, merging, scheduler or recurrent mission wake was performed.
