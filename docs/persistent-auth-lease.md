# Persistent Auth Lease + Provider Queue

Status: candidate extension stacked on Work-Sparse Unattended Execution (PR #17) and EAC-01 (PR #16).

## Goal

Reduce repeated human authentication without storing or recreating credentials and without attempting to defeat provider session-expiry policy.

The design selected by a real Build Colony frontier optimization is:

```text
provider-bound work
  -> provider queue
  -> auth capability evidence
       connector/API available? use it first
       browser session available? reuse it
       evidence stale/uncertain? probe before asking human
       provider rejected/challenged? HUMAN_REAUTH_REQUIRED
  -> one human authentication event
  -> AUTH_AVAILABLE
  -> drain already-authorized queued work while auth remains accepted
```

Build Colony evidence:

- research branch: `research/persistent-auth-lease-001`;
- frontier decision digest: `85821e385dc00015c9a62b3e61a2048572278c2495b7584514fffb72d6fff481`;
- selected candidate: `candidate-b-auth-lease-queue`;
- utility: 8790 bp;
- browser keepalive alternative: 3975 bp;
- durable secret persistence alternative: 3075 bp;
- CI run `37429215393`: SUCCESS on Python 3.11/3.12/3.13;
- remote-pool-ci `37429215395`: SUCCESS.

The optimizer fixed `authority_created=false` and `execution_authorized=false`.

## What is durable

Only non-secret capability evidence is durable:

- provider id;
- auth surface (`connector_api` or `cloud_browser`);
- state;
- generation and previous digest;
- observation time;
- evidence reference and digest.

The durable schema has no field for a password, MFA value, cookie, API key, bearer token or browser-session payload.

Every auth artifact also fixes:

```text
credentials_persisted = false
cookies_persisted = false
tokens_persisted = false
authority_created = false
```

The actual authenticated session remains provider/ChatGPT-connector/browser managed.

## State machine

```text
AUTH_SUCCESS     -> AUTH_AVAILABLE
AUTH_UNCERTAIN   -> AUTH_SUSPECT
AUTH_REJECTED    -> HUMAN_REAUTH_REQUIRED
AUTH_CHALLENGE   -> HUMAN_REAUTH_REQUIRED
```

A later successful provider observation returns the same provider/surface lineage to `AUTH_AVAILABLE`.

Age alone never manufactures `HUMAN_REAUTH_REQUIRED`. An evidence-freshness policy may downgrade an old `AUTH_AVAILABLE` observation to an effective `AUTH_SUSPECT`, which means **probe first**. Human reauthentication requires explicit provider rejection/challenge evidence.

This deliberately maximizes legitimate session reuse.

## Auth path priority

For one provider:

1. authenticated connector/API capability;
2. authenticated existing cloud-browser session;
3. suspect connector/API -> probe;
4. suspect browser session -> probe;
5. provider rejection/challenge -> one consolidated human reauth gate.

There is no keepalive loop. The controller never sends browser traffic merely to prolong a session.

## Provider queue

Tasks blocked on the same provider are stored as non-secret queue records.

If three Vercel tasks are waiting and no accepted auth evidence exists, the controller emits one provider-level human gate with `queue_depth=3`, not three login requests.

After one human login succeeds:

```text
HUMAN_REAUTH_REQUIRED
  -> provider AUTH_SUCCESS evidence
  -> AUTH_AVAILABLE
  -> bounded drain plan [q1, q2, q3]
```

Drain planning never claims that work executed:

```text
execution_triggered = false
authority_created = false
```

The selected queue item still flows through Work-Sparse / existing launch admission and EAC-01.

## Restart safety

`SqliteProviderAuthStateStore` persists auth-lease heads and provider queues transactionally.

- lease transitions are compare-and-swap bound;
- queue IDs cannot be rebound to different work;
- drained items require exact item digest and evidence;
- repeated drain admission is idempotent;
- a restart reconstructs both auth evidence and outstanding provider work.

## Security boundary

This candidate does **not**:

- extend provider TTLs;
- bypass MFA/passkeys/CAPTCHA;
- persist or expose credentials;
- create API keys;
- alter connector permissions;
- log into a provider without the human when the provider demands human authentication;
- authorize Work consumption, paid spend, merge, release, consensus/economics, physical hardware or mainnet.

The intended effect is fewer repeated logins through legitimate session reuse and batching, not weaker authentication.
