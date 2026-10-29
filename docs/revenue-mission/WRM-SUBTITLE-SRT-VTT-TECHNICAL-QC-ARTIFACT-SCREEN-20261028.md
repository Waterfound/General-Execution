# WRM — Subtitle SRT/VTT Technical-QC Artifact Screen — 2026-10-28

Status: **REPEATED_BUYER_SIGNAL / TECHNICAL_LAYER_DIRECTLY_SUBSTITUTED / HUMAN_AUDIO_LANGUAGE_ACCEPTANCE / NO_BUILD**

Observed Waterfound revenue: **USD 0**

## Narrow job tested

Given an existing SRT or WebVTT file and a declared delivery profile, produce a read-only, source-pinned report covering:

- parse and encoding validity;
- cue order, duplicate or empty cues and malformed timestamps;
- overlaps and insufficient gaps;
- minimum/maximum display duration;
- characters per second, words per minute, line length and line count;
- differences against a named platform/profile;
- a cue-level CSV/HTML report;
- only deterministic candidate repairs, preserving every unresolved language, audio, scene-cut and translation judgment.

The commercial question was whether buyers pay for this bounded machine artifact independently of transcription, translation, audio alignment, linguistic review or final delivery responsibility.

## Current buyer/problem evidence

Buyer demand for subtitle work is current and repeated, but the paid acceptance is broader than the machine artifact:

1. **US$10–25/hour, 30+ hours/week, 6+ months — English SRT/VTT creation.** The buyer requests seven to eight hours of audio, accurate transcription, synchronization, segmentation and formatting, with samples and ongoing availability.
   https://www.upwork.com/freelance-jobs/apply/English-SRT-VTT-Subtitle-Creator-Needed-Hours-Audio_~022100525411798995079/

2. **US$15–30/hour — French localization.** The buyer requests natural French voiceover, synchronized SRT files and QA of talking-head lip sync across approximately 25 hours of work.
   https://www.upwork.com/freelance-jobs/apply/French-Voiceover-and-Subtitle-Localization_~022115147208873344709/

3. **US$100 fixed — Neutral Spanish SRT QC.** The job explicitly buys linguistic and cultural fluency, correction of awkward phrasing, correspondence to spoken dialogue, timing and readability.
   https://www.upwork.com/freelance-jobs/apply/Neutral-Spanish-Subtitling-Specialist-for-SRT-Quality-Control-Review-Film-Video-Content_~022102382284665648415/

4. **US$250–750 — English audio to SRT/VTT.** The buyer requests verbatim transcription, natural timing, overlaps, pauses, laughs, music cues and speaker identification.
   https://www.br.freelancer.com/projects/audio-editing/english-audio-subtitle-transcription

5. **US$30–250 — caption proofreading.** The buyer requests grammar and spelling correction of existing SRT files while preserving timestamps.
   https://www.br.freelancer.com/projects/video-editing/srt-caption-proofreading-test

6. **Current multilingual alignment/QA recruitment, posted 2026-10-27.** The work requires listening to source audio, understanding Chinese subtitles, identifying mismatched or missing content, language assessment and a freelance agreement before platform access; compensation is restricted.
   https://connect.proz.com/translation-jobs/2275921

These sources establish paid work around captions. They do not establish willingness to buy Waterfound's bounded technical report, completed payment to Waterfound, or an autonomous product price.

## Direct substitution of the machine-only scope

The named technical predicate is already answered by free and low-cost tools:

- **Subtitle Edit** lists every line that breaks configured reading-speed, duration, line-length, overlap and gap rules, and exports the result to text, Excel or a web page.
  https://subtitleedit.github.io/subtitleedit/features/list-errors.html
- Subtitle Edit includes rule profiles, automatic common-error repair, Netflix checks with proposed fixes and CSV reports, batch conversion, synchronization tools and a headless command line.
  https://subtitleedit.github.io/subtitleedit/
  https://subtitleedit.github.io/subtitleedit/features/settings.html
  https://github.com/SubtitleEdit/subtitleedit/blob/main/docs/reference/command-line.md
