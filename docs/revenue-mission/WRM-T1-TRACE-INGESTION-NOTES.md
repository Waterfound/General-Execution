# WRM-T1 — Representative workflow trace ingestion (candidate)

Status: DESIGN_CANDIDATE_ONLY. No canonical integration, release, activation or pricing authority.

## Observational boundary

The merged WRM-T1 projector is read-only and accepts an explicit observation object. The next machine-admissible step is to map real workflow receipts into that object without inventing fields. A successful GitHub PR or CI run proves process completion, not a full business mission, not an eliminated approval and not operator-hours saved.

For each naturally occurring representative workflow, preserve:
- workflow ID and class; immutable links to originating intent, final disposition, and evidence;
- original intent timestamp, **only** if an actual intent receipt exists (PR creation is not necessarily intent);
- terminal timestamp and state, **only** if a terminal mission receipt exists (a green CI run is not necessarily mission completion);
- state transitions and process invocations counted from authoritative runtime receipts, not from prose summaries;
- human requests and genuinely required human gates separately; do not infer an avoided approval from the absence of a request;
- human active minutes only from observed activity intervals; no extrapolation from calendar duration or waiting time;
- retry, rework and recovery events only from identified receipts;
- provenance numerator and denominator only when an explicit expected-item manifest exists;
- autonomous resolution numerator and denominator only when an explicit opportunity set exists.

## Fail-closed collection contract

An event requires event_id, workflow_id, timestamp with timezone, kind, and durable evidence reference. Duplicate event IDs, contradictory ordering, missing evidence, and invalid timestamps are rejected. A partial trace may contain witnessed events, but absence of an event is **unknown**, not zero.

A category may be declared complete only when a separate coverage receipt establishes that the relevant observation interval was fully covered, including zero events. Completeness claims are subject to independent review and must not be silently upgraded to proven coverage. Preserve both raw receipts and derivation code/version.

For human-active intervals, reject overlap before summing; round observed whole minutes down conservatively. A HUMAN_GATE terminal is a real authority stop, not a failed autonomous resolution by default.

## Natural comparison and economic claim boundary

Match workflow scope, deliverable quality, starting conditions, tool capabilities, and outcome before considering comparative metrics. If no natural comparable exists, keep coordination tax removed, hours saved, latency reduction, rework avoided, risk reduction, ROI and price ceiling **null**. No artificial manual baseline, fictional customer or synthetic monetary benefit.

Prior verified unattended pilot: 5 transitions, 8 invocations, no chat-context dependency and genuine stop at human_gate. This is capability evidence only. The merged projector's synthetic unit tests are not customer outcomes.

## Acceptance sequence

1. Inventory a real representative workflow with intent and terminal receipts.
2. Identify runtime source-of-truth for each metric; mark unavailable fields null.
3. Implement a **read-only** event adapter as an isolated candidate; no authority changes or automatic execution.
4. Verify duplicate/ordering/coverage/denominator/human-gate rejection tests offline.
5. Compare adapter output to independently reviewed raw receipts.
6. Admit observation into Value Proof only after evidence review; economic deltas remain gated.
7. Seek real independent buyer evidence only when lawful contact/publication authority is established.

## Operational constraints

No new spend, credential expansion, provider changes, public customer claims, outreach, payment/KYC, pricing, production repin or canonical merge. Protect private runtime topology, secrets and tenant data. Avoid requiring routine Waterfound labor; use machine-readable receipts and existing authorized read-only surfaces.
