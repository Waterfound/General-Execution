# Wave 5 Exact-Source Verification Harness

## Purpose

`scripts/verify_wave5_core.py` on the development checkpoint is the fixed controller for the Durable Execution Wave 5 executable gate. The isolated operational branch uses `ops/verify_wave5_candidate.py`, a byte-identical copy of that controller frozen at `53bd734ef3faeccc2618058c742bc3c92572bcdc`.

It does not accept a revision, repository, command list, suite, test path, verifier, or minimum test count from the caller.

Those values are frozen in source.

## Frozen target

```text
revision:
04a47cd7031b608368de15ec2c99ccc715eb6cbf

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

This target supersedes `8f6494eca2c730de49b2e6ebfeb085cad1f33744` after
16 failures were reproduced in the old full regression bank. The corrected
source passed 345 local tests. That local result is not a Vercel receipt.

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

## Invocation and output

Install the exact optional SDK boundary with `python -m pip install -e '.[dev,vercel-sandbox]'`.
It pins `vercel==0.5.9` to preserve the synchronous v1 runner protocol.

First run the offline preflight:

```bash
python scripts/verify_wave5_core.py --preflight
```

It invokes no provider and emits no verification receipt. Exit 2 means SDK or
authentication configuration is missing. Once authenticated execution is
available, the fixed invocation is:

```bash
python scripts/verify_wave5_core.py --output evidence/wave5-vercel-run.json
```

The output path must not already exist. No revision override is accepted.

On complete GREEN, stdout and the optional file contain a v2 JSON object binding:

- verification manifest + digest;
- Vercel Sandbox spec + digest;
- conformance run + digest;
- admitted CoreVerificationReceipt + digest.

Exit 0 / `PASS` includes an admitted receipt. Exit 1 / `FAIL` retains the
conformance run without a receipt. Exit 2 / `ERROR` preserves only safe error
classification when no complete conformance run could be returned; the provider
state must be reconciled before another attempt. Exception messages and credentials
are never serialized. Shutdown is awaited with the SDK's blocking stop.

Any source-revision mismatch, failed command, failed pytest, failed shutdown, or
inconsistent evidence prevents a receipt. No automatic retry is performed.

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

## Operational deployment checkpoint — 2026-09-26

Deploy `ops/wave5-vercel-verification` at `0949c447d988caaf7f083cb6d2798cfd2301c018`.
The original operational commit `aa1fd573...` must not be deployed: because it was
based on the immutable candidate, its candidate-internal historical script still
targets the rejected `8f6494...` source. This discrepancy was proved before any
Sandbox invocation.

The corrected ops branch adds a separate entrypoint with the fixed `04a47cd...`
target; all 100 candidate files remain byte-identical. Its only delta from the
candidate is `ops/verify_wave5_candidate.py` and `vercel.json`. Preflight JSON is
retained in both stdout and an exclusive file, so a failing build retains the
non-secret preflight evidence. No endpoint, cron, or runtime trigger is added.

The local preflight confirmed SDK compatibility and returned exit 2 because no
Vercel authentication was configured. The browser also redirected to login.
No external run or CoreVerificationReceipt exists. See
`../evidence/durable-execution/2026-09-26/ops-binding-repair.json`.
