# WRM Patchstack Target 02 — WPZOOM Forms

Date: 2026-10-27  
Mission: Waterfound Revenue Mission (WRM)  
Track: non-crypto research income / Patchstack Alliance  
Disposition: **HYPOTHESIS_FALSIFIED / NON_REPORTABLE_RESIDUAL / NO_REPORT / CHANNEL_ACTIVE**  
Observed Waterfound revenue: **USD 0**

## Commercial question

Can a current, eligible, publicly distributed WordPress plugin expose a narrow unauthenticated path to a Patchstack-accepted high-impact sink, producing an objectively verifiable and morally compatible bounty candidate without account creation, outreach, paid spend, or access to a third-party live system?

This target tests one predicate only:

> In WPZOOM Forms 2.0.10, can attacker-controlled data from the unauthenticated form-submission surface reach a high-impact sink such as stored/site-wide reflected XSS, arbitrary file operation, unsafe deserialization, SQL injection, privilege escalation, or significant broken access control?

## Target eligibility

- Plugin: WPZOOM Forms
- WordPress.org: https://wordpress.org/plugins/wpzoom-forms/
- Public source: https://github.com/wpzoom/wpzoom-forms
- Inspected source revision: `8bd2f69c98c853fb6906a6e543d3b585934872c7`
- WordPress.org state observed 2026-10-27: version 2.0.10, 10,000+ active installations, updated four weeks earlier, tested through WordPress 7.1.3.
- The plugin page directs security reports to Patchstack's vulnerability disclosure program.
- Patchstack controlling rules: https://patchstack.com/database/bug-bounty-program/
- Patchstack rules and rewards: https://patchstack.com/bug-bounty/terms-and-conditions/

This establishes channel and target eligibility. It does not establish a vulnerability, bounty acceptance, payout, customer demand, or WTP.

## Source-pinned inspection

### Anonymous submission path

The free plugin registers `admin_post_nopriv_wpzf_submit` in `classes/class-wpzoom-forms-submission-handler.php`.

The handler:

1. verifies the `_wpnonce` against `wpzf_submit`;
2. requires the referenced object to be a `wpzf-form`;
3. applies the honeypot and configured anti-abuse controls;
4. sanitizes field values by type:
   - email through `sanitize_email` and `is_email`;
   - URL through `esc_url_raw`;
   - textarea through `sanitize_textarea_field`;
   - remaining scalar fields through `sanitize_text_field`;
5. escapes labels and values with `esc_html` when composing the mail body;
6. accepts sender/reply-to values only after email validation;
7. persists submissions through WordPress post APIs using sanitized content.

No file-upload path exists in the inspected free version. No attacker-controlled unsafe deserialization, arbitrary file write, SQL construction, code execution, or unescaped site-wide rendering sink survived the source gate.

### REST surface

Routes in `classes/class-wpzoom-forms-rest.php` define permission callbacks:

- listing and builder metadata require `edit_posts`;
- creation requires the post type's `publish_posts` capability;
- per-form read, update, delete, and duplication use WordPress meta-capability checks and publishing capability where applicable;
- update inputs are sanitized before persistence.

The inspected REST surface therefore did not yield an unauthenticated or Subscriber-level path to the named high-impact sinks.

### Residual observation

The submission handler validates object type but does not independently require a published post status before accepting a nonce-bearing form identifier. A guessed draft/private form ID may therefore reach the intended submission workflow if a valid form nonce is also available.

Under the current evidence this residual is **not reportable**:

- it does not expose protected form configuration or stored submissions;
- it does not create Contributor-or-higher privilege;
- it does not produce an accepted high-impact file, SQL, deserialization, code-execution, or XSS sink;
- its observed effect is the plugin's intended form-submission/email/storage behavior;
- Patchstack excludes low-impact spam/rate-limit-style findings and requires significant security impact.

No claim is made that every deployment configuration is invulnerable. The bounded predicate above is falsified at the inspected revision.

## Dynamic-test decision

No dynamic fixture was built. Static source dataflow and authorization checks were sufficient to answer the named predicate negatively. Running a synthetic WordPress instance would add implementation activity without a surviving in-scope sink and would not increase commercial information enough to justify it.

No public or private live site was probed. No exploit payload was sent anywhere.

## Evidence accounting

| Evidence class | Result |
|---|---|
| Channel capability | Patchstack offers a public researcher route and traditional payout methods subject to its rules |
| Target eligibility | Public plugin, current release, 10,000+ active installs, explicit Patchstack VDP route |
| Observed security outcome | Named unauthenticated high-impact dataflow not found at pinned source revision |
| Competitive/differentiation evidence | Not applicable; this is a bounty target screen, not a product wedge |
| Demand evidence | Program existence only; no acceptance or payout evidence for Waterfound |
| WTP evidence | Program rules indicate bounty pools/rewards; no Waterfound report accepted |
| Revenue | USD 0 |

## Kill criteria and result

Target kill criteria:

- terminate if nonce, sanitization/escaping, capability checks, and absence of an accepted high-impact sink falsify the predicate;
- terminate if only intended form delivery, spam/rate limiting, speculative configuration, or low-impact metadata remains;
- never escalate a weak residual into a report to manufacture activity.

**Result: kill criteria met. Target 02 is closed without a report.**

## Channel disposition and next frontier

Patchstack remains **ACTIVE** because it provides a verified, non-crypto, traditional-payout research channel compatible with source-first screening.

The next target should not repeat a generic form-spam hypothesis. Prefer a current eligible plugin with a materially sharper sink class—file manager, import/export, backup/restore, archive extraction, or authenticated low-privilege object access—where one narrow unauthenticated/Subscriber predicate can be accepted or killed from pinned source.

## Authority and privacy boundary

This work used only public metadata and public source. It did not create a Patchstack account, submit a report, contact a maintainer, install code on an external account, publish commercial material, accept a contract, spend funds, perform KYC, or activate the Privacy P0 private producer candidate. It did not acquire the global writer lease, invoke a dispatcher, or write canonical operational databases.
