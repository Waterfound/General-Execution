# WRM Algora current-opportunity screen — 2026-10-19

**Decision:** `PLATFORM_HAS_PUBLIC_REWARD_HISTORY / SAMPLED_CURRENT_TASKS_NOT_ADMISSIBLE / NO_CURRENT_WATERFOUND_OPPORTUNITY / NO_CLAIM / NO_REVENUE`

## Commercial predicate

Does Algora currently expose a funded, bounded, low-duplication software task that Waterfound can evaluate toward first revenue without speculative duplicate work, private credentials, paid services or premature payout onboarding?

## Evidence boundary

Public GitHub issue bodies, labels and complete public comment histories were inspected. No Algora account, claim, attempt comment, fork, branch, pull request, maintainer contact, demo video, payout setup, KYC or paid cloud call was created.

Primary sources:

- <https://github.com/BAWES-Universe/workadventure-universe/issues/1>
- <https://github.com/arakoodev/EdgeChains/issues/290>

## Sampled opportunities

| Candidate | Advertised reward | Current primary state | Competition / delivery evidence | Decision |
|---|---:|---|---|---|
| BAWES mobile-app epic | US$150 | Open but labelled `on-hold`; reward applies to a multi-slice epic | 16 public attempts, 4 claim mentions, at least 8 PR references; bot table already lists many solution/reward links; contributors repeatedly ask which slice or award remains | Reject current task |
| EdgeChains AWS Comprehend redaction | US$50 + US$25 | Open, but original assignment dialogue is stale and current unmet scope is not reconciled | 51 public attempts, 19 claim mentions, at least 13 PR references; bot table lists many historical solutions/reward links; recent contributors ask whether any payable gap remains | Reject current task |

Counts describe comments, not distinct valid implementations. They establish the narrower commercial fact needed here: both advertised awards are already surrounded by overlapping submissions, claims or slice ambiguity, so a new implementation would be speculative duplication.

## Platform evidence

Algora's bot exposes attempt, claim and reward links and states that awarded payouts are received after reward. This is materially stronger than an unstructured maintainer promise and preserves Algora as a potentially valid discovery channel.

However, the payment-eligibility link currently emitted by the bot — `https://algora.io/docs/payments#supported-countries-regions` — returned no live documentation page during this inspection. Therefore Brazilian payout eligibility remains unverified and cannot be assumed from historical rewards to other contributors.

Platform capability does not override job-level admission. A task must still be currently funded, clearly unclaimed or exclusively assigned, bounded by a stable acceptance contract, and payable to the intended Brazilian payee.

## Kill criteria reached for sampled tasks

- explicit `on-hold` state or stale unresolved commissioning state;
- multiple prior solution/reward records;
- overlapping current attempts, claims and PRs;
- no maintainer-confirmed remaining payable gap;
- payout-country evidence unavailable at the bot's published documentation link;
- expected duplicate-work burden disproportionate to US$75–150 gross.

## Re-entry criteria

Reconsider Algora only when a primary issue and bot record jointly show:

1. a newly funded amount attached to a distinct bounded task;
2. no accepted solution, competing claim or unresolved prior delivery;
3. a stable base revision and objective acceptance checks;
4. explicit maintainer confirmation that the task remains payable;
5. official Brazil-compatible payout eligibility and current identity/tax requirements;
6. expected net value remains material after implementation, demo, KYC, tax and collection burden.

## Mission posture

`ALGORA_CHANNEL_PASSIVE / CURRENT_SAMPLE_REJECTED / CONTINUE_READ_ONLY_DISCOVERY`

No task, product, account, external contact, publication, WTP or revenue was created. Observed Waterfound revenue remains **USD 0**.

## 2026-10-20 reconciliation addendum — board state is not payment authority

**Updated state:** `ALGORA_CHANNEL_PASSIVE / ISSUE_SIDE_PAYMENT_CONFIRMATION_REQUIRED / STALE_BOARD_HAZARD_CONFIRMED / NO_CLAIM / NO_REVENUE`

A current primary-source reconciliation confirmed a stronger failure mode than competition alone.

### Coolify issue #7528

- The GitHub issue remains open and Algora bot comments advertise a **US$200** bounty.
- The issue accumulated 47 comments, many attempts, and several submitted PRs.
- The maintainer locked the thread because of AI-bot spam.
- Most importantly, maintainer **Cinzya** stated that Coolify stopped its Algora bounty program, asked Algora to remove still-listed issues, and warned that payouts “won't work / happen” and bounty claims are no longer accepted.

Primary sources:

- <https://github.com/coollabsio/coolify/issues/7528>
- <https://github.com/coollabsio/coolify/issues/7528#issuecomment-5655068172>

Therefore an Algora-visible reward, open GitHub issue, and bot instructions are jointly insufficient evidence that paid entitlement still exists. Starting work on this item would be speculative unpaid contribution and is rejected.

### Additional stale-state evidence

Algora's Cal.com board currently reports two open rewards attached to the same old font issue, while the underlying GitHub issue was closed as completed in September 2025. This independently shows that board-open state can diverge from source-of-truth completion state.

Sources:

- <https://algora.io/cal/bounties?status=open>
- <https://github.com/calcom/sans/issues/2>

### Adjacent marketplace check

OpenBounty currently advertises funded tasks and amounts but explicitly states that it is in **mock-payments mode** and no real funds move during the MVP. It is not an admissible revenue channel regardless of apparent dollar labels.

Source: <https://openbounty.ai/>

### Hardened admission rule

A bounty is machine-admissible for technical feasibility work only after all of the following are proven concurrently:

1. the underlying issue is open and current;
2. the maintainer has not ended or repudiated the bounty program;
3. the platform moves real money rather than simulated balances;
4. the exact task has remaining award capacity and no accepted or overlapping solution;
5. current issue-side evidence confirms that the reward is still payable;
6. the payout route supports Brazil and its KYC/tax requirements are known;
7. Waterfound has authority for any required claim/contact step.

A marketplace label, bot comment, “funded” badge, balance display, or historical payout record cannot substitute for these predicates.

### Commercial consequence

- Reject Coolify #7528 as a revenue opportunity.
- Reject OpenBounty while mock payments remain in effect.
- Do not build, claim, comment, contact maintainers, create accounts, or onboard payout details.
- Keep Algora as `PASSIVE / WATCH_ONLY`; require issue-side payment confirmation before spending implementation effort.
- Preserve `NO_PRODUCT_SELECTED`, revenue **USD 0**, and no WTP or payout claim.
