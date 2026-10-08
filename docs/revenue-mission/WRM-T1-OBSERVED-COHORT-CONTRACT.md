# WRM-T1 — Observed cohort projection candidate

Status: design-only; no ROI claim.

The canonical value-proof projector now validates individual observations. Next candidate frontier is a read-only cohort projection over naturally occurring representative workflows, grouped by workflow class, with unique workflow identifiers and explicit missing-data counts.

Safety invariants:
- Preserve null for missing measurements; never silently treat unknown as zero.
- Keep observed human active minutes distinct from operator-hours saved.
- Require real comparable workflows with matched scope and outcomes before estimating improvement.
- Preserve evidence references and distinguish references supplied from independently verified provenance.
- Never infer monetary value, willingness-to-pay, or price from execution counters.
- No credentials, account changes, provider mutations, payments, releases, or new authority.
- Do not treat a pull request's created/merged timestamps as mission intent/terminal timestamps without evidence.

This candidate is documentation only until executable validation and canonical integration are independently verified.