- **Subtidy** performs local browser-only SRT/VTT/ASS QC and automatic repair. Its free tier includes all automatic fixes, presets, preview, full report and SRT export; batch/custom limits and additional formats cost **US$39/year**.
  https://subtidy.io/
- **FormatPhantom** provides a local SRT/WebVTT delivery checker for CPS, line length, cue duration, frame gaps and overlaps.
  https://formatphantom.com/caption-tools/caption-qc
- **CueForge** offers local no-account conversion, QC, repair, shift and retime for free; printable/CSV reports, audio resync and batch workflows cost **US$99/year or US$12/month**.
  https://cue-forge.com/
- An API-style checker on Apify advertises the same validation and safe-correction artifact from **US$40 per 1,000 files**.
  https://apify.com/lumaxys/subtitle-qc

A Waterfound parser/report would reproduce existing checks, exports and repairs. It would not establish superior commercial value.

## Acceptance boundary

The paid jobs require one or more non-technical predicates:

- understanding the source audio and identifying exact speech boundaries;
- accurate transcription and speaker attribution;
- translation fidelity, idiom, dialect and cultural nuance;
- grammar, spelling and natural phrasing;
- deciding whether a line break or condensation preserves meaning;
- scene-cut, lip-sync and visual-context review;
- SDH sound cues and plot relevance;
- final playback and delivery responsibility.

Even Netflix's style guidance treats reading-speed correction as editorial work involving deletion, reformulation, re-timing, re-segmentation, merging or omission, rather than a purely mechanical threshold fix:
https://partnerhelp.netflixstudios.com/hc/en-us/articles/219375728-Timed-Text-Style-Guide-Subtitle-Templates

The current jobs explicitly request language proficiency, listening, visual QC, samples or a platform agreement. A file-only technical report does not satisfy their acceptance predicate.

## Decision

Do **not** build a generic SRT/VTT validator, caption-QC dashboard, rules-profile engine, error export, batch repairer or browser-local subtitle checker.

The machine-only layer is directly substituted at free, US$39/year, US$99/year and commodity API pricing. The paid residual is human audio/language/editorial work and private delivery access, which conflicts with the selected autonomous low-touch artifact.

Keep subtitle work as **SUPPORT_ONLY / service-demand evidence**. Do not infer that technical error counts equal customer value, compliance, acceptance or avoided labor.

## Kill criteria reached

1. A free tool checks and exports the exact proposed rule violations: **reached**.
2. Free tools already propose or apply deterministic repairs: **reached**.
3. Browser-local no-upload alternatives exist: **reached**.
4. Paid batch/custom/report alternatives cost materially below a service engagement: **reached**.
5. Current buyers accept a technical-only report without listening or linguistic review: **not observed**.
6. Waterfound differentiation, willingness-to-try, WTP or revenue exists: **not observed**.

## Re-entry criteria

All must hold:

1. two current buyers request the same bounded technical artifact independent of transcription, translation and audiovisual review;
2. acceptance is expressed as reproducible file/profile checks with an example fixture;
3. the artifact produces a decision-relevant result absent from Subtitle Edit, Subtidy, CueForge and adjacent tools;
4. a public or consented fixture demonstrates that advantage;
5. repair remains conservative and every semantic/audio uncertainty is explicit;
6. external contact, proposal, private file receipt, platform agreement, publication, contract and payment remain separately authorized.

## Evidence accounting

| Predicate | State |
| --- | --- |
| Buyer/problem evidence | Strong for full subtitle service |
| Technical-only buyer demand | Not observed |
| Machine capability needed | No; exact checks and exports already exist |
| Competitive differentiation | Falsified |
| Complete paid acceptance automatable | Falsified |
| Demand evidence for Waterfound | None |
| Waterfound WTT / WTP / revenue | None / none / USD 0 |
| Mission posture | Wedge closed; commercial discovery remains ACTIVE |

No media, subtitle file or private platform was accessed. No linguistic or accessibility assurance was represented as final. No outreach, proposal, account, agreement, publication, contract, payment/KYC, spend, runtime activation or Privacy P0 action occurred.
