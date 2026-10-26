# Solo Stack Continuity Auditor v0

Candidate proof for one narrow job: **show a solo software founder which repository-visible operational dependencies are not covered by a successor/recovery plan**.

The CLI is read-only, uses the Python standard library, scans a local repository, records secret names but never values, and emits:

- a private metadata report containing observed workflows, schedules, providers, domains, and declared recovery controls;
- explicit continuity gaps; and
- a SHA-256 public attestation that can prove the report existed without publishing its contents.

Run the synthetic proof:

    python3 continuity_audit.py fixture
    python3 -m unittest -v test_continuity_audit.py

This is not a password manager, backup product, legal estate plan, provider integration, or claim that recovery works. It does not access GitHub APIs, provider accounts, secret values, billing, customer data, or external networks.
