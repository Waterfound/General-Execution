# DP6 Dependency Hardening Investigation — 2026-10-09

This evidence packet records a real **General Execution** bounded read-only run performed because GitHub Actions runner allocation was unavailable/exhausted. GitHub Actions consumed: **0**.

## Question

Can current DP6 be materially improved, at the same gross work budget, in:

- dependency quality;
- bank/locality resistance;
- address unpredictability;
- precomputation resistance?

The run also asks whether any discovered feature is strong enough to justify changing DP6 and paying the downstream ASIC/PPA plus representative-device revalidation cost.

## Source binding

Frozen DP6 HLS semantics are bound to:

- repository: `Waterfound/FAE-testnet`;
- ref: `evidence/fae-dp6-rp-b3-t2-20260930`;
- path: `labs/asic-f2-pre-go/hls/fae_dp6_hls.cpp`;
- blob: `ea1ab21fbf359adc35955c42ea8e137707c37b6d`.

General Execution semantics are bound to `Waterfound/General-Execution@143af0aae8a2131a8590437cad9ee282bede8f29`.

## Result

Terminal verdict:

`PRESERVE_CURRENT_DP6__NO_MATERIAL_SAME_BUDGET_CHANGE_FOUND__COUPLED_LATENCY_HIDING_SUPPRESSION_IS_KEY_DESIGN_INVARIANT`

The strongest architectural property is **coupled latency-hiding suppression**:

1. the mandatory RW5 memory-carried recurrence suppresses within-context memory-level parallelism;
2. the 256 MiB nonce-private state raises the residency cost of the natural specialized escape route: many independent contexts used to hide memory latency.

Neither component should be treated as sufficient alone.

The audit found no obvious missing serial-edge coverage, no obvious cross-nonce precomputation shortcut, and no demonstrated ideal-state bank imbalance. A final bank-address mixer has local diffusion headroom in the surrogate, but no exact-trace/controller exploit or specialized economic gain was established. Therefore no implementation candidate is admitted.

The only remaining bounded research question is whether an **exact frozen DP6 address trace mapped onto a concrete specialized memory-controller bank function** exposes exploitable locality. That stays inside the existing DP6 Robust Premise / specialized-memory-economic owner.

## Decision rule

Do not start a future DP6 optimization by increasing memory or reads. Seek more specialized-hardware hostility **per existing byte/read**. A consequential algorithm change is admissible only after a concrete exploit reduction survives Robust Premise and specialized PPA/economic analysis; only then does fresh physical-device evidence become justified.

No DP6/consensus change, physical run, provider/credential mutation, paid spend, release or mainnet authority is created by this packet.
