# WRM Patchstack Target 03 — Widget Importer & Exporter

Date: 2026-10-27  
Mission: Waterfound Revenue Mission (WRM)  
Track: non-crypto research income / Patchstack Alliance  
Disposition: **LOW-PRIVILEGE HYPOTHESIS FALSIFIED / ADMIN-ONLY RESIDUAL / NO REPORT / CHANNEL ACTIVE**  
Observed Waterfound revenue: **USD 0**

## Commercial question

Can an unauthenticated or Subscriber-level actor use the current Widget Importer & Exporter upload/import surface to place attacker-controlled executable content, create stored XSS, disclose widget data, or make a significant unauthorized settings change that meets Patchstack's public-program impact threshold?

This target tests one bounded predicate:

> In Widget Importer & Exporter 1.6.2, can an anonymous or Subscriber-level request reach the `.wie` import/export path and produce arbitrary file upload, stored/site-wide XSS, protected data disclosure, or significant widget/settings modification?

## Target eligibility

- WordPress.org: https://wordpress.org/plugins/widget-importer-exporter/
- Official source: https://github.com/churchthemes/widget-importer-exporter
- Inspected revision: `e547575c5c70f7bf4d9c8126499461aee78e2c2d` (2026-10-15)
- Stable release: 1.6.2
- WordPress.org state observed 2026-10-27: 200,000+ active installations, updated six days earlier, tested through WordPress 7.1.3.
- Patchstack public-program rules: https://patchstack.com/database/bug-bounty-program/
- Patchstack terms and rewards: https://patchstack.com/bug-bounty/terms-and-conditions/

The install count, recency, public source, and accepted vulnerability classes make this a materially eligible target. They do not establish a vulnerability, acceptance, payout, customer demand, or WTP.

## Source-pinned inspection

### Access boundary

`includes/page.php` registers the import/export screen through `add_management_page(..., 'edit_theme_options', ...)`. The nonce fields for import and export are rendered only on this capability-gated management page.

The processing functions are attached to `load-tools_page_widget-importer-exporter`, not to `wp_ajax_nopriv_*`, `wp_ajax_*`, `admin_post_nopriv_*`, REST routes, or public frontend hooks.

Both import entry points enforce:

- `check_admin_referer('wie_import', 'wie_import_nonce')`.

The export entry point enforces:

- `check_admin_referer('wie_export', 'wie_export_nonce')`.

No anonymous or Subscriber-level nonce source or alternate public handler was found.

### Upload and file handling

`includes/import.php` accepts a `.wie` upload only after the capability-gated page and nonce path. It then:

1. sanitizes the client filename;
2. validates extension/MIME through `wp_check_filetype_and_ext`;
3. delegates movement and WordPress upload controls to `wp_handle_upload`;
4. reads and JSON-decodes the file;
5. deletes the temporary uploaded import with `wp_delete_file`;
6. rejects empty or non-object decoded data.

The current MIME compatibility helper allows `.wie` content detected as `text/plain`, `application/json`, or—in a narrowly scoped compatibility case—`text/html`. This is a security-sensitive residual because the upload location may be web-addressable on ordinary WordPress configurations.

It is not a reportable public-program finding under the observed path:

- the action is not reachable by anonymous or Subscriber roles;
- a valid import nonce from the capability-gated management page is required;
- the filename extension remains `.wie`, not PHP or another executable server-side extension;
- the file is consumed as JSON and deleted in the same request;
- no persistent attacker-controlled HTML rendering path was found;
- no cross-origin or nonce-bypass predicate survived source inspection.

This does not assert that every unusual hosting MIME configuration is safe. It closes the named public-program low-privilege predicate at the pinned revision.

### Imported widget settings

The import path converts the JSON object to arrays and passes each supported widget through the widget's native `WP_Widget::update()` sanitization path. The same `widget_update_callback` filter used by WordPress core is then applied.

For legacy widgets lacking a `WP_Widget` object, string values pass through `wp_kses_post` whenever the importing user lacks `unfiltered_html`.

Therefore the inspected code does not expose a low-privilege bypass that converts imported widget content into accepted stored/site-wide XSS.

### Export path

Export reads widget options only after the management-page and nonce boundary and streams JSON as an attachment. No public direct-download artifact is created, and no unauthenticated widget-data disclosure route was found.

## Dynamic-test decision

No dynamic WordPress fixture was built. The public-program predicate is defeated before a payload reaches the file or settings sinks: the only handlers are bound to a capability-gated admin screen and require nonces rendered on that screen.

A dynamic test of Administrator-authorized import would only prove intended product behavior and would not increase commercial information. No live site was probed and no payload was sent.

## Evidence accounting

| Evidence class | Result |
|---|---|
| Channel capability | Patchstack provides a verified non-crypto research/payout route subject to its rules |
| Target eligibility | Current public plugin, 200,000+ installations, source-pinned release |
| Observed security outcome | No anonymous/Subscriber path to upload, import, export, XSS, disclosure, or settings mutation |
| Residual | Admin-authorized `.wie` upload may accept text/html MIME; no low-privilege or persistent impact path found |
| Demand evidence | Program existence only; no Waterfound report acceptance |
| WTP evidence | Program reward rules only; no Waterfound payout |
| Revenue | USD 0 |

## Kill criteria and result

Target kill criteria:

- terminate if all relevant handlers remain behind `edit_theme_options` plus valid nonces;
- terminate if uploaded content is constrained to `.wie`, decoded as JSON, deleted, and widget values pass native sanitization;
- terminate if the only residual requires an Administrator intentionally using the import UI;
- never report administrative intended behavior or a speculative MIME condition as a public-program low-privilege vulnerability.

**Result: kill criteria met. Target 03 is closed without a report.**

## Channel disposition and selection lesson

Patchstack remains **ACTIVE**, but raw install count is not enough. A 200,000-install import plugin still yielded no admissible low-privilege path because WordPress management-page capabilities and nonce provenance collapsed the attack surface before the sink.

The next target should require one of these pre-screen properties before full inspection:

1. a public/Subscriber handler that reaches archive extraction, remote URL fetch, file read/write/delete, or object mutation; or
2. a nonce exposed to low-privilege users for a file-capable action; or
3. a REST/AJAX permission callback whose capability mapping is materially weaker than the sink.

Targets with only Administrator import/export screens should be rejected at pre-screen rather than consuming a full target slot.

## Authority and privacy boundary

Only public metadata and public source were read. No Patchstack account or report was created; no maintainer was contacted; no plugin was installed on a third-party system; no public commercial material, contract, payment, KYC, spending, or credential expansion occurred. Privacy P0 was not activated. No global writer lease, dispatcher, SQLite database, dispatcher bundle, or DISPATCH_FENCE was touched.
