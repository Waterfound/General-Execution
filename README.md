# General Execution

**Provider-neutral deterministic execution substrate**

Durable Execution candidate update (2026-09-26): the 1 Active + 1 Secondary + N
Passive branch now has **345 passing local Python 3.13 tests** after repairing
public ASP API collisions and verification-harness defects. The exact-source
Vercel gate and CORE-1 remain pending; unattended runtime is disabled. See the
[resumption record](docs/durable-execution-work-resumption-2026-09-26.md) and
[fixed harness](docs/durable-execution-wave5-verification-harness.md).

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

> **Execution consumes authority. It does not create authority.**

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> durable capacity lease
  -> durable dispatch intent
  -> provider reconciliation
  -> durable observed outcome
  -> restart-safe capacity release
  -> deterministic Session recovery projection
  -> bounded mechanical recovery driver
  -> external sandbox conformance provenance
  -> execution ledger
```

## Protocol milestones

- **v0.0.1 — Execution Kernel:** deterministic request identity, capability matching, logical attempts, result binding, ledger.
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate.
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct and retry lineage is explicit.
- **v0.0.4 — Capacity & Lease Semantics:** bounded parallelism, deterministic slots, CAS capacity state, explicit release.
- **v0.0.5 — Durable Head & Restart Recovery:** SQLite-backed capacity heads and unresolved-lease recovery.
- **v0.0.6 — Durable Dispatch Intent:** crash-safe outbox state, submission ambiguity, capacity-bound dispatch permits.
- **v0.0.7 — Provider Idempotency & Reconciliation:** stable invocation-key reconciliation and conservative resubmission decisions.
- **v0.0.8 — Provider Conformance & Attestation:** immutable adapter-revision attestation and same-invocation-only resubmission permits.
- **v0.0.9 — Executable Provider Conformance Harness:** executable provider-neutral cases and false-contract detection.
- **v0.0.10 — Durable Observed Outcome:** atomically retain the complete admitted physical outcome with the observed transition.
- **v0.0.11 — Session Recovery Projection:** reconstruct logical Session state from canonical durable execution evidence.
- **v0.0.12 — Bounded Recovery Driver:** apply at most one named mechanical restart action without transport or retry authority.
- **v0.0.13 — Vercel Sandbox Conformance Runner:** execute the exact repository regression bank from an exact Git SHA inside an externally identifiable Vercel Sandbox.

Detailed design notes are under [`docs/`](docs/).

## v0.0.13 fixed execution boundary

`VercelSandboxConformanceSpec` accepts only an exact lowercase 40-character Git SHA. The repository, Sandbox runtime, timeout, Python provisioning path, and validation commands are protocol-fixed.

The empirically validated sequence is:

```text
1. git rev-parse HEAD
2. sudo dnf -y -q install python3.13 python3.13-pip
3. python3.13 -c "import sys, sqlite3; print(sys.version); print(sqlite3.sqlite_version)"
4. python3.13 -m pip install -e .[dev] --disable-pip-version-check
5. python3.13 -m compileall -q src
6. python3.13 -m pytest -q
```

The Vercel Sandbox runtime is fixed to `node24`. Python 3.13 is provisioned inside that microVM because the direct `python3.13` Sandbox image proved unsuitable for the full General Execution bank: ordinary build isolation was required for `setuptools.build_meta`, and the direct Python image did not expose the native `_sqlite3` extension used by the durable stores.

The runner enforces:

- exact Git SHA verification before provisioning or tests;
- stop-on-first-nonzero semantics;
- fixed executable/argv identity in evidence;
- no caller-supplied repository, runtime, shell fragment, or command list;
- stdout/stderr represented by digests in canonical provenance;
- a non-empty provider-issued Sandbox identity; current Vercel `name` and older id-shaped SDK attributes are accepted;
- sandbox shutdown in `finally`, with shutdown failure preventing `all_passed`;
- no General Execution transport permit, automatic retry, domain verification, integration, or release authority.

## External evidence

Build Colony was used as the bounded coordinator while GitHub Actions were unavailable. It deployed an isolated Vercel worker without granting that worker project-write, verification, integration, release, automatic-retry, or production-transport authority.

A real Vercel Sandbox run executed the complete General Execution bank for revision:

`89a18db36cd41657a0099187bc4beb51fdf3c596`

Observed environment:

- Vercel Sandbox runtime: `node24`;
- Python: `3.13.14`;
- SQLite: `3.40.0`;
- editable dev installation: GREEN;
- `compileall`: GREEN;
- complete pytest bank: **157/157 GREEN**;
- sandbox shutdown: GREEN;
- GitHub Actions consumed: **0**.

Pytest stdout digest:

`sha256:f424985d6233d07fb5378c6e77b533a4c2409b59ee3c96e906ebfbb010a2b2d7`

The complete failure-domain discovery and evidence record is in [`docs/v0.0.13-vercel-sandbox-conformance-evidence.md`](docs/v0.0.13-vercel-sandbox-conformance-evidence.md).

## Candidate line

The intended canonical candidate chain remains linear:

```text
main v0.0.9
  -> v0.0.10 Durable Observed Outcome
  -> v0.0.11 Session Recovery Projection
  -> v0.0.12 Bounded Recovery Driver
  -> v0.0.13 Vercel Sandbox Conformance Runner
```

The old full-tree external run proves the complete history through the original v0.0.13 candidate. The final v0.0.13 freeze changes only its Sandbox environment/provenance surface and focused tests in response to that empirical evidence.

## First client

Build Colony remains the first client identity. It translates bounded Work Packages into `ExecutionSpec` objects. General Execution governs execution mechanics and recovery state; Build Colony retains engineering-evidence verification and serialized integration authority. See [`docs/build-colony-first-client.md`](docs/build-colony-first-client.md).

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

Optional Vercel SDK integration:

```bash
python -m pip install -e .[vercel-sandbox]
```

## Promotion gate

`main` remains on v0.0.9 until the **final frozen v0.0.13 SHA itself** is executed through the proven Vercel failure domain and returns:

- exact source SHA equality;
- Python 3.13 + SQLite availability;
- package install GREEN;
- compileall GREEN;
- full pytest GREEN;
- clean Sandbox shutdown;
- verified provenance identity.

Only after that gate should the linear v0.0.10–v0.0.13 chain be fast-forwarded to `main`.

## Status

**v0.0.13 is a stacked candidate with real external full-regression evidence. Final exact-SHA rerun is the remaining promotion gate.**
