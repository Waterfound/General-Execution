# Provider Portability live activation

This directory is the bounded operational surface for Provider Portability.

The live pool contains only resources that already existed and had independent execution evidence before activation.

Current eligible live dispatch resource:

- `ga-general-execution` — existing GitHub Actions production executor adapter.

Recorded but unavailable:

- `build-colony-cross-repo` — excluded from live dispatch while its existing cross-repository credential/capability gate remains unresolved.

Work is excluded because the current unattended Work budget is zero.

The activation does not create providers, accounts, identities, credentials, billing paths or paid resources.

A routing request is accepted only from Waterfound, carries no credential-shaped data, uses the pinned verified runtime source, and persists a receipt for Continuity Check.

When no eligible live resource exists, routing must defer fail-closed.
