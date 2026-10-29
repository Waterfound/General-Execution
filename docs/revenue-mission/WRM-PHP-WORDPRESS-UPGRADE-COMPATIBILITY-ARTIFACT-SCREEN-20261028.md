# WRM — PHP / WordPress Upgrade Compatibility Artifact Screen — 2026-10-28

Status: **REPEATED_PAID_SERVICE_DEMAND / STATIC_ARTIFACT_DIRECTLY_SUBSTITUTED / REMEDIATION_AND_RUNTIME_PROOF_BOUND / NO_BUILD**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Can Waterfound sell a narrow, read-only compatibility report for a public or customer-supplied PHP/WordPress/Laravel codebase before an upgrade, without production credentials or ongoing human remediation?

## Current buyer evidence

Recent marketplace postings show repeated willingness to pay for successful upgrades:

1. A 2026-10-27 Upwork posting seeks PHP 7.4 to 8.4 stabilization for a WordPress child theme at US$15–35/hour. Acceptance includes diagnosing the critical error, locating the responsible theme/plugin combination, making minimum code changes and preserving site behavior.
   https://www.upwork.com/freelance-jobs/apply/PHP-Code-Compatibility-Update_~022114800213923330287/

2. A worldwide Laravel/PHP upgrade job posted 2026-10-24 offers US$20 fixed price for diagnosis, dependency updates, server/config fixes and full functional testing.
   https://www.upwork.com/freelance-jobs/apply/Laravel-Developer-Needed-Fix-Website-After-PHP-Version-Upgrade_~022114055930865402154/

3. A WordPress upgrade listing offers US$180 and requires backup, WordPress/plugin updates and recovery safety.
   https://www.upwork.com/freelance-jobs/apply/WordPress-Version-and-Plugin-Update_~022098808150515305977/

4. A Freelancer WordPress/PHP migration job requests a pre-upgrade report, live upgrade, zero functional regressions, post-upgrade test log and handoff note for US$10–30; it displayed 16 proposals.
   https://www.vn.freelancer.com/projects/website-development/wordpress-blog-php-upgrade

5. A Laravel 7-to-current modernization listing shows a US$1,500 CAD bid for framework, PHP, dependency, Sentry, server and deployment migration with staging and rollback.
   https://www.freelancer.com/projects/git/laravel-web-app-upgrade-migration

6. A heavily customized WordPress plugin upgrade at US$25–50/hour requires SSH, WP-Admin and staging credentials, actual refactoring, full membership/form/booking flows, clean logs and change documentation; it displayed 152 proposals.
   https://www.freelancer.com/projects/css/custom-wordpress-plugin-site-updates

This is strong service demand, but the paid acceptance predicate is an upgraded, functioning system—not a scanner report alone.

## Direct substitution of the machine-only artifact

The read-only/static layer is already occupied:

- **PHPCompatibility** scans source for cross-version PHP incompatibilities and can emit a full report file.
  https://github.com/PHPCompatibility/PHPCompatibility
- **PHPCompatibilityWP** applies the compatibility ruleset specifically to WordPress projects.
  https://github.com/PHPCompatibility/PHPCompatibilityWP
- WordPress.org distributes compatibility scanners that report file/line failures for target PHP versions through 8.4 and plugins that scan PHP/database/WordPress compatibility.
  https://wordpress.org/plugins/eli-php-compatibility-scanner/
  https://wordpress.org/plugins/plugin-compatibility-checker/
- WordPress documentation directs operators to compatibility checking before upgrading PHP.
  https://wordpress.org/documentation/update-php/
- **Rector** provides PHP upgrade rule sets and automated refactoring.
  https://getrector.com/documentation/levels
  https://getrector.com/documentation/set-lists
- **Laravel Shift** automates Laravel upgrades, dependency changes and common code migrations; Laravel's official upgrade guide names it as an upgrade aid.
  https://laravelshift.com/
  https://laravel.com/framework/docs/12.x/upgrade

A new static scanner, normalized report or upgrade checklist would duplicate established free/native/paid tools.

## Residual value boundary

The buyer pays for work that static analysis cannot prove:

- booting the actual application under the target runtime;
- resolving theme/plugin/package interactions;
- repairing code and deployment configuration;
- exercising authentication, forms, bookings, queues, schedules, database paths and admin flows;
- preserving customer-specific behavior;
- backup/restore and rollback;
- staging and production deployment;
- accepting responsibility for regressions.

These require private repositories, databases, logs, staging environments and human/business acceptance. They cannot be reproduced safely from a public fixture as evidence of the buyer's real outcome.

## Decision

Do **not** build:

- a PHP-version compatibility scanner;
- WordPress theme/plugin compatibility report;
- Laravel upgrade-readiness score;
- generic deprecated-API inventory;
- upgrade checklist or static evidence dashboard.

The machine-only predicate is directly substituted, while the paid predicate is remediation and representative runtime verification. A synthetic proof would establish only a capability already available in PHPCompatibility/Rector/Shift and would not establish buyer value.

Preserve compatibility scanning only as **SUPPORT_ONLY** if a future admitted job independently requires it.

## Kill criteria reached

1. A maintained free tool already produces the named compatibility findings: **reached**.
2. Framework-specific automation already performs common migrations: **reached**.
3. Buyer acceptance requires a running private application and remediation: **reached**.
4. Higher-value work requires credentials and customer-specific regression judgment: **reached**.
5. No public buyer requests only the static artifact at a price supporting differentiation: **not observed**.

## Re-entry criteria

Re-open only if two independent current buyers request the same bounded artifact and:

1. acceptance explicitly excludes code changes, deployment and full functional assurance;
2. the artifact reveals a decision-relevant class missed by PHPCompatibility, Rector, WordPress scanners and Laravel Shift;
3. a public or user-supplied fixture demonstrates higher recall, lower review time or better provenance;
4. delivery requires no privileged access or recurring Waterfound operation;
5. external contact, proposal, contract and payment remain separately authorized.

## Evidence accounting

| Predicate | State |
| --- | --- |
| Repeated buyer/problem evidence | Observed |
| Paid service demand | Observed |
| Demand for static Waterfound artifact | Not observed |
| Direct substitutes | Strong / established |
| Differentiation | Falsified |
| Capability proof | Not admitted; would answer a solved predicate |
| Waterfound WTT / WTP / revenue | None / none / USD 0 |
| Mission posture | Candidate closed; discovery remains ACTIVE |

No customer code, credentials, staging environment or logs were acquired. No proposal, outreach, account, installation, remediation, deployment, publication, contract, payment/KYC, spend, runtime activation or Privacy P0 activation occurred.
