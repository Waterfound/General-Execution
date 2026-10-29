# WRM — Machine-embroidery file preflight screen (2026-10-25)

## Decision

**KILL before prototype.** A browser-local DST/PES/JEF preflight that flags density hotspots, micro/overlong stitches, jumps, trims, colour changes and hoop fit is already directly supplied by multiple free tools. Building the same feature set would not answer a missing commercial predicate.

## Narrow job tested

> Before stitching a garment, inspect a machine-embroidery file locally and identify deterministic file-level risk signals so the operator can decide whether to test, repair, or reject it.

Intended buyer: small embroidery shops and prosumer operators who receive third-party digitized files.

## Evidence classification

### Buyer/problem evidence

The underlying problem is real but multi-causal:

- Bad files can contribute to puckering, thread breaks, excessive trims, machine stops and ruined blanks.
- Physical outcome also depends on fabric, stabilizer, thread, needle, tension, hooping, machine setup and operator choices.
- Therefore a file-only tool may report structural signals, but cannot honestly certify stitch-out quality.

Examples:
- Madeira, *How to Prevent Puckering*: https://www.madeira.co.uk/wp-content/uploads/2019/10/How-To-Prevent-Puckering-2019.pdf
- Melco E16 Pro manual (test on representative fabric/backing): https://docs.melcocloud.com/resources/Storage/e16pro_user_manual.pdf
- Recent operator report in which apparent digitizing/material faults were mechanical: https://www.reddit.com/r/Machine_Embroidery/comments/1trb1pa/

### Direct substitution

Exact or near-exact browser tools already exist:

1. PlixaLabs free file analyzer — DST/PES/EXP/JEF/VP3; score, stitch-length risks, jumps, trims, colour changes, density and hoop fit:
   https://www.plixalabs.com/tools/dst-file-analyzer
2. Stitch Toolbox free pre-flight — density, thread-break-length signals, jumps and hoop fit:
   https://stitchtoolbox.com/tools/embroidery-preflight-check
3. Tiny Online Tools stitch analyzer — counts, length histogram and density:
   https://tiny-online.tools/embroidery-cnc-tools/embroidery-stitch-analyzer
4. The Standard Digitizing free local-browser DST checker — preview, stitch count, size, trims, jumps, colour stops, density risk and warnings:
   https://www.thestandarddigitizing.com/p/free-dst-file-checker.html
5. StitchSentry — automated QA for DST/PES/JEF/EXP/VP3 with density, jumps, trims, tiny stitches, underlay and colour-stop warnings:
   https://www.nxgntools.com/tools/stitchsentry
6. EmbroidAI advertises an instant 10-point score with the same signal family:
   https://www.embroidai.com/
7. ValidStitch markets embroidery validation and production workflow software:
   https://validstitch.com/

A public validation post for StitchSentry describes essentially the same proposed job and output:
https://www.reddit.com/r/Machine_Embroidery/comments/1rmf1jd/

### Capability and observed outcomes

- Waterfound capability: not tested for this wedge because substitution failed first.
- Customer outcome: not measured.
- Demand/WTP: not established.
- Revenue: USD 0.

## Differentiation test

The candidate has no defensible narrow differentiation on:

- accepted formats;
- local/browser processing;
- density hotspot detection;
- micro/long stitch detection;
- jump/trim analysis;
- colour-block reporting;
- hoop-fit checks;
- risk scoring.

Fabric-aware prescriptions do not rescue the wedge: they increase liability and require fabric, stabilizer, thread, needle, tension and machine context plus representative sew-outs. A file-only conclusion would overstate certainty.

## Kill criteria applied

Killed because:

1. at least two free direct substitutes cover the core job;
2. a named product already uses the same “pre-flight” positioning;
3. no verified buyer evidence shows a missing high-value output those substitutes omit;
4. no willingness-to-pay evidence exists;
5. a trustworthy proof would need to remain deliberately narrower than claims already made by substitutes.

## Re-entry condition

Reconsider only if independent buyer evidence identifies a materially different unresolved job, for example a production-system integration or batch exception workflow with measured operator time/cost that existing tools cannot handle. Do not re-enter for another generic score, viewer, converter, dashboard, or threshold set.

## Mission consequence

- No prototype admitted.
- No public publication, outreach, account installation, spend, KYC, payment, contract or recurring entitlement used.
- Candidate status: **CLOSED / SUPPORTING MARKET EVIDENCE ONLY**.
- The commercial frontier remains buyer/problem discovery outside generic one-file transformations and static audits.
