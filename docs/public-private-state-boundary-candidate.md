# Generic public egress contract — candidate

This document describes a public-code mechanism for minimizing data emitted to public artifact stores. It is not a live-runtime configuration, security incident report, operational inventory or activation authorization.

## API

- Reject publication to reserved mutable-state, identity, authority and event paths.
- Reject database payloads and serialized database images regardless of suffix.
- Reject stable private semantic aliases and nested operational-state fields.
- Fail closed on invalid JSON where a JSON receipt is required.
- Report only generic finding categories and totals, never matched sensitive values.
- Create receipts from a strict allowlist of digest-only inputs; no arbitrary metadata passthrough and no authority or execution claim.

## Deployment contract

1. Apply the boundary **before** any external public write. A pull-request check evaluates already-published candidate diffs and is not a preventive security perimeter by itself.
2. Store mutable operating state and unminimized evidence under a private, authenticated, independently recoverable state owner.
3. If a public proof is necessary, publish only schema-bound digests and general pass/fail information with explicit audit lineage.
4. Independently verify private recovery, replay handling, stop conditions, minimal publication, source pins, rollback and zero duplicated writers before any host migration.
5. Historical source, branches and caches may remain recoverable after a delete operation; handle legacy material with the appropriate private incident owner.
6. Never create authority, broaden provider credentials, repin a running executor, activate scheduling, or spend money based on successful candidate tests.

**Disposition: candidate mechanism only.** Public/private operating-boundary closure requires separate evidence from the active private execution owner. Detailed inventory and migration action refs must not be published here.
