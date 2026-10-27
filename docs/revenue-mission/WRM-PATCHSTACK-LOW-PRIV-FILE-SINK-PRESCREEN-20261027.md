# WRM — Low-privilege file-sink pre-screen

Date: 2026-10-27  
Mission: Waterfound Revenue Mission  
Channel: Patchstack non-crypto security bounties  
Decision: `PUBLIC_LOW_PRIV_FILE_SINK_QUERY_NEGATIVE / NO_TARGET_ADMITTED / PATCHSTACK_SECONDARY`

## Commercial predicate

Can public code search identify a current, eligible WordPress plugin where an unauthenticated or Subscriber-level entry point reaches a material file-system or remote-fetch sink, strongly enough to justify a full source-pinned target review?

This pre-screen applies the selection lesson from the first three Patchstack targets. It exists to avoid spending a full target slot on admin-only import/export, generic form submission, stale code, or mere textual co-occurrence.

## Admission rule

A candidate advances only if all of the following are visible before full review:

1. an official or attributable public source can be pinned;
2. the plugin is current and plausibly meets the program's installation and maintenance rules;
3. a public/Subscriber handler, low-privilege nonce path, or weak permission callback is identifiable;
4. that entry point has a plausible route to file read/write/delete, archive extraction, remote fetch, or another material mutation;
5. the hypothesis is not already explained by an admin-only workflow or an obviously ineligible/stale project.

## Queries screened

The search used route/sink conjunctions, including these families:

- `wp_ajax_nopriv` with `ZipArchive::extractTo`;
- `wp_ajax_nopriv` with `wp_remote_get` and `file_put_contents`;
- `register_rest_route` / `permission_callback` with `file_put_contents`;
- `admin_post_nopriv` with `unzip_file`.

## Observed result

No candidate survived the admission rule.

The returned sources were dominated by one or more of:

- discontinued or stale plugins;
- custom, private-purpose, or non-directory repositories without a qualifying public program target;
- security methodology and exploit-reference material rather than eligible product code;
- old mirrors or unattributable copies;
- files where route and sink terms merely co-occurred without a verified control-flow relationship.

No current official plugin with the required installation threshold and a verified public/Subscriber route into a material sink was established. This is a selector result, not a claim that the ecosystem has no vulnerabilities.

## Evidence classification

| Layer | Result |
|---|---|
| Capability | Public source search and source-level pre-screening are available without paid spend, credentials, or live-site interaction. |
| Observed outcome | Four low-privilege route/sink query families produced no admissible target. |
| Competitive/commercial implication | A bounty channel exists, but broad co-occurrence scanning now has low marginal information gain. |
| Demand evidence | Patchstack payouts establish an external reward mechanism generally; no reportable finding or buyer-specific demand was produced here. |
| WTP / revenue | No earned reward, payout claim, or Waterfound revenue. Observed revenue remains US$0. |

## Portfolio disposition

Patchstack moves from **ACTIVE** to **SECONDARY / WATCH_FOR_QUALIFIED_TARGET**.

Reason: three full target hypotheses were falsified, and the stricter low-privilege file-sink selector produced no admissible fourth target. Continuing broad scans would optimize activity rather than expected commercial information gain.

Patchstack may return to ACTIVE only when a candidate already satisfies the admission rule above, including a pinned current source and a credible route-to-sink relation. Admin-only import/export, generic form spam, and raw keyword co-occurrence are insufficient.

The next ACTIVE allocation returns to buyer/problem evidence or traditional-currency opportunities that are eligible in Brazil and compatible with One Machine / Full Autonomy. Existing dated opportunities remain condition waits: Kiroween cannot start before its opening on 2026-10-30, and #BuildHybridAI awaits complete rules expected on 2026-11-09. No early build is admitted.

## Kill criteria and unknowns

Kill further Patchstack scanning in a wake when:

- the candidate fails eligibility or current-maintenance screening;
- the relevant handler is administrator-only;
- no route-to-sink relation can be established from pinned source;
- the likely impact falls outside the program's accepted classes;
- dynamic testing would be the first step rather than confirmation of a source-backed hypothesis.

Unknowns preserved:

- a qualified target may exist outside the indexed results;
- a current plugin may expose a material route through indirect callbacks not captured by these query families;
- a future update may create a newly admissible surface.

These unknowns justify SECONDARY watch status, not continued ACTIVE allocation.

## Authority and safety record

No live target was tested. No account, report, outreach, disclosure, payment, KYC, publication, credential, new permission, paid spend, recurrence, runtime activation, private ingress, dispatcher, SQLite write, or Privacy P0 activation occurred. No human gate is currently required.
