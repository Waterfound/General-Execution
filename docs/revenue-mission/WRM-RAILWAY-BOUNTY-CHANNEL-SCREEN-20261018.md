# WRM Railway bounty channel screen — 2026-10-18

**Decision:** `PAYMENT_RAIL_CONFIRMED / CURRENT_ITEMS_PROVIDER_BOUND_OR_IMMATERIAL / NO_PRIVATE_PROOF_ADMITTED / NO_PRODUCT_SELECTED`

## Commercial predicate

Can Railway Central Station bounties provide a lawful, presently machine-admissible path from public technical evidence to first revenue without requiring private access, speculative product work, or an external commitment before a claimable answer exists?

## Evidence boundary

This is a read-only screen of public sources. No Railway account was created or used; no question was answered; no bounty was claimed; no payout account, Stripe Connect, or KYC flow was started. No private project, customer, or Waterfound runtime evidence was admitted.

Sources checked on 2026-10-18:

- Railway's official bounty documentation: <https://docs.railway.com/community/bounties>
- Railway Central Station's public bounty board: <https://station.railway.com/bounties>
- Primary question: <https://station.railway.com/questions/southeast-asia-egress-ips-152-55-188-0-5c5acecd>
- Primary question: <https://station.railway.com/questions/deployment-fails-immediately-after-succe-348f484b>
- Discovery lead only (not treated as authoritative): <https://github.com/HCTDIP/corps-jobs/blob/main/reports/railway_bounty_latest.json>, generated 2026-10-18T16:08:47Z.

## Payment-rail facts

Railway documents a real community bounty program:

- an answer must be accepted by the asker and then reviewed by Railway;
- a qualifying answer must genuinely solve the problem, and the responder cannot be the asker;
- the standard bounty is US$10, with some questions paying more;
- Railway funds the bounty;
- earnings enter the responder's Railway workspace and may be used as Railway credits or withdrawn through Stripe Connect;
- AI assistance is permitted only when disclosed and when the responder has fully reviewed and verified the answer; low-effort or unreviewed AI output may result in a ban.

These facts establish a payment mechanism, not a currently claimable opportunity, expected revenue, or willingness to pay for WRM-T1.

## Current-item falsification

### Southeast Asia egress geolocation — US$10, zero replies at screen time

The public evidence already isolates a Railway-owned condition: IPs in `152.55.188.0/22` used by `asia-southeast1-eqsg3a` geolocate to San Francisco in public databases, while the reporter's EU West workaround returns expected exchange responses. The requested durable remedies are publication/correction of Railway's RFC 8805 geofeed, notifications to GeoIP providers, and clarification of Railway static-egress allocation.

A community responder cannot authoritatively change Railway's geofeed, IP allocation, or provider escalation state. A public answer could restate the diagnosis or workaround but could not verify completion of the requested remedy. Therefore the item is not admitted as claimable despite low visible competition.

### Deployment fails after successful export — US$10, two replies at screen time

The thread already contains a Railway-team statement that the failure occurred inside the build after export, before runtime or provisioning, and that the specific cause cannot be determined from the available logs. The reporter asks for an account-level investigation of the builder/registry path.

The missing evidence is internal to Railway. A community answer cannot verify an account-scoped builder or registry incident from the public record. Therefore the item is not admitted as claimable.

### Older higher-value items

The discovery report lists older US$20 questions involving Anycast routing, compliance ingress metadata, storage I/O, regional latency, DNS, and point-in-time recovery. They are months old, already have replies, and are predominantly provider-infrastructure or account-state cases. They do not provide a sharper machine-admissible opportunity than the two current items and were not promoted to candidate status.

## Unit-economics gate

Even if a correct public explanation were possible, the standard US$10 reward must cover:

1. source verification and reproduction;
2. account creation or login;
3. public answer publication and AI-use disclosure;
4. acceptance uncertainty;
5. Railway review;
6. conversion from workspace earnings to cash through Stripe Connect and any associated identity/tax requirements.

No expected-value claim is made because acceptance probability, review latency, payout friction, and Waterfound's marginal account/KYC cost are unmeasured. At US$10, those unknowns are material. External account creation, public answering, and payment onboarding remain unjustified until a technically resolvable, sufficiently valuable item survives the read-only screen.

## Commercial conclusion

This channel is real but the current frontier is not a present human gate: there is no sufficiently valuable, publicly solvable bounty for which a bounded account or publication action would unlock a verified answer. The right action is to keep the channel secondary and continue machine-admissible discovery for a higher-value, externally testable job.

The screen does not validate customer demand, WRM-T1 differentiation, willingness to try, willingness to pay, operator-hours saved, avoided rework, or monetary ROI.

## Re-entry and kill criteria

Promote a Railway bounty only when all are true:

- the question is open and funded in the primary source;
- the answer can be verified from public or synthetic evidence without provider-internal access;
- the proposed answer materially resolves the ask rather than merely escalating it;
- visible competition does not already contain an equivalent solution;
- expected reward is proportionate to verification, publication, acceptance, and payout friction;
- required account/publication/payment steps are presented as an exact bounded Waterfound gate before execution.

Kill or close a candidate when any of these holds:

- remedy requires Railway staff, private account telemetry, or provider-side mutation;
- public evidence cannot distinguish the proposed diagnosis;
- an equivalent answer is already present;
- reward is immaterial after conservative completion and payout costs;
- proof would require unapproved private data, new paid spend, deceptive framing, or unverifiable claims.
