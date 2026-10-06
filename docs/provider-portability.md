# Provider Portability Contract

Status: candidate software extension. No live routing authority.

## Purpose

Bind exact internal work to a minimal provider-visible task envelope, then route that envelope only to resources already admitted by authority.

The provider-facing object deliberately excludes:

- internal work IDs;
- portfolio names;
- source branch names;
- human-readable project/frontier objectives;
- internal authority lineage;
- semantic context that is not necessary for execution.

The internal evidence plane retains those fields in `InternalLineageBinding` and binds them to the provider envelope by digest.

## Correct attribution

The external envelope includes `billing_scope_ref` because provider ownership/accounting must remain truthful.

Semantic minimization is not identity spoofing.

## Resource dispositions

- `AVAILABLE`: eligible when capability and authority checks pass.
- `UNAVAILABLE`: excluded from routing.
- `DECLINED`: excluded from routing.

A declined resource is not retried by this planner. If another independently authorized resource is available, the task may be projected into a new provider task envelope for that resource. Otherwise the route is deferred.

## Authority

The route decision fixes:

- `authority_created=false`
- `execution_authorized=false`

The planner selects a candidate resource only. Existing dispatch/live-execution gates remain authoritative.
