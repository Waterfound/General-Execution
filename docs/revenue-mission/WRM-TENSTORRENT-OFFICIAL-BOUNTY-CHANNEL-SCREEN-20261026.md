# WRM — Tenstorrent Official Bounty Channel Screen — 2026-10-26

Status: **OFFICIAL_PAID_CHANNEL / FOUR_OPEN_LABELLED_BOUNTIES / FOUR_OCCUPIED_OR_ALREADY_RESOLVED / AUTOMATION_AND_CONTRACT_RISK / NO_BUILD / WATCH_ONLY**

Observed Waterfound revenue: **USD 0**

## Commercial predicate

Does Tenstorrent's official contribution program currently expose one specific, unassigned, machine-admissible bounty that Waterfound can reproduce and solve privately before any public claim, pull request, contract acceptance, payment onboarding or hardware dependency?

Admission requires:

1. an open issue tagged for the official bounty program;
2. no existing assignment, claimant, accepted implementation or separately unpaid residual;
3. explicit acceptance criteria and credible dollar consideration;
4. a testable path using public inputs and available compute;
5. program terms compatible with truthful AI-assisted execution;
6. contractual acceptance, publication and payout onboarding deferred until after a differentiated private proof exists.

## Why this channel was screened

Unlike the noisy public-bounty aggregators, Tenstorrent is a real operating company with an official contribution program, public source repositories and recent paid-contribution evidence.

Official sources:

- https://tenstorrent.com/
- https://docs.tenstorrent.com/bounty_terms.html
- https://github.com/orgs/tenstorrent/projects/17/views/5

Tenstorrent's site explicitly presents the channel as “Fix bugs, add features, get paid.” The current terms were last updated in October 2026 and describe dollar payments by ACH or wire after eligibility and tax/payment requirements.

This is therefore a materially stronger channel than self-issued tokens or recursive bounty boards.

## Canonical terms relevant to admission

The official terms state:

- a bounty may be created by Tenstorrent or proposed by a participant;
- participant-proposed bounties may be assigned directly to the proposer without opening competition;
- work on an issue already assigned to someone else is not eligible and may be declined without review;
- a participant must be assigned on GitHub when submitting the pull request;
- only a merged pull request addressing an eligible open issue can qualify as an Accepted Contribution;
- payment and tax information may be required;
- participation forms a legally binding contract;
- Tenstorrent may unassign work that is low quality or appears AI-generated;
- automated, bot-generated, duplicative or out-of-scope activity receives heightened review;
- participation by automated means may be treated as fraud or abuse.

Sources: Sections 1–5 and 10–11 of https://docs.tenstorrent.com/bounty_terms.html

These clauses do not prove that every AI-assisted contribution is forbidden, but they create a decisive fit risk for an unattended machine-operated mission. Any future participation would require exact written scope compatibility and Waterfound's separate contractual acceptance.

## Current official bounty inventory

A GitHub search of the Tenstorrent organization found four open issues carrying the `bounty` label:

| Issue | Headline reward | Repository state | Commercial disposition |
| --- | ---: | --- | --- |
| [#51655 — uint16 typecast rounding](https://github.com/tenstorrent/tt-metal/issues/51655) | USD 1,000 | Assigned in the maintainer's canonical issue comment to `@kinginu`; multiple alternative PRs and backup claimants already exist | **OCCUPIED / NO PAYABLE RESIDUAL** |
| [#53787 — log_sigmoid accuracy](https://github.com/tenstorrent/tt-metal/issues/53787) | USD 5,000 | Assigned by maintainer to `@kanapitsas`; multiple contributors request reassignment and several publish complete approaches | **ASSIGNED / SATURATED REASSIGNMENT QUEUE** |
| [#56908 — distributed LayerNorm/RMSNorm stride](https://github.com/tenstorrent/tt-metal/issues/56908) | USD 3,000 | Assigned to `@Adraca`; issue comments state the described defect was substantially fixed on `main` by commit `5717c69b` and competing PRs already cover the scope | **ASSIGNED / ROOT DEFECT ALREADY LANDED / NO RESIDUAL** |
| [#59732 — sampling distribution bias](https://github.com/tenstorrent/tt-metal/issues/59732) | USD 3,000 | A named contributor states they are actively working on it; multiple backup contributors already offer complete fixes | **OCCUPIED / CONTESTED** |

The GitHub issue objects exposed an empty assignee field, but maintainer comments establish the operative assignments. The terms make that assignment decisive. Treating an empty metadata field as an unclaimed reward would be misleading.

## Narrowest candidate examined: #51655

The USD 1,000 uint16 typecast issue initially appeared to be the lowest-cost technical proof. It is not admissible:

- the maintainer assigned it to `@kinginu`;
- the assigned contributor has an active implementation, current measurements and a rebased PR;
- several other contributors have posted alternative implementations or asked to become backups;
- the terms explicitly make submissions to assigned issues ineligible;
- hardware-specific correctness and performance are material to acceptance.

A Waterfound patch would duplicate existing work and could not establish a separately payable unit of value.

Decision: **DO NOT CLONE / DO NOT PATCH / DO NOT CLAIM**.

## Hardware and validation boundary

Tenstorrent may provide cloud hardware after assignment, but access must be requested. The available Waterfound hardware is not Tenstorrent hardware. Simulator-only work is insufficient for several current bounties because the acceptance discussions rely on Wormhole/Blackhole measurements, multi-device meshes or architecture-specific kernels.

No new cloud access, account, credential or external installation is authorized here.

## Commercial outcome

The channel is real, funded and technically aligned with machine capability, but the current opportunity set fails before implementation:

- all four labeled issues are assigned, actively worked, already substantially resolved or saturated with backup solvers;
- no unassigned warmup or easy bounty was found;
- the official program requires assignment before eligible work;
- contract, tax and bank onboarding are unavoidable later gates;
- unattended AI execution is not clearly compatible with the current terms and may be disqualified.

No private fixture or repository clone was admitted because it would answer a non-payable predicate.

## Re-entry criteria

Re-enter only when all are true:

1. an official Tenstorrent issue is open and explicitly unassigned in both metadata and maintainer comments;
2. the maintainer confirms Waterfound's assignment before any public PR;
3. the acceptance artifact can be proven locally or through already-authorized free hardware access;
4. no existing claimant has published an equivalent solution;
5. Tenstorrent confirms the intended AI-assisted workflow is eligible under the current terms;
6. Waterfound separately authorizes the binding terms, public contribution and any payment/tax onboarding;
7. expected reward remains positive after hardware, contention and collection risk.

## Evidence accounting

- Credible paid channel: observed.
- Current unassigned payable task: none.
- Private differentiated proof: not admitted.
- Buyer acceptance/WTP for Waterfound: unobserved.
- Revenue: USD 0.
- Claim, issue comment, fork, clone, pull request, public submission, hardware request, contract acceptance, payment onboarding, tax form, bank disclosure or spend: none.
- Mission posture: **WATCH_ONLY / CONTINUE DISCOVERY / NO CURRENT HUMAN GATE**.
