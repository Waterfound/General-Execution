# Canonical Constitution Gate

## Canonical source

General Execution is bound to the Waterfound system Canonical Constitution at:

- repository: `Waterfound/Systems`
- revision: `913fc1e6b7fd20eac789b60abd684f168bd8a29d`
- artifact: `constitution/canonical-constitution.v1.json`
- identity: `catechism-catholic-church-john-paul-ii`

That artifact adopts the **Catechism of the Catholic Church promulgated by Saint John Paul II** as the Canonical Constitution of the Waterfound system family for matters of faith and morals.

General Execution does not interpret or replace the Magisterium. It enforces the admission consequence of an evidence-bound constitutional assessment.

## Constitutional hierarchy

```text
Canonical Constitution
  -> Waterfound human authority
    -> execution authority envelope
      -> machine execution
```

The constitutional gate runs before ordinary execution-launch admission.

A normal Waterfound authority grant cannot override an `INCOMPATIBLE` disposition.

## Exact-order binding

A constitutional assessment binds:

- workstream identity;
- the exact `ExecutionLaunchOrder.digest`;
- the exact canonical Systems revision;
- disposition;
- evidence/basis references;
- assessor identity and assessment reference.

If the execution order changes, its digest changes and the prior constitutional assessment cannot be reused.

## Dispositions

| Assessment | Gate result | Effect |
| --- | --- | --- |
| `OUT_OF_SCOPE` | `ADMITTED` | Ordinary technical work may proceed to authority admission |
| `COMPATIBLE` | `ADMITTED` | Constitutionally relevant work may proceed to authority admission |
| `INTERPRETATION_REQUIRED` | `INTERPRETATION_GATE` | No launch; resolve authoritative ecclesial/factual uncertainty |
| `INCOMPATIBLE` | `REJECTED` | No launch; ordinary authority cannot override |

A materially relevant disposition other than `OUT_OF_SCOPE` requires non-empty `basis_refs`.

## Separation of responsibilities

The constitutional gate:

- does not create authority;
- does not execute anything;
- does not grant provider access;
- does not authorize spending, merge, release, consensus/economics or mainnet;
- does not determine theology by string matching.

The assessment producer is responsible for substantive reasoning and evidence. For Catholic teaching, it should cite Catechism paragraphs or official Holy See sources. Genuine doctrinal or factual uncertainty is represented explicitly rather than converted into synthetic certainty.

## Canonical launch path

The governed path is:

```text
ExecutionLaunchOrder
  + ConstitutionalAssessment bound to exact order digest
  -> constitutional admission
     OUT_OF_SCOPE / COMPATIBLE -> ELG-01 authority/executor admission
     INTERPRETATION_REQUIRED   -> stop
     INCOMPATIBLE              -> reject
```

`admit_execution_launch_order` remains the lower-level ELG-01 primitive. System-level Full Autonomy must use the constitutionally governed composition when a consequential autonomous action is being admitted.
