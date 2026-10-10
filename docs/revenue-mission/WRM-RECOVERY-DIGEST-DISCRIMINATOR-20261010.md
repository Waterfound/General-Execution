# WRM — Zero-migration PR recovery discriminator

Status: candidate experiment, not product or customer validation. Date: 2026-10-10.

## Named commercial predicate
Does a read-only diagnosis of a stalled agent-created PR provide materially clearer, verifiable next-action information than native repository views and adjacent tools, with negligible setup?

## Smallest admissible experiment
Use a synthetic public-style PR snapshot containing exact PR head SHA, required-check policy, head-matched check runs, approval policy, and evidence links. A deterministic classifier returns one of INSUFFICIENT_EVIDENCE, CONDITION_WAIT, RECOVERABLE_CANDIDATE, HUMAN_GATE, REVIEW_READY_CANDIDATE, or TERMINAL, with a single bounded next action. Never treat a review gate as merge authorization. A check on a stale head is not admissible. No GitHub write permission, new account, live customer data, hosted service, or external outreach is required.

## Adversarial cases
1. Failed required check on current head -> inspect failure, not blind retry.
2. Queued required check -> condition wait.
3. Check evidence on old SHA -> insufficient evidence.
4. Successful checks and explicit unsatisfied required approval -> human gate.
5. Missing authoritative approval policy -> insufficient evidence.
6. All current checks successful, policy satisfied and mergeable -> review-ready candidate, never auto-merge.
7. Missing required-check policy -> insufficient evidence.

## Competitive control
The baseline is native PR checks, review state, branch policy and mergeability. Each diagnosis must be decomposed into facts already displayed natively and a separately evaluated derived inference. A nicer summary is not automatically incremental value. Compare against GitHub native UI, GitLab AI Governance, Agentplane and any available no-migration competitor; label untested product claims UNKNOWN. Native GitHub already displays check failures and review requirements. The candidate wins only if its inference changes a safe next action beyond negligible native friction. Otherwise KILL or REFINE without feature expansion.

## Evidence status
Seven logical test scenarios specified; independent Node test execution and external substitute side-by-side comparison NOT YET VERIFIED. Buyer pain, WTP, onboarding time, savings, ROI and revenue UNKNOWN. No merge, release, credential change, outreach or spending authorized by this candidate.
