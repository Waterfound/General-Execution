# Build Colony — first client pilot

Build Colony is the first intended producer for General Execution, but General Execution does not import Build Colony or encode Build Colony-specific decision logic.

```text
Build Colony Work Package
        -> client-side translation
        -> ExecutionSpec
        -> AdapterDispatchRequest
        -> ProviderObservation
        -> InvocationBundle
        -> Build Colony evidence admission
        -> independent verification / integration
```

The v0.0.2 local pilot used `build-colony` as producer identity and passed the complete contract:

- request identity reproduced exactly;
- provider observation admitted against the exact request;
- invocation bundle verified;
- four-event ledger record verified;
- result was accepted by the exact active Session;
- no verification or integration authority moved into General Execution.

Observed deterministic identifiers from the pilot:

```text
spec_id       = ges-b7de5ec9302e2cfbd2a574a9
session_id    = gex-bbeec79d82ae31edc3cb28c8
request_id    = ger-01f45291ab83fe23f3d08c53
bundle_digest = sha256:5e6605ee224f8fcc0ec79adde672a68af43a3d070a17ef0d8172567f94f50b31
ledger_head   = sha256:f345aa36f73ce4a00466f21beeedf6a84bb17797b8b8ad1523a1e222d5ced1d8
```

These values are conformance evidence for this frozen local pilot, not globally privileged identities.
