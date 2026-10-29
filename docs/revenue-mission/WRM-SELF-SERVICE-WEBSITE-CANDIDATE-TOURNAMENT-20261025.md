# WRM — Self-Service Website Candidate Tournament — 2026-10-25

Status: **THREE_CANDIDATES_SCREENED / THREE_DIRECTLY_SUBSTITUTED / ZERO_BUILDS / NO_PRODUCT_SELECTED / NO_HUMAN_GATE**

Observed Waterfound revenue: **USD 0**.

## Selection rule

This screen tests three self-service website jobs with an objective customer consequence and near-zero recurring Waterfound operation. Each candidate is rejected at the first commercially decisive substitute. A technically buildable website is not admitted merely because Waterfound can implement it.

## 1. App-store rejection preflight

### Buyer/problem evidence

Recent public developer reports describe repeated App Store rejections, inconsistent reviewer findings and multi-week delays:

- https://www.reddit.com/r/iOSProgramming/comments/1wclsll/3_rejections_10_business_days_on_third_submission/
- https://www.reddit.com/r/iOSProgramming/comments/1s0nb97/got_rejected_by_the_app_store_5_times_before/
- https://www.reddit.com/r/iOSProgramming/comments/1opbclo/stuck_in_an_app_store_review_loop_guideline_21/

Apple says incomplete submissions may be delayed or fail review and provides extensive review guidelines:

- https://developer.apple.com/distribute/app-review/
- https://developer.apple.com/app-store/review/guidelines/

### Direct substitutes

- Rork markets an AI App Store Reviewer covering safety, performance, business, design and legal:
  - https://rork.com/app-store-reviewer
- AppReviewer Preflight is already distributed through Apple's App Store:
  - https://apps.apple.com/ph/app/appreviewer-preflight/id6761920856
- LogicLine Labs published an open-source checker that scans Swift, Info.plist, entitlements and privacy manifests, maps features to Apple's guideline sections, and produces blockers, warnings and a manual checklist:
  - https://www.logiclinelabs.com/blog/tech/appstore-review-checker/
- AppCheck sells a local-browser Expo/React Native release-readiness report for EUR 11.99 one-time and exposes a free risk scan:
  - https://appcheckhq.com/
  - https://appcheckhq.com/pricing
  - https://appcheckhq.com/methodology

Decision: **KILL BEFORE BUILD**. The exact preflight format, local processing and source-linked findings already exist.

## 2. Two-face 3D coin asset generator

### Paid-category evidence

Fiverr exposes custom 3D coin, sculpting and spinning-logo services with listings beginning around USD 5–85 depending on the job:

- https://www.fiverr.com/

### Direct substitutes

- 3DLogo.io already provides browser upload, live materials, motion and exports to PNG, GLB, OBJ, STL, USDZ and MP4. Free exports include commercial rights with a watermark; paid plans remove it and add higher-resolution output:
  - https://3dlogo.io/
- 3DLogoLab/Coiny3D offers the exact 2D-logo-to-spinning-coin flow, exporting video, image or 3D model, with a free tier and a displayed USD 12.49/month Pro plan:
  - https://www.3dlogolab.io/3d-coin
- ProFounder advertises transparent 1080p spin-loop generation:
  - https://profounder.com/spin-loop/

Decision: **KILL BEFORE BUILD**. Waterfound's demonstrated sovereign-coin capability is not itself a commercial moat. The exact self-service transformation and deliverable formats are already free or inexpensive.

## 3. Mobile privacy-disclosure parity checker

### Problem evidence

Apple requires developers to disclose their own and integrated third-party data practices and keep the answers accurate:

- https://developer.apple.com/app-store/app-privacy-details/

Research finds high discrepancy rates:

- ATLAS reports that 88% of apps with both an accessible privacy policy and privacy label had at least one possible discrepancy:
  - https://arxiv.org/abs/2306.09247
- A separate large-scale study reports that 228,000 apps may disclose more linked data in policies than in labels and that 97% of sampled “Data Not Collected” labels conflicted with policy text:
  - https://arxiv.org/abs/2306.17063

These are possible discrepancies, not adjudicated legal violations.

### Direct substitutes and boundaries

- Privado's free/open-source scanner discovers data flows and generates Play Store Data Safety, Apple Privacy Manifest and Privacy Nutrition Label reports:
  - https://www.privado.ai/open-source
  - https://github.com/Privado-Inc/privado
- AppCheck already includes privacy findings, evidence locations and remediation guidance while processing code locally in the browser:
  - https://appcheckhq.com/pricing
  - https://appcheckhq.com/methodology
- Apple can generate an aggregate Xcode Privacy Report, but developers must still map the result to App Store disclosures and account for backend/server-side collection:
  - https://developer.apple.com/videos/play/wwdc2025/246/

Decision: **KILL AS A STANDALONE WEBSITE**. The machine-verifiable core is directly substituted by free tooling and a low-price local checker. The remaining gap requires complete knowledge of runtime, backend, SDK and legal context and cannot truthfully be sold as automated compliance.

## Consolidated evidence ledger

| Candidate | Pain/category | Direct substitute | Decision |
| --- | --- | --- | --- |
| App-store rejection preflight | Repeated rejection and delay reports | Rork, AppReviewer, open-source checker, AppCheck | Killed |
| 3D coin asset generator | Paid freelance design category | 3DLogo.io, 3DLogoLab, ProFounder | Killed |
| Privacy-disclosure parity | Mandatory disclosure and measured mismatch prevalence | Privado, Xcode report, AppCheck | Killed |

## Commercial conclusion

All three candidates are attractive because they are demonstrable, self-service and compatible with One Machine operation. All fail differentiation. None should receive engineering, publishing or payment work.

The strongest fresh lesson is that a generic website performing one transformation or one static audit is quickly commoditized in the 2026 market. A future candidate must own a consequence that cannot be recreated by a free local checker, a general AI assistant or a low-price upload tool.

## Next admissible frontier

Continue external buyer/problem research, but require before any prototype:

1. repeated buyer evidence for one exact outcome;
2. a measurable consequence larger than content generation or formatted findings;
3. a lawful self-service input path;
4. no equivalent free/local checker;
5. a plausible recurring or transaction-based value unit;
6. zero routine Waterfound operation.

No prototype, customer data access, account, outreach, publication, pricing commitment, paid spend, financial onboarding, payment/KYC, contract, Privacy P0 activation, merge or release occurred.
