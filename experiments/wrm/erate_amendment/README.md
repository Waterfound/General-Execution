# CR-001 — Executed E-Rate amendment impact probe (12 Oct 2026)

**Classification:** `TECHNICAL_PROBE_VERIFIED / COMMERCIAL_SELECTION_NOT_ADMITTED`.
**Owner ancestry:** GE #46 `5920b02299edc37abb8fd39f70b8168c99a4c911` → GE #53 `9741bc67a4aea0a3bf1b0b2265b48243545f9a4f`. No changes to these owner branches.
**Code:** `experiments/wrm/erate_amendment/amendment_impact.py`, one-source offline command:

```sh
cd experiments/wrm/erate_amendment
python -m unittest -v test_amendment_impact.py
python amendment_impact.py oregon_2025_grounded.json
```

## Observable buyer pain and independent public source

- [Buyer-posted E-Rate / RFP Procurement Intelligence App](https://www.upwork.com/freelance-jobs/apply/RFP-Procurement-Intelligence-App_~022099679983526658973/) explicitly asks to ingest USAC Form 470, associated RFPs/attachments/addenda, score opportunities and give a bid team source links. This is **buyer-authored project demand**, not a Waterfound purchase. This listing does **not** establish a verified spend amount for Waterfound.
- [USAC E-rate Form 470 tool and public API](https://www.usac.org/e-rate/service-providers/step-2-responding-to-bids/) support public service requests/RFP document discovery; [USAC Open Data](https://opendata.usac.org/) advertises broad public reuse. Source access alone does not prove distribution or a differentiated product.
- [Oregon Buys official historical bid](https://oregonbuys.gov/bso/external/bidDetail.sda?docId=S-P03012-00012701&external=true&parentUrl=close) #S-P03012-00012701, FCC470 #250018588: opening Feb 28 2025 14:30 Pacific; official amendment #1 on Feb 20 adds an addendum and a **revised price schedule**; amendment #2 on Mar 4 adds a **notice of intent to award**. The manually transcribed event fixture stores these three attachment names and event timestamps, never reproduced raw procurement files.

## What was actually executed

**Python 3.13.5, standard library only:** `18/18 unittest PASS` on exact-file Git blobs:
- Source `7de18125a9e003260870de4bdc62f5fec09dbdaf`;
- Tests `c29a42d4a08e3de9ec17881649bad455f44cea01`;
- Manually transcribed public fixture `047abefe32ae244f82d77a6f8bcfe92bd5494c4b`.
- SHA-256 source `fec4cda3e6a682b0d6d875b5325592308b95f6fadb8cbf722dcab139f7662213`; tests `57a81db7b33c484f07d1f994c854cb460060c0b498bf1723554dce625f5d6c1b`; fixture `fc26721a0a7fd648cb2e83de14ed42ac6e7d12b71b89852c7d1db12502b8a9ff`.
- Run output SHA-256 `a333b230fa30f8e01ad7681df65526edf63b5fc5915956502c2e1ef74177d57e`. Generated `real_case_output.json` is committed.
- Historical ground truth: two amendments, **one pre-opening potentially material event, one post-opening award notice**. This is a *labeled data classification*, not a measurement of money saved. The candidate correctly reports **zero current bidding actions** against a 2025 historical record.

**Newly caught and repaired failure:** the first prototype described the February 2025 pre-opening change as a bid action today. The code was amended to fail closed: require a genuinely current snapshot before suggesting *review* and explicitly warn that bid-opening time is **not** a verified submission deadline. Negative test added; original code behavior preserved in commit ancestry. No legal deadline or opportunity is invented.

## Competitive falsification (do not overclaim)

- Official Oregon page **already displays both amendments and the revised attachment name**. Thus the classifier's result largely reorganizes publicly visible source facts.
- [ERateSignal](https://www.eratesignal.com/) advertises a free tier and planned $49/$399/$699 monthly tiers with Form 470 discovery, transparency and alerts. Prices are advertised/waitlist, **not independently evidenced sales**. [Dedicated Form 470 alert page](https://eratesignal.com/form-470-alerts) already covers source filtering/scoring.
- The simple **naive all-amendments watcher** (our own deliberately weak baseline, *not an incumbent*) would mark two events, one of them a post-opening award notice. The candidate classifies them correctly using source note/sequence. This validates a narrow algorithmic improvement **only over this toy baseline**. Neither the official USAC tool nor ERateSignal was executed for same-input comparisons. **No competitive superiority demonstrated.**

**Principal open gates:** authenticated fetching of actual source documents (rather than manual transcription), real same-document semantic change and quoted evidence (price/requirements), output check by an independent specialist, same-input output against installed USAC/ERateSignal, repeated buyer pain and actual willingness to try/pay, no-account zero-human delivery. The source-page classification alone is commodity and **NOT a product to select or launch**.

## Commercial disposition and next bounded experiment

**`REFINE_ONE_TIMESOURCE_DOC_COMPARISON`, no product selection.** Only invest again if a legally accessible paired official original + amendment document set can be retrieved with exact bytes and a source-labeled specific changed obligation, including a no-account comparison to source-native listing and any usable competitor. If this fails, `KILL_ERATE_GENERIC_AMENDMENT_WATCHER` and pivot to the next buyer-posted machine-deliverable narrow job; do not build generic dashboards, crawlers, paid SaaS, monitoring schedules or GPT summaries.

No client contact, prospecting, paid Work, spend, new accounts, credentials, OAuth, provider changes, commercial release, main merge, runtime activation or canonical registry modification. Static candidate/PR and a local test do NOT certify unattended owner execution or first revenue.
