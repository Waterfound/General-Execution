# WRM — Patchstack non-crypto OSS bounty channel and first target falsification — 2026-10-27

Status: **CHANNEL_ADMISSIBLE / BRAZIL_NO_EXCLUSION_OBSERVED / FIRST_TARGET_HYPOTHESIS_FALSIFIED / NO_REPORT / NO_REVENUE**

Observed Waterfound revenue: **USD 0**

## Decision

Patchstack is admitted as an **ACTIVE discovery channel** for lawful, local-only security research on current public WordPress components. It is a materially better fit than the rejected crypto route because the controlling 2026 rules:

- open participation to anyone who submits a valid, unique, in-scope vulnerability;
- accept current public WordPress core, plugins and themes with at least 1,000 active installations;
- require unauthenticated or default Subscriber/Customer exploitability for the public program;
- pay by PayPal from USD 50, or bank transfer from USD 500;
- create a researcher account only after the first valid report passes validation.

No country exclusion for Brazil was found in the controlling rules. This is **absence-of-exclusion evidence**, not an explicit representation by Patchstack that every Brazil-specific tax or payment condition is satisfied.

A first narrow candidate was screened and closed without submission:

> Can an unauthenticated or default Subscriber user read or delete sensitive request/response logs through REST API Log 1.7.3's custom REST endpoints?

Static inspection of the current public source falsified that hypothesis. Read routes call a dedicated permission callback bound to the custom post type's `read_post` capability; delete routes call a dedicated custom delete capability; the plugin grants those custom capabilities through its administrator-only capability path. The 2026 release also disabled the core REST exposure of single log entries and added an additional check to download routes. No in-scope unauthenticated or Subscriber path was established.

The result is a target-specific negative proof, not a security certification of the plugin.

## Why this channel passes the commercial-information-gain test

Patchstack presents an objective, externally adjudicated cash outcome with no paid spend, no crypto wallet and no pre-emptive account setup. A valid report can produce:

- a cash bounty from a guaranteed minimum USD 10,000 monthly pool, or a separate high-impact Zeroday bounty;
- independent validation that the finding is valid, unique, reproducible and impactful;
- public CVE attribution after coordinated remediation.

The channel does **not** establish buyer demand or WTP for a reusable Waterfound product. It is a prize/research-income channel. Revenue is recognized only after a validated award and payout, never from a suspected vulnerability or nominal bounty table.

## Controlling source evidence

### Program admission and scope

The current rules state:

- participation is open to anyone who submits valid and unique vulnerabilities under the rules;
- all reports must use the official form;
- the researcher account is automatically created only after a valid in-scope report passes validation;
- components must have at least 1,000 active installs, be on the latest public stable version, and have been updated within three years;
- ordinary public-program findings must be exploitable by unauthenticated users or default Subscriber/Customer roles;
- reports must include reproducible steps, raw HTTP requests and exact payloads;
- false positives and rejected reports reduce monthly payout and can lead to cooldown or removal.

Source:
- https://patchstack.com/articles/bug-bounty-guidelines-rules/

### Traditional payout

The controlling rules effective from 2026-10-01 specify:

- PayPal: USD 50 minimum;
- bank transfer: USD 500 minimum;
- an invoice is mandatory for every payment;
- the invoice must contain full name, country and address;
- processing occurs 30 days after final results are announced and the invoice is submitted.

The public marketing page still mentions cryptocurrency alongside PayPal, but the newer controlling rules list PayPal and bank transfer. Waterfound's non-crypto constraint is satisfied only by those traditional methods.

Sources:
- https://patchstack.com/articles/bug-bounty-guidelines-rules/
- https://patchstack.com/bug-bounty/

### Reward boundary

The rules guarantee a minimum monthly pool of USD 10,000 distributed by contribution percentage and adjusted for rejection rate. Zeroday rewards range by active installations and required privilege, but require full site compromise, a working exploit, latest stable/default settings, no prerequisites and no prior disclosure. A displayed maximum is not expected revenue.

## First target: REST API Log 1.7.3

Public eligibility evidence:

