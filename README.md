# General Execution

**Provider-neutral deterministic execution substrate**

General Execution performs bounded work that another system has already authorized. It does **not** decide what should be built, whether a result is correct, whether it should be integrated, or whether it should be released.

```text
ExecutionSpec
  -> deterministic plan
  -> logical Session
  -> physical authorization
  -> capacity lease
  -> durable recovery context
  -> durable capacity head
  -> provider identity / status
  -> cold bootstrap
  -> provider reattachment
  -> reconciliation
  -> cut-point recovery assessment
  -> execution ledger
```

> **Execution consumes authority. It does not create authority.**

## Protocol milestones

- **v0.0.1 — Execution Kernel:** immutable request identity, deterministic capability matching, retry-safe logical attempts, result binding, and ledger.
- **v0.0.2 — Provider-neutral Adapter Contract:** authorization, transport, and evidence admission are separate.
- **v0.0.3 — Physical Failure Semantics:** logical and physical attempts are distinct; physical outcomes and retry lineage are explicit.
- **v0.0.4 — Capacity & Lease Semantics:** `max_parallelism`, deterministic slots, compare-and-swap capacity state, explicit release, and retry-capacity ordering.
- **v0.0.5 — Durable Head & Restart Recovery:** replayable capacity snapshots and conservative `in_flight_unknown` recovery.
- **v0.0.6 — SQLite Durable Head Persistence:** filesystem-backed canonical-head CAS.
- **v0.0.7 — Post-Restart Provider Reconciliation:** explicit source-to-target recovery plans and atomic reconciliation.
- **v0.0.8 — Provider Reattachment Semantics:** deterministic pre-dispatch reattachment keys and conservative status probes.
- **v0.0.9 — Reattachable Reference Provider:** durable provider identity/status control plane.
- **v0.0.10 — Durable Store Reopen Rehearsal:** two-store reopen QA with execution context explicitly caller-retained.
- **v0.0.11 — Durable Recovery Context + Cold Bootstrap:** stores-only reconstruction of runner, Spec, registry, plan, Session and physical authorization, followed by true cold provider reattachment and reconciliation. See [`docs/v0.0.11-durable-recovery-context.md`](docs/v0.0.11-durable-recovery-context.md).
- **v0.0.12 — Cross-Store Cut-Point Failure Matrix:** deterministic reconstruction of the exact safe state at every persistence/reconciliation boundary, including lost post-CAS acknowledgement. See [`docs/v0.0.12-cutpoint-failure-matrix.md`](docs/v0.0.12-cutpoint-failure-matrix.md).

## v0.0.12 cut-point states

The matrix freezes five canonical durable boundaries:

| Cut point | Reconstructed state |
| --- | --- |
| recovery context persisted | `orphan_context` |
| capacity head committed | `active_provider_unknown` |
| provider identity registered | `active_provider_running` |
| provider terminal state persisted | `terminal_pending_reconciliation` |
| reconciliation CAS committed | `settled_terminal_reconciliation` |

These states are derived from durable records only; the matrix does not use wall-clock expiry, sleeps, or timing assumptions.

### Conservative provider absence

If the capacity head is canonical but the provider key is absent, lookup produces `not_found` and the state remains `active_provider_unknown`.

```text
not_found -> remain_unknown
```

No physical failure is fabricated, capacity stays occupied, and retry is not authorized.

### Lost reconciliation acknowledgement

If reconciliation CAS committed and the coordinator lost the acknowledgement, the active lease is already gone. v0.0.12 reconstructs the historical settlement from:

- immutable recovery-context anchor;
- current canonical capacity history;
- exact canonical release;
- durable terminal provider observation;
- re-admitted physical outcome.

The state is `settled_terminal_reconciliation` only when the canonical release contains the exact same physical `outcome_digest` and receipt digest.

### Invalid ordering fails closed

Provider identity without a canonical capacity head violates the persistence order and is rejected. The supported ordering remains:

```text
recovery context
  -> capacity head
  -> provider identity
  -> terminal provider state
  -> reconciliation CAS
```

## Authority boundary

The failure matrix is recovery evidence only. It does not create retry, verification, integration, or release authority.

The logical boundary is unchanged:

```text
physical completion != logical result submission
```

## Development

```bash
PYTHONPATH=src pytest
PYTHONPATH=src python -m compileall -q src
python -m pip install -e . --no-build-isolation --no-deps
```

The core has no non-stdlib runtime dependencies; SQLite comes from Python's standard library.

## Current v0.0.12 conformance bank

The repository includes all five canonical cut-point classifications, safe orphan recovery, conservative provider `not_found`, terminal persistence without premature capacity release, post-CAS lost-ack reconstruction, invalid provider-before-capacity ordering, terminal-payload corruption rejection, and deterministic assessments across fresh filesystem paths.

## Admission state

v0.0.12 remains stacked above the v0.0.5-v0.0.11 candidate line. Canonical `main` remains at v0.0.4 until the full historical repository regression for the stacked line can be executed in a complete runner environment.

## Next ceiling

The next highest-value boundary is **durable logical Session settlement**. Physical completion and capacity reconciliation now survive cold restart and lost acknowledgements, but explicit `submit_result(...)` still changes only an in-memory `ExecutionSession`. A crash before or after logical submission therefore needs a durable, idempotent settlement protocol.

## Status

**v0.0.12 Cross-Store Cut-Point Failure Matrix: stacked implementation candidate under validation.**
