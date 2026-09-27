# Wave 8 — provider-neutral adapters, inactive

Wave 5 and CORE-1 evidence qualifies immutable candidate
`04a47cd7031b608368de15ec2c99ccc715eb6cbf`. The recovered original CORE-1 report
has 13 passing assertions. These receipts do not claim external verification of
the new Wave 8 source.

`external_trigger.consume_external_trigger` accepts one externally admitted
event bound to an exact observation, portfolio, policy and transition. It opens
a fresh SQLite store, preserves the event identity binding, invokes at most one
existing `resume_tick`, and returns. The existing portfolio CAS remains the only
state transition mechanism. Historical checkpoint lookup makes late duplicate
delivery idempotent after subsequent generations. A crash before or after the
tick can be recovered by redelivery; a missed event can be delivered later if
its expected head remains current. Stale events fail closed and require a new
admission, not automatic rebasing or polling.

The host must independently authenticate the admission digest. That argument
must never be populated from an untrusted event body. This contract does not
implement webhook authentication, signature verification, a listener, cron,
network transport, or provider activation. The supplied event cannot carry an
authority grant. Actual host admission and verifier separation remain gates
before live integration.

`thin_envelope_escalation.prepare_escalation` creates an offline request bound
to the current durable state, checkpoint, tick, source revision and evidence.
Build Colony may return advisory work selection; DI may return diagnosis.
Neither response applies a transition or creates repair, transport or release
authority. Unknown systems, stale provenance, mismatched response identity and
human gates fail closed. An unavailable system yields `waiting_external`.
This is the narrow request/response boundary; no live Build Colony/DI transport
is activated and no compatibility with an external wire format is claimed.

Validation: 15 adapter tests cover concurrent/late duplicates, missed delivery
in a fresh process, both crash windows, evidence substitution, event collision,
stale heads, CORE-1 binding, human stops, DI unavailability and advisory-only
selection. Full repository regression: 360 passed, zero failures/errors/skips;
compileall passed on local Python 3.12.14. JUnit files are in
`evidence/durable-execution/2026-09-27/`.

Next frozen frontier: Wave 9, `verification-escalation`, establishing independent
verification and rejection/rework. Real provider triggers and unattended pilot
remain disabled and require the corresponding explicit activation authority.
