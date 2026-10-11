# Public/private state separation — P0 candidate

**Status: CANDIDATE. Active runtime privacy: OPEN.**

## Observed failure mode

The provider-triggered durable host currently commits a serialized SQLite database and detailed event/transition/authority evidence to a **public** repository branch. This material exposes workflow identity, objectives, dependency observations and authority boundaries. It is more revealing than the opaque, task-scoped public contract requires. Existing public commits remain historically recoverable even if files are later removed.

The candidate adds:
1. \`general_execution.publication_boundary\`: path, encoded/raw SQLite, stable identifier and operational schema rejection, with public-safe error categories.
2. Digest-only public receipt factory with no private payload passthrough or authority.
3. A candidate Git diff gate with sanitized output and adversarial unit tests.

**Do not mistake this for activation:** a PR check runs after branch publication. The effective preventive gate belongs in the PRIVATE trusted publisher before any public Git write.

## Required migration and acceptance

1. Freeze a verifiable exact-head snapshot and live-event sequence without interrupting admitted work. Verify digest, append-only event chain, independently retained backup and an actual private clean-room recovery.
2. Select a **private** persistent state destination with proven control, capacity and bounded credentials. Public-source audit code and generic proof receipt definitions may stay public. Detailed SQLite state, event payloads, human decisions, authority receipts, private strategy and unminimized service/provider metadata must be placed exclusively in the private boundary.
3. Compare pre-cutover and reconstructed state digests; test replay/idempotence, restart, human-gate stop, provider event admission, concurrency and failure recovery in a private rehearsal. Never call a synthetic rehearsal real recovery.
4. Activate a bounded, explicitly authorized runtime host cutover only after verifying the source pin, workflow changes, access scope, rollback and zero paid cost. No live mutation or repin is authorized by **this candidate PR**.
5. Require the egress guard to execute BEFORE publication and verify that new public commits contain only minimal digest-bound receipts with a verifiable no-private-payload contract. Observe at least one genuine admitted transition and its exact source/result lineage with no new public private-state writes.
6. Review historical Git branches, commits, PRs, Actions logs, published artifacts and mirrors. Classify legacy exposure separately; history deletion alone does not reclaim previously public information. Any verified credential exposure requires the credential owner to rotate it under exact separate authorization.
7. After independent recovery and no-new-leak tests, issue an exact evidence-bound terminal verdict. Until then the status is **PRIVACY_OPEN**.

## Non-negotiable boundaries

- No merge, public runtime workflow modification, runtime source repin, scheduler activation, new credential or provider mutation, paid usage or destructive deletion in this candidate.
- No private architecture registry, stable internal identifier mapping or System dependency/authority graph in public diagnostics.
- Candidate tests prove classifier invariants only; do not imply exhaustive historical exposure inventory.
- Preserve public source and independently verifiable mechanics, while moving actual mutable operating state to a private persistence plane.
