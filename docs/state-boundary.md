# State Boundary

This candidate separates durable state visibility from execution-resource selection.

It is a pre-cutover proof surface. It does not move live state, change repository visibility, repin a runtime, create provider resources, alter credentials or authorize execution.

## Core rule

```text
state storage visibility
        !=
execution resource
```

A private state plane must not imply that execution is bound to the same storage provider or to a particular hosted-runner class.

## Public surface

The public side may receive only a minimal opaque state receipt:

- opaque `state_ref`;
- blob digest;
- byte count;
- storage visibility;
- receipt digest.

It does not receive:

- storage path;
- private state content;
- project/workstream identity;
- provider topology;
- authority lineage;
- private semantic mapping.

## Preservation contract

A candidate boundary is acceptable only when:

1. durable semantic receipts are equivalent before and after the boundary;
2. authority stop / human-gate semantics are unchanged;
3. the same evidence predicate is preserved;
4. storage and compute remain independently selectable;
5. restart/recovery reconstructs the same state and checkpoint;
6. existing executor selection remains unaffected by the storage location.

Any semantic, authority, evidence or storage/compute-coupling regression fails closed.

## Candidate local/private transport

`FilePrivateStateBoundary` is only a proof primitive. It demonstrates that rich state can be kept outside a public receipt while preserving exact bytes and digest verification.

It is not the future production storage provider and creates no provider commitment.
