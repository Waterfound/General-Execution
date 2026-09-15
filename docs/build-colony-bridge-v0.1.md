# Build Colony bridge v0.1

This is General Execution's first concrete client bridge produced from the System Interoperability Envelope onboarding pilot.

The consumer accepts only a pinned `build_colony_session_dispatch_request` artifact. It replays wrapper, capability, request and dispatch-ID digests before deriving an `ExecutionSpec`.

Build Colony constraints that do not have first-class General Execution fields are not discarded. The bridge serializes `invariants`, `exclusive_resources`, dependencies and gate definitions into canonical metadata and sets:

```text
required_capabilities = ("build_colony.session-dispatch.v1",)
```

A generic runner that does not explicitly advertise this capability is therefore incompatible and the existing planner fails closed with `no_compatible_runner`.

The returned `general_execution_admission_receipt` is admission-only:

```text
accepted                = true
execution_authorized    = false
verification_authorized = false
integration_authorized  = false
promotion_authorized    = false
```

The receipt can be consumed by Build Colony to bind its native retry-aware session. No provider transport is introduced by this bridge version.
