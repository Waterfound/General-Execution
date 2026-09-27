# Durable Execution branch protection preflight

This document defines the repository protection settings that remain outside the
Durable Execution runtime itself. They are repository-administration controls,
not runtime authority.

## Main branch

Target: `main`

Recommended rules:

- Require changes through a pull request before merging.
- Do not require a second human approval while this remains a single-maintainer
  repository; the pull-request requirement is for an auditable integration path,
  not artificial multi-person approval.
- Require the status check `main-integration-gate`.
- Require the branch to be up to date before merging.
- Block force pushes.
- Block branch deletion.
- Apply the rules to administrators as well, so ordinary repository-admin access
  does not silently bypass the integration gate.
- Keep linear-history enforcement disabled while merge commits are the canonical
  integration method.
- Keep merge queue disabled unless it is deliberately introduced later.

The required check is intentionally a single workflow that always runs for pull
requests targeting `main`. The existing specialized verification workflows use
path filters and therefore must not themselves be configured as globally
required checks.

## Runtime branch

Target: `runtime/durable-asp-control`

Recommended rules:

- Protect the branch so force pushes are blocked.
- Block branch deletion.
- Do **not** require pull requests: the durable provider must commit state and
  evidence directly to this operational branch.
- Do **not** require globally mandatory status checks on every runtime commit:
  runtime state commits intentionally use bounded automation and may include
  `[skip ci]`.
- Do not enable linear-history enforcement unless the runtime rebase/commit path
  is separately reverified under that rule.

The runtime workflows themselves remain the authority boundary:

- ordinary events: `events/*.json`;
- explicit human authority: `authority/*.json`;
- actor boundary: `Waterfound`;
- one shared concurrency group: `durable-asp-persistent-runtime`;
- no production, release, spending, credential, consensus, or mainnet authority.

## Administrative limitation

Repository-rule mutation requires GitHub repository administration permission.
The connected GitHub integration used by Durable Execution does not expose that
administrative write permission. Applying these settings is therefore a
one-time repository-owner action in GitHub Settings.

## Verification after activation

After protection is enabled:

1. Open a harmless pull request targeting `main`.
2. Confirm `main-integration-gate` is required and passes.
3. Confirm a direct update to `main` is rejected.
4. Confirm normal PR merge still works after the required check.
5. Confirm a normal runtime `events/*.json` bootstrap can still update
   `runtime/durable-asp-control`.
6. Confirm force-push and deletion remain blocked on both protected branches.
