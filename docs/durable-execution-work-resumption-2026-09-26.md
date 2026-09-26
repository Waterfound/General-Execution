# Durable Execution — Work resumption, 2026-09-26

The exact Wave 5 source was retrieved and executed locally in Python 3.13.
It is **not a green candidate**. Updating the remote runner's binding alone
would not close the gate.

| Source | Result | Environment |
| --- | --- | --- |
| `8f6494eca2c730de49b2e6ebfeb085cad1f33744` | 289 passed, 16 failed | local Python 3.13.15 |
| `6cad261424c9f28e3b6651e656c6adafdb6954ee` | 318 passed, 17 failed | local Python 3.13.15 |
| `04a47cd7031b608368de15ec2c99ccc715eb6cbf` | 345 passed, 0 failed | local Python 3.13.15 |

These are full-repository executions with actual package imports. No shim,
test exclusion, skipped failing test, synthetic provider run, or Vercel receipt
is represented as external evidence. Logs and JUnit results are retained in
`evidence/durable-execution/2026-09-26/`.

The complete JUnit files are authoritative for case counts and individual
failures. The `candidate-before.log` stdout capture is partial; the corresponding
JUnit file retains all 335 cases and all 17 failures.

The [development checkpoint](../checkpoints/durable-execution-2026-09-26.json)
binds every tested Python/configuration file to the frozen Git commit and
records the provider blocker plus the exact next invocation.

## Corrections

1. The package imported `AspTransitionError`, `PassiveWakeAdmission`, and
   `admit_passive_wake` from two incompatible implementations under the same
   names. The second import silently replaced the first. The root API now binds
   these names to `asp_transition`, which is consumed by `resume_tick`.
   The signal-based variant remains accessible under `SignalAspTransitionError`,
   `SignalPassiveWakeAdmission`, and `admit_passive_wake_signal`.
   Both implementations retain their regression banks.
2. One policy-error assertion escaped the literal plus twice. It now checks
   the actual literal plus without weakening the error assertion.
3. One resume-tick test still passed the removed `required_core_revision`
   parameter. It now supplies the full `CoreVerificationRequirement` and still
   requires rejection of a mismatched policy digest.
4. The unpinned optional Vercel dependency resolved to `vercel==0.11.4`, whose
   `Sandbox` class lacks `create`. The v1 runner now pins `vercel==0.5.9`, whose
   installed implementation supports the exact synchronous
   `Sandbox.create`/`run_command` API and the frozen `node24` parameters.
   This proves API compatibility locally, not provider acceptance.
5. The SDK's `stop()` defaults to a non-blocking request. The runner now uses
   `blocking=True` where supported; shutdown timeout/failure prevents PASS.
6. The fixed harness retains failed conformance evidence and emits no receipt
   on FAIL/ERROR. Provider exception text is not persisted. `--output` creates
   an exclusive artifact so a rerun cannot overwrite an earlier receipt.
   `--preflight` checks SDK/auth configuration without invoking the provider.

## External state and authority

The Vercel connector identifies:

- team: `team_MHwznJgPOms2fJdgTInc1WZG`;
- project: `prj_0eyS5MBoYLjAMpWmHMJGBv5cjdIK`;
- project name: `general-execution-colony-runner`;
- current deployment: `dpl_6Uic6nBTvSQTNpUmThaY9V4F9Ymn`.

The current deployment's source was not changed. The connector's advertised
deployment tool returned `Tool deploy_to_vercel not found`. The browser
redirected to login; no authenticated dashboard operation was performed.
The Work terminal has no Vercel token/OIDC configuration. The user attempted
sign-in unsuccessfully and authorized continued work without it.

The old Wave 5 SHA must remain recorded as a rejected local regression target.
The subsequent checkpoint freezes the corrected Git SHA and explicitly rebinds
the harness and CORE-1 fixture to that source. This is candidate repair,
not admission of the failed source or relaxation of the verifier.

The next executable gate still requires the fixed Vercel sequence: exact SHA,
Python 3.13 plus SQLite, editable dev install, compileall, complete pytest, and
confirmed shutdown. Local results do not open the Vercel receipt interlock.

CORE-1 remains unexecuted. Provider triggers and unattended runtime remain
disabled. No merge, release, broader systems integration, spending, or
production authority was inferred from the local PASS.
