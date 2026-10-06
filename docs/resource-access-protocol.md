# Resource Access Protocol

Status: candidate operational protocol. **No secrets are stored here.**

## Purpose

Preserve enough durable knowledge to reconstruct how authorized systems reach project resources after chat/session loss, without turning documentation into an access credential or a topology leak.

Canonical rule:

> **Remember the route, never persist the key.**

This protocol records **access classes and resolution order**, not passwords, tokens, cookies, seed phrases, private keys, MFA recovery material, session payloads, or decrypted environment secrets.

## Resolution order

For any resource needed by Build Colony, Durable Execution, Work, or an agent:

1. resolve the **logical resource class**;
2. prefer an already-authorized **connector/API**;
3. use repository/runtime evidence to resolve the exact project/workstream identity;
4. if the connector session is unavailable, classify whether reauthentication is human-required;
5. use authenticated browser/Work only when the connector/API cannot complete the task;
6. never persist browser cookies, bearer tokens, passwords, passkeys, MFA secrets, or decrypted secret values;
7. if access cannot be reconstructed safely, stop at a genuine human/authentication gate.

## Logical access classes

| Alias | Preferred route | Durable knowledge | Human boundary |
| --- | --- | --- | --- |
| `canonical-source` | GitHub connector/API | repository + branch + SHA + PR + workflow evidence | reconnect/install authorization if connector scope expires |
| `durable-runtime` | GitHub-backed General Execution persistent runtime | events, processed receipts, reports, state/database digests | authority transitions only |
| `build-colony` | GitHub connector/API + GitHub Actions | profile, manifest, ledger, workflow run IDs | no routine login while connector works |
| `vercel-hosting` | Vercel plugin/API | project identity resolved through authenticated account context; exact deployment evidence when relevant | browser login only when plugin/API cannot perform account-bound step |
| `render-hosting` | Render connector/API when available; authenticated dashboard otherwise | service identity and exact source binding are evidence, but credentials are not | dashboard login/MFA and secret insertion remain human gates |
| `aws-compute` | AWS connector/API under explicit cost/authority envelope | region/resource/workload identity and spend ceiling may be recorded; credentials are not | login/role/MFA or any new spend/privilege expansion is a human gate |
| `local-compute` | local device/workspace reached through the authorized execution surface | device class + capability + evidence artifact | physical access, power state and local login remain human/physical gates |
| `other-provider` | provider-native connector/API first | record only the minimum locator/evidence needed for reconstruction | authentication, billing or privilege changes remain human gates |

## Current operational policy

### GitHub / canonical repositories

GitHub is the preferred durable control and evidence plane for source, branches, PRs, workflows, Build Colony artifacts and General Execution runtime events.

Prefer connector/API operations over browser sessions.

A branch/SHA/workflow receipt is durable evidence. A logged-in browser tab is not.

### General Execution / Durable Execution

The persistent runtime is reconstructed from repository-resident events, processed receipts, reports, checkpoints and the bound state database digest.

Chat history is not required to recover runtime state.

### Build Colony

Build Colony work should be reconstructible from its profile, source revision, Run Manifest, ledger/evidence and workflow receipts.

Remote capacity does not grant project authority. Runner/provider access remains downstream of an existing authority envelope.

### Vercel

Prefer the Vercel plugin/API because its authenticated account context is separable from a browser login.

Use an authenticated browser only for a task the API/plugin cannot complete or when provider-side interactive authentication is explicitly required.

Do not persist temporary share/auth bypass links as durable project credentials.

### Render

Prefer connector/API access when it exposes the required operation.

Dashboard access is an explicit human-mediated fallback for operations such as provider login, MFA, source-binding steps not available through the connector, or insertion/rotation of protected secret material.

Do not record Render cookies, passwords, MFA data, or secret values.

### AWS

Use AWS through the provider connector/API under an explicit authority and spend envelope.

Resource identifiers and bounded execution evidence may be durable; account credentials, access keys and session tokens may not.

Any new paid resource, privilege expansion, account authentication requirement or spending beyond the established envelope must fail closed to human authority.

### Local compute

Local compute may be treated as a resource class, but remote documentation must not pretend physical reachability.

Persist only capability/evidence metadata. Power-on, local authentication, device attachment and other physical dependencies remain explicit gates.

## Session durability model

| State | Meaning |
| --- | --- |
| `CONNECTOR_AVAILABLE` | use connector/API directly |
| `SESSION_REUSABLE` | an existing authenticated session may be reused, but is not durable truth |
| `REAUTH_REQUIRED` | human login/MFA/passkey/CAPTCHA or equivalent is required |
| `AUTHORITY_REQUIRED` | credentials may work, but the requested action exceeds current authority |
| `UNRESOLVED` | exact resource cannot be resolved safely from durable evidence; fail closed |

A future agent should never interpret `REAUTH_REQUIRED` as permission to seek or store the user's credentials.

## Stealth constraints

Resource-access documentation must not become an external observability amplifier.

Therefore:

- prefer logical aliases over publishing unnecessary account/project topology;
- keep exact locators only where they are already required for canonical evidence;
- do not create public discovery endpoints merely to simplify access;
- do not publish secret-bearing configuration;
- do not weaken Continuity Check: authorized internal reconstruction must remain possible;
- do not weaken Full Autonomy: once connector/API access is already authorized and available, proceed without asking for redundant human action.

## Recovery algorithm

```text
need resource
  -> resolve logical class
  -> inspect durable evidence for target identity
  -> connector/API available?
       yes -> operate inside authority
       no  -> reusable authenticated session available?
                yes -> use only if needed
                no  -> classify REAUTH_REQUIRED
  -> action exceeds authority?
       yes -> AUTHORITY_REQUIRED
  -> persist receipt, never credential
```

## Anti-memory rule

Never rely on a statement such as “I remember being logged in.”

Instead prove one of:

- connector/API call succeeds;
- provider/session evidence resolves current authenticated context;
- durable runtime receipt proves the resource state;
- a genuine human reauthentication gate is present.

> **Memory suggests. Access evidence decides.**
