# WRM — Public Software Bounty Channel Screen — 2026-10-28

Status: **CASH_REWARDS_EXIST / INDEX_STALENESS_CONFIRMED / HIGH_VALUE_ITEMS_ALREADY_CLAIMED / LOW_EXPECTED_VALUE / NO_BUILD / CHANNEL_SECONDARY**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound reach first revenue through a public software bounty with an explicit cash reward and reproducible acceptance criteria, while preparing the solution privately and keeping account creation, public submission, contract/payment/KYC and irreversible commitments behind their existing gates?

This screen intentionally shifts from another generic website idea to a direct-revenue channel. It checks canonical issue state before admitting engineering.

## Initial opportunity signal

Algora index pages displayed several apparently open bounties:

- Cal.com issues at **USD 500**;
- Coolify generic OIDC support at **USD 20**;
- Terrastruct D2 `shape: cycle` at **USD 50**;
- pgstrap/PGlite generation at **USD 30**;
- old Drizzle ORM custom-type issues at **USD 30–50**.

Sources:

- https://algora.io/cal/bounties/community?fund=calcom%2Fcal.com%2318992
- https://algora.io/coollabsio/bounties?status=open
- https://algora.io/terrastruct/bounties
- https://algora.io/tscircuit/bounties
- https://algora.io/Seated/bounties?status=open

The listing itself is not sufficient evidence that a bounty is available.

## Canonical reconciliation

### Cal.com USD 500 items

The apparent high-value items were stale or already contested:

- Outlook cache issue #21050 already has multiple implementations and pending claims from 2025, including PRs #21071 and #22312.
  - https://algora.io/claims/xwXdFgrP2XfA3utE
  - https://algora.io/claims/ueuGq7apvbkonab4
- MS Teams + Outlook issue #14765 is closed; one implementation received the USD 500 award.
  - https://github.com/calcom/cal.diy/issues/14765
  - https://algora.io/claims/ehuXjnJ2Qimziiid
- Fastmail/CalDAV duplicate invitations issue #9485 is closed and has multiple historical implementations/claims.
  - https://github.com/calcom/cal.diy/issues/9485
  - https://algora.io/claims/P3Mk6UsnjR6Q6WXV
- Algora's completed-bounty view lists a USD 500 CalDAV fix.
  - https://algora.io/org/cal/bounties/community?fund=calcom%2Fcal.com%2318459

Result: the apparent open USD 500 pool was not a current unclaimed opportunity.

### Smaller items

- Coolify #6696 is listed at USD 20, but current Coolify documentation already describes generic OIDC configuration, indicating the feature has landed or the indexed issue is obsolete.
  - https://coolify.io/docs/core/security/authentication/sso/oidc
- Terrastruct D2 #1578 is still indexed at USD 50 after approximately 19 months. The age and unclear current acceptance state make it unsuitable without maintainer confirmation.
  - https://algora.io/terrastruct/bounties
- pgstrap #2 remains open and indexed at USD 30, but its issue history shows many attempts and PRs, including multiple submissions in October 2026. The displayed issue page reports more than 60 remaining timeline items.
  - https://github.com/seveibar/pgstrap/issues/2
- Drizzle ORM #1083 is more than three years old, already has a claim, and the current documentation describes evolved custom-type codec behavior. A USD 30 reward does not justify speculative reconciliation of an old feature request.
  - https://github.com/drizzle-team/drizzle-orm/issues/1083
  - https://orm.drizzle.team/docs/custom-types

## Commercial decision

**DO NOT BUILD OR CLAIM.**

The public bounty channel is real, but this inspected set has poor expected value:

1. high-value listings were already closed, rewarded or heavily claimed;
2. low-value listings were old, ambiguous or contested;
3. index pages lag canonical GitHub and claim state;
4. successful participation requires an external public PR and Algora account;
5. payout may require payment onboarding or wallet details;
6. no inspected issue had a current, exclusive, reproducible acceptance path worth the engineering time.

No candidate solution was implemented because availability failed before capability was the missing predicate.

## Bounty admission rule

Admit a bounty to **ACTIVE** engineering only when all are independently verified on the same inspection date:

1. canonical issue is open;
2. bounty sponsor and amount are still active;
3. no merged fix, approved claim or equivalent feature exists;
4. no active assignee or materially complete competing PR exists;
5. issue was maintained or confirmed within the last 60 days;
6. acceptance criteria can be reproduced without customer credentials, paid infrastructure or unavailable hardware;
7. reward is at least USD 250, or the bounded fix is demonstrably under two machine-hours;
8. expected payout route is lawful and compatible with existing financial gates;
9. private candidate work can be completed before any public claim or submission;
10. submission, account, publication, contract and payment/KYC remain explicit gates.

Failing any item keeps the opportunity SECONDARY or rejects it.

## Evidence ledger

| Predicate | State |
| --- | --- |
| Cash rewards exist | Observed |
| High-value current unclaimed opportunity | Falsified in inspected set |
| Canonical index accuracy | Falsified; index lag observed |
| Reproducible acceptance | Mixed / unresolved |
| Competitive claim load | High on remaining technical items |
| Machine-only private proof justified | No |
| Waterfound account/payment readiness | Not invoked |
| Revenue | USD 0 |

## Active–Secondary–Passive decision

- **ACTIVE:** buyer/problem discovery for a differentiated self-serve product or a newly verified direct-revenue opportunity.
- **SECONDARY:** public bounties, subject to the admission rule above.
- **PASSIVE:** stale Algora indices, already-claimed issues, low-value speculative fixes and bounty scraping infrastructure.

## Next machine-admissible frontier

Continue discovery without building another generic checker. Prefer either:

- a newly posted bounty meeting the full admission rule; or
- a repeated buyer artifact whose exact machine-generated output is paid, not merely the surrounding human correction.

Do not create a bounty-monitoring runtime or telemetry system; fresh read-only checks are cheaper and sufficient.

No external repository was modified. No claim, comment, PR, account, outreach, proposal, publication, checkout, card/crypto integration, payment/KYC, wallet, spend, contract, runtime activation, private producer activation, writer lease, dispatcher, SQLite write or DISPATCH_FENCE action occurred.
