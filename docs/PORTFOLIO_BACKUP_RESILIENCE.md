# Portfolio Backup Resilience — PBR-001

PBR-001 turns repository preservation from a one-time recovery proof into a
provider-independent unattended operating contract.

## Frozen terminal criterion

The capability is **not** terminal because one mirror run succeeds. Terminal
readiness requires, simultaneously:

1. provider-native automatic mirror cadence <= 60 minutes;
2. fail-closed freshness watchdog;
3. immutable/versioned snapshot at least daily;
4. clean-room restoration proven at least weekly;
5. machine-readable disaster-recovery capsule;
6. no routine Waterfound step.

The contract deliberately separates provider-neutral evidence semantics from
provider-bound scheduling and credentials. General Execution can verify that a
binding satisfies the contract; it cannot manufacture a GitLab schedule,
credential, provider project, storage bucket or authority.

## DI input

PB-DI-001 localized the observed failure boundary before mirror execution:
there are zero GitLab scheduled pipelines for the existing backup project,
the last successful run was API-triggered, and the mirror job is manual-only.
The mirror and off-host recovery primitives themselves have a positive control.

## Security

Secrets are not backup content. Recovery capsules identify required provider
bindings but never contain passwords, tokens, cookies, MFA values, wallet
private keys or seed phrases.
