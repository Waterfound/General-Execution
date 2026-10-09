# DP6 exact-trace bank/locality stress closure

**Program:** DP6-EXACT-TRACE-BANK-LOCALITY-001  
**Authority:** research/evidence only. No DP6, consensus, provider, physical-test, release or mainnet mutation.

## Why this run existed

The prior DP6 dependency-hardening investigation retained one narrow software question:

> Does the exact frozen DP6 address trace expose bank/interleave locality that a specialized memory controller could exploit enough to justify changing the algorithm?

This wave deliberately tried to make that concern survive.

## Real execution

The frozen DP6 HLS semantics at blob `ea1ab21fbf359adc35955c42ea8e137707c37b6d` were instrumented and compiled locally. The canonical nonce-1200 MH3 output, RW5 transcript and final DP6 vector all matched the frozen expected values before the trace evidence was admitted.

Two 16-trace corpora were executed:

1. the canonical template with nonces 1200..1215;
2. one canonical vector plus 15 deterministic variants changing header, task, previous hash, height and nonce.

That produced **33,554,432 exact mandatory RW5 addresses** across the two corpora, plus the real optional RW5 memory-op accesses.

GitHub Actions consumed: **0**.

## Stress result

The mandatory address stream behaves extremely close to a random bank-selection baseline across linear and XOR-fold mappings, bank counts 16..256, interleave granularities 32..256 bytes, temporal lags 1..1024 and cross-nonce comparisons.

A 408-function mapping family was searched on a training subset and the selected anomalies were then evaluated on disjoint holdout traces. Apparent training extremes mostly collapsed on holdout.

Optional RW5 opcodes do contain measurable low-level bank skew. This is a real source-level property and is intentionally not hidden. However, once mandatory and optional accesses are combined, representative B64 mappings show only about 1–1.4% hottest-bank deviation. Under fixed-64-bank adversarial mapping selection, the observed difference between train-selected worst and best mappings corresponds to only about **0.45%** hottest-bank-load headroom on the canonical holdout and **0.12%** on the diverse holdout.

Those percentages are **not** asserted as throughput or ASIC-economic gains. They are merely structural evidence that the suspected bank-mapping optimization surface is small inside the tested family.

Row-hit probabilities were approximately 6–7 × 10^-6 and 4 KiB same-page probabilities stayed near the random address-space baseline.

## Red Team conclusion

The concern survives only in a narrower form:

> A concrete real controller could have an undocumented mapping/timing behavior outside the modeled family.

That is an external hardware/controller evidence question, not a reason to mutate DP6 preemptively.

Terminal verdict:

`NO_MATERIAL_BANK_LOCALITY_EXPLOIT_FOUND_IN_MODELED_MAPPING_FAMILY__VENDOR_SPECIFIC_PHYSICAL_MAPPING_REMAINS_EXTERNAL`

## Engineering decision

**Preserve current DP6.**

Do not add address whitening, increase memory, or increase mandatory reads from this evidence.

The generic software-only bank/locality search is closed at the current information value. Reopen it only if a concrete controller mapping, calibrated specialized PPA model, or physical specialized implementation demonstrates a repeatable material locality advantage.

This strengthens, rather than replaces, the existing design maxim:

> **Do not maximize memory. Do not maximize reads. Maximize the cost specialized hardware must pay to hide latency that general-purpose hardware already pays, while keeping the gross work budget as small as the participation target permits.**

The open DP6 memory-economic ASIC bound remains separate; this wave closes only the residual generic bank/locality hypothesis.
