# Wave 5 Exact-Source Verification Harness

## Purpose

`scripts/verify_wave5_core.py` is the single fixed entry point for closing the Durable Execution Wave 5 executable gate.

It does not accept a revision, repository, command list, suite, test path, verifier, or minimum test count from the caller.

Those values are frozen in source.

## Frozen target

```text
revision:
8f6494eca2c730de49b2e6ebfeb085cad1f33744

repository:
https://github.com/Waterfound/General-Execution.git

suite:
tests://durable-execution/wave5-asp/full-repository

focused contract:
tests/test_asp_transition.py

focused cases:
18

verifier:
verifier://vercel-sandbox-conformance/v1
```

The Vercel runner itself remains protocol-fixed to:

```text
node24
-> install Python 3.13 + pip
-> prove sqlite3
-> editable dev install
-> compileall src
-> full pytest
-> clean Sandbox shutdown
```

## Provider configuration

The script may consume provider authentication/routing from environment only:

- `VERCEL_TOKEN`
- `VERCEL_TEAM_ID`
- `VERCEL_PROJECT_ID`

These values are passed only to Sandbox creation. They are not persisted into the emitted verification receipt.

They do not alter the Git source, revision, runtime, command sequence, suite, or verifier contract.

## Output

On complete GREEN, stdout contains one canonical JSON object binding:

- verification manifest + digest;
- Vercel Sandbox spec + digest;
- conformance run + digest;
- admitted CoreVerificationReceipt + digest.

Any source-revision mismatch, failed command, failed pytest, failed shutdown, or inconsistent evidence raises/fails instead of fabricating a receipt.

## Authority boundary

A valid receipt opens only the Wave 6 technical interlock for the tested core contract.

It does not authorize:

- merge to `main`;
- unattended production execution;
- spending beyond an existing authority;
- release;
- credentials;
- consensus/economics changes;
- mainnet;
- provider trigger activation.

CORE-1 must still pass separately.
