# WRM Solo Stack Continuity Auditor — public-fixture falsification

Date: 2026-10-26

## Decision

**PUBLIC FIXTURE PASS AFTER ONE BOUNDED REFINEMENT / DIFFERENTIATION NARROW / STANDALONE MOAT WEAK / DEMAND AND WTP UNVALIDATED / DO_NOT_EXPAND**

The candidate survived a real public-repository test, but the substitute review narrowed its residual sharply. The defensible job is not general dependency mapping, bus-factor analysis, cloud inventory, secret scanning, or a digital vault. It is:

> From repository metadata alone, locally produce a private continuity-control gap report for a solo operator, without provider credentials or secret values, plus a safe public attestation.

This is a useful feature candidate. It is not yet evidence for a paid standalone product.

## Public fixture

- Repository: `PaddleHQ/paddle-nextjs-starter-kit`
- Immutable fixture head: `da90482f8416f0e54a24991200e168496fce94b7`
- Source: <https://github.com/PaddleHQ/paddle-nextjs-starter-kit/tree/da90482f8416f0e54a24991200e168496fce94b7>
- Access: anonymous read-only clone; no account, token, issue, PR, or external mutation.

### Falsification result before refinement

The first run found the five absent declared controls, but it failed the usefulness predicate:

- false negative: Paddle and Supabase configuration identifiers were present in `.env.local.example` but were not reported;
- false positive: commented AWS examples in `supabase/config.toml` were treated as an active provider signal.

The proof therefore was not counted as a pass.

### Smallest admissible correction

The parser was changed only to:

1. record environment/configuration identifiers while never reading or emitting their values;
2. recognize Paddle and Supabase provider signals; and
3. ignore comment-only lines in machine configuration when detecting providers.

No provider API, account, secret value, browser, database, network agent, or persistent runtime was added.

### Verified result after refinement

- Tests: `2/2 PASS`.
- Providers: GitHub, Paddle, Supabase, Vercel.
- Configuration identifiers: seven names, including Paddle, Supabase, and webhook identifiers; zero values.
- False AWS signal: removed.
- External Actions: six pinned actions identified.
- Recovery gaps: successor/recovery owner, private-repository recovery, restore-test evidence, domain recovery route, and payment-processor recovery.
- Public attestation: `037f7984b7b9bb68ddfb342a3f6ed40b2faa865d58eabff198b877d7bb36d470`.

These are repository-visible observations only. They do not prove that the fixture is a solo business, that the detected services are live, or that recovery would succeed.

## Substitute reconciliation

| Substitute | What it already proves or maps | Residual not shown by its public materials |
|---|---|---|
| GitHub Dependency Graph | Package/action dependencies, manifests, licenses, transitive paths, and vulnerability context | Successor ownership, domain/payment recovery routes, and restore-test evidence |
| Bus Factor Explorer | Knowledge concentration and files/subsystems at turnover risk from commit history | Operational provider inventory or recovery-control coverage; the repository describes itself as a finished research prototype with no further support |
| InfraMole | Read-only infrastructure discovery, dependency mapping, impact analysis, no secret collection, free open-source self-hosting | Credential-free repository-only mapping to successor/recovery controls |
| Fix Inventory | Agentless cloud metadata collection and dependency/access graphs across major providers | It requires cloud-account access and targets security/compliance rather than succession readiness |
| Riffle Resilience | Operational dependencies, single points of failure, linked recovery plans, and integrations | Public positioning targets organizations with operational systems and demo-led onboarding, not a zero-account local solo-founder audit |
| AmberKey | Digital-legacy planning, encrypted vault, GitHub recovery playbook, printed recovery kit | Automatic discovery from repository metadata is not documented |

Primary sources:

- GitHub Dependency Graph: <https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/explore-dependencies>
- Bus Factor Explorer: <https://github.com/JetBrains-Research/bus-factor-explorer>
- InfraMole: <https://inframole.com/>
- Fix Inventory: <https://github.com/someengineering/fixinventory>
- Riffle Resilience: <https://www.riffleresilience.com/>
- AmberKey GitHub playbook: <https://amberkey.app/docs/playbooks/github/>

## Commercial interpretation

The substitutes cover almost every component separately and several cover broader enterprise versions. The residual advantage is low-friction composition: local, no credentials, continuity-specific, and attestable. That may reduce setup cost for a solo founder, but public evidence does not establish that this convenience is painful enough to buy.

Consequently:

- do not add dashboards, agents, provider integrations, vaults, hosted accounts, or automated reminders;
- do not claim recoverability, ROI, time savings, demand, or WTP;
- keep the proof as a bounded secondary candidate, not the ACTIVE revenue thesis;
- the next commercial predicate is natural buyer/problem evidence that founders already perform or purchase this exact reconciliation;
- if no such evidence appears, close the standalone wedge and retain the auditor only as a possible free diagnostic/feature inside a more valuable continuity offer.

## Kill criteria

Close the standalone candidate if any of the following remains true after the next buyer-evidence screen:

1. no repeated public evidence of founders paying for repository-to-recovery reconciliation;
2. adjacent continuity tools add automatic repository discovery with equivalent privacy and setup cost;
3. useful accuracy requires provider credentials or a manually maintained inventory before value appears;
4. false positives/negatives cannot be bounded using repository-visible evidence; or
5. acquisition requires routine founder education or Waterfound-operated consulting.

## Mission state

- Capability: public-fixture predicate PASS after one correction.
- Observed customer outcome: none.
- Differentiation: narrow and provisional.
- Demand evidence: none for the exact job.
- WTP evidence: none.
- Revenue: USD 0.
- Status: `SECONDARY / DO_NOT_EXPAND / BUYER-EVIDENCE_NEXT`.
- Privacy P0 producer binding: untouched and inactive.
