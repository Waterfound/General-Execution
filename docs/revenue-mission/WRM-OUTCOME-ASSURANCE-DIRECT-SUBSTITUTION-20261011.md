# WRM — Outcome-assurance buyer pain and direct substitution test
Observation date: 2026-10-11 (public-source research; no outreach).
Status: EVIDENCE-BOUND MARKET FALSIFICATION / NO BUYER VALIDATION / NO PRODUCT FREEZE.

## Commercial question
Could WRM win with an independent, low-friction service that checks whether an automation actually delivered its intended business outcome rather than merely reporting a successful execution?

## Independent first-hand pain (anecdotal, not validated buyers)
1. 2026-06-09: a self-described client-workflow operator reports that a scheduled weekly client report silently stopped after upstream credential rotation, unnoticed for nine days. Source: https://www.reddit.com/r/n8n/comments/1u163v6/what_is_the_worst_silent_failure_you_have_shipped/
2. 2026-06-22: a different n8n operator describes client work in which a scheduled trigger stopped, an API returned HTTP 200 with an empty body, and a Continue-on-Fail node masked missing output. Source: https://www.reddit.com/r/n8n/comments/1ucepi7/the_n8n_failures_that_scare_me_are_not_the_red/
3. 2026-07-08: a workflow builder says API field changes silently caused missing/garbage records in clients' systems. Source: https://www.reddit.com/r/n8n/comments/1uqo631/ever_had_a_clients_api_silently_change_and_break/
4. 2026-08-05: an operator of HubSpot/Apollo automation reports a green workflow that did not persist expected changes. Source: https://www.reddit.com/r/AiAutomations/comments/1vfw7zq/for_those_running_ai_agents_against_real_business/

Interpretation: at least two distinct public posters self-identify with client automation operation and describe a recurring *failure class*. Identity, customer budget, purchasing authority, representativeness, and willingness to pay are UNKNOWN. Several posts may themselves be product-marketing; these are weak demand signals, not interviews or proof of purchasing intent.

## Direct commercial substitution (first-party product contracts)
- VerifLoop: https://verifloop.com/ — claims independent read-only destination readback (PostgreSQL, Sheets, Slack, HubSpot, HTTP), expected outcome contracts, checkpoint delays, evidence links and agency views; self-serve trial. Its published prices as observed 2026-10-11 are $99/$199/$349 per month by workflow tier: https://verifloop.com/pricing . **These are asking prices, NOT verified receipts, WTP or market size.**
- YieldCue: https://yieldcue.com/ — advertises outcome contracts, missing heartbeat, zero output, volume/correctness checks, evidence-backed incidents, client routing, n8n/Zapier/Make/HubSpot/Airtable integration and no-migration trial. No installed parity test.
- Native n8n: https://docs.n8n.io/workflows/executions/all-executions/ offers success/failed/waiting run states; https://docs.n8n.io/flow-logic/error-handling/ offers error workflows. These do not alone prove business outcome, but users can build postcondition checks using ordinary workflow nodes.
- LangSmith: https://docs.langchain.com/langsmith/evaluation-types provides online production evaluations, including code evaluators and model-based evaluators. Adjacent substitute for semantic output quality, though not identical to independent downstream readback.

## Explicit adversarial verdict
- Generic 'green execution != business result' positioning: **KILL_AS_UNIQUE_DIFFERENTIATOR**. Both VerifLoop and YieldCue already explicitly market this.
- Generic heartbeat / missing run / alert / output-count monitoring: **KILL_AS_UNIQUE_DIFFERENTIATOR**; native and third-party options exist.
- Independent destination readback for n8n agencies: **DIRECTLY SUBSTITUTED** by VerifLoop's published product. No claim of superiority is admissible without a measured comparison.
- Accepted-outcome assurance across coding agents and business workflows: **HYPOTHESIS_ONLY**; it must demonstrate a buyer-specific outcome contract, independently obtainable evidence and a *measurably better* decision under lower friction/cost than named substitutes. Do not silently rebrand a commoditized feature.
- The existence of advertised commercial plans is evidence that competitors offer paid products, not that WRM customers exist.

## Ratchet: commercial decision and next admissible experiment
Do not build a general outcome monitor, PR dashboard, generic agent control plane or another instrumentation layer. Reopen the **vertical workflow automation** and **specialized operational intelligence** market candidates under GE PR #47. Select ONE specific payer/job pair from public first-hand evidence, then compare its actual job-to-be-done against an incumbent and a direct niche substitute. Require a buyer-facing deliverable that can be fulfilled, checked and supported autonomously, with no recurring Waterfound operations. Stop/kill if native or specialist tools solve the same job with negligible friction, if independent lawful data is unavailable, or if a recurring payer pain cannot be evidenced. Only then consider a tiny candidate product proof.

No contacts, customer installs, accounts, payments, credential changes, merges, scheduler changes, paid spending or releases occurred. No revenue, interviews, ROI, WTP, user count or verified product superiority demonstrated.

## UFP evidence attribution
This is a *real* market-research decision artifact persisted on the existing WRM commercial discovery branch. It is not a production execution receipt, not a mission cold-restart rehearsal, not customer validation, and not proof of UFP UNATTENDED_READY.
