# WRM Polar payout-eligibility screen — 2026-10-19

**Decision:** `BRAZIL_NOT_IN_DOCUMENTED_PAYOUT_COUNTRIES / REJECT_BEFORE_TASK_SEARCH / NO_ONBOARDING / NO_REVENUE`

## Commercial predicate

Can Polar provide a lawful, routine and documented payout rail to a Brazilian Waterfound payee for public software work, before any task-specific implementation, publication or financial onboarding?

## Evidence boundary

Only Polar's official public documentation was inspected. No account was created, no Stripe connection or KYC was started, no task was claimed, and no seller or maintainer was contacted.

Primary source:

- <https://polar.sh/docs/merchant-of-record/supported-countries>

## Finding

Polar states that it uses Stripe Connect Express to issue payouts only to residents or businesses in the countries listed on its supported-countries page. The page's complete payout list was inspected on 2026-10-19. Brazil is not listed.

The page separately says Polar can accept customer payments globally except sanctioned countries. That is not equivalent to Brazilian seller payout eligibility. The commercial predicate here is receipt of earned funds by Waterfound in Brazil, so global customer-payment coverage does not cure the missing payout country.

## Decision

The channel fails at payout eligibility before task discovery. Searching, prototyping or competing for Polar-dependent work would create implementation effort behind a known settlement blocker.

State:

`PAYMENT_INTAKE_GLOBAL / SELLER_PAYOUT_COUNTRIES_ENUMERATED / BRAZIL_OMITTED / NO_LAWFUL_ROUTINE_WATERFOUND_PAYOUT_ROUTE_ESTABLISHED`

## Re-entry criteria

Reconsider only if Polar's official documentation adds Brazil, or Polar publishes a binding alternative payout route for a Brazilian individual or entity with fees, verification requirements, tax treatment and settlement timing disclosed before work begins.

## Mission posture

`PASSIVE / CONDITION_WAIT_ON_OFFICIAL_COUNTRY_SUPPORT`

No product, claim, account, KYC, publication, customer demand, WTP or revenue was created. Observed Waterfound revenue remains **USD 0**.