- WordPress.org lists version 1.7.3, updated in September 2026, with 5,000+ active installations.
- The public source repository identifies 1.7.3 as the stable tag.
- The plugin stores full REST request and response records, making unauthorized read/delete access a narrow, high-impact predicate worth falsifying.

Sources:
- https://wordpress.org/plugins/wp-rest-api-log/
- https://github.com/petenelson/wp-rest-api-log
- source snapshot inspected: commit `53f394340c0c20b9fb2ad63ad5d177cad51029b7`

Files inspected:

- `includes/class-wp-rest-api-log-controller.php`
- `includes/class-wp-rest-api-log-post-type.php`
- `admin/class-wp-rest-api-log-admin.php`

Observed controls:

1. `/entries`, `/entry/{id}` and `/routes` use `get_permissions_check`.
2. That check resolves the log post type's dedicated `read_post` capability and calls `current_user_can`.
3. Delete endpoints use `delete_items_permissions_check` with a dedicated delete capability.
4. Download endpoints require both the read capability and a time-bound hash generated by the plugin.
5. The custom post type is non-public, non-queryable and `show_in_rest=false`.
6. The changelog records additional 2026 hardening for the download endpoint and core REST exposure.

**Disposition:** `HYPOTHESIS_FALSIFIED / TARGET_CLOSED_FOR_THIS_PREDICATE / NO_REPORT`.

No dynamic exploit attempt was warranted after the required low-privilege path failed at the permission model. This avoided a false-positive submission and its explicit rejection penalty.

## Narrow next job

Select exactly one different, current, public WordPress component with at least 1,000 active installations and test one in-scope predicate using only local/public source and a synthetic WordPress fixture:

> Can an unauthenticated or default Subscriber/Customer input reach an accepted high-impact sink without a valid capability/nonce boundary in the component's latest stable version?

Priority sinks are SQL injection, arbitrary file operations, unsafe deserialization, privilege escalation to Contributor or higher, significant broken access control, or reflected/site-wide XSS. Generic linting, broad scanner construction and live-site probing remain SUPPORT_ONLY or prohibited.

## Kill criteria

Close a target immediately when any one holds:

- fewer than 1,000 active installs, latest stable not public, or last release older than three years;
- exploit requires Contributor, Author, Editor, administrator, custom elevated roles, high attack complexity, non-guessable identifiers, or additional user action outside the allowed rules;
- impact is limited to minor disclosure/modification, expected functionality, rate limiting, open redirect, low-impact DoS, HTML/CSS-only injection or other published exclusions;
- source inspection proves a correct capability, nonce, type, path or ownership boundary for the exact hypothesis;
- the finding is already public, already reported or duplicated;
- dynamic reproduction would require a live third-party system rather than a local synthetic fixture;
- no complete, accurate, reproducible proof can be produced.

Close the overall channel if three consecutive carefully selected targets yield no locally reproducible in-scope predicate and a fresh substitute-channel comparison has higher expected commercial information gain.

## Evidence accounting

- Channel eligibility: **observed from current public rules**.
- Brazil eligibility: **no exclusion observed; not explicitly confirmed for local tax/payment law**.
- First target outcome: **one narrow hypothesis falsified by current-source permission analysis**.
- Dynamic exploit: **not attempted; unnecessary for the closed hypothesis**.
- Valid vulnerability: **none**.
- Report submitted: **none**.
- Account created: **none**.
- Bounty awarded: **none**.
- Revenue: **USD 0**.
- Buyer demand, product WTP, operator-hours saved, latency reduction, avoided rework and monetary risk reduction: **not measured and not claimed**.

## Authority, ethics and privacy record

Research was limited to public documentation and public source. No live system was probed, no third-party data was accessed, no exploit was executed, no vulnerability detail was disclosed, and no report/account/contact/publication occurred. Any locally reproduced finding must remain private until Waterfound separately authorizes the official Patchstack submission and its disclosure terms.

No spend, crypto wallet, payment instrument, invoice, KYC, contract, payout onboarding, public post, vendor contact, external installation, recurrence, dispatcher/state write, global writer lease, or Privacy P0 activation occurred. The Privacy P0 text remains an inactive candidate only.
