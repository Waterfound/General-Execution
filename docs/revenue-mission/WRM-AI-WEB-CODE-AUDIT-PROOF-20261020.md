# WRM AI-Generated Web Code Audit — Buyer-Fit Proof — 2026-10-20

## Decision

**State:** `NARROW_PROOF_PASSED / BOUNDED_BUYER_AND_WTP_OBSERVED / APPLICATION_AUTHORITY_GATE / NO_PROPOSAL_SENT`

A current public buyer asks for a small research-oriented audit of AI-generated website code: generate or select a sample, identify 3–5 demonstrable issues in performance, security, accessibility, maintainability, or production readiness, link each issue to exact code, explain it in plain English, and recommend practical fixes. The listing is worldwide, intermediate level, less than 30 hours/week, less than one month, and displays USD 15–25/hour.

The smallest read-only proof below uses an existing public Lovable-generated educational site at an immutable commit. It finds five concrete issues without private access, fabricated customer data, artificial inefficiency, or changes to the source repository. The proof answers the named capability predicate. Further fixture instrumentation is `SUPPORT_ONLY`.

No proposal, customer contact, external publication outside the existing candidate branch, account action, Connects purchase, identity/KYC, contract, private access, or payment onboarding occurred.

## Buyer evidence

**Listing:** Web Developer for AI Code Audit  
**URL:** https://www.upwork.com/freelance-jobs/apply/Web-Developer-for-Code-Audit_~022102608080165544228/

Observed public terms:

- worldwide, remote;
- one-time project;
- intermediate experience level;
- less than 30 hours/week;
- less than one month;
- USD 15–25/hour;
- buyer asks for 3–5 strong, demonstrable findings with exact code, plain-English impact, and practical fixes;
- client profile shows approximately USD 1,900 spent, 17 hires, one active contract, and 76 hours.

Freshness is not fully reliable: current search indexes label the post “yesterday,” while the underlying crawl metadata is several weeks old. The page remains indexed and exposes activity scaffolding, but current proposal count, interview activity, payment verification, and open/closed status were not independently visible. Treat it as direct buyer/WTP evidence and a conditional application candidate, not guaranteed inventory.

## Public fixture and provenance

**Repository:** https://github.com/temikeezy/african-countries-explorer  
**Immutable commit:** `43123d6840316ec946b43ed0b6ee6894cc7c3c4e`

The repository README states that the project is connected to a Lovable project and that Lovable changes are committed automatically. It is an educational React/Vite/TypeScript site using REST Countries and Advice Slip APIs.

Pinned evidence:

- README / Lovable provenance: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/README.md
- Main data flow: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/src/pages/Index.tsx
- Country interaction: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/src/components/CountryCard.tsx
- Search control: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/src/components/SearchBar.tsx
- Advice control: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/src/components/AdviceCard.tsx
- TypeScript configuration: https://github.com/temikeezy/african-countries-explorer/blob/43123d6840316ec946b43ed0b6ee6894cc7c3c4e/tsconfig.app.json

## Five demonstrable findings

### 1. Country cards are pointer-only interactive controls

**Class:** Accessibility / functional reachability  
**Severity:** Medium  
**Evidence:** `CountryCard.tsx` renders a card container with `onClick={onClick}` and pointer styling, but no native `button`, keyboard handler, `tabIndex`, or control semantics.

**Why it matters:** Keyboard-only and switch-device users cannot reliably focus or activate country details. The UI appears interactive visually while withholding the same function from non-pointer input.

**Practical fix:** Render the interactive surface as a native `button` or place a full-size button inside the card. Preserve a visible focus indicator and accessible name. Test Tab, Enter, and Space activation.

**Verification:** Automated axe check plus a keyboard-only path from page load to opening and closing a country dialog.

### 2. Search and refresh controls lack durable accessible names

**Class:** Accessibility  
**Severity:** Medium  
**Evidence:**

- `SearchBar.tsx` relies on placeholder text and provides no associated `label` or `aria-label`.
- `AdviceCard.tsx` renders an icon-only refresh button without text, `aria-label`, or tooltip exposed as an accessible name.

**Why it matters:** Placeholder text is not a persistent label and can disappear once the user types. Screen-reader users may encounter an unnamed edit field and an unnamed button, making the interface ambiguous.

**Practical fix:** Add a visible or visually hidden `label` tied to the input ID; add `aria-label="Refresh advice"` to the button; mark decorative icons `aria-hidden="true"`.

**Verification:** Inspect the accessibility tree and require non-empty accessible names for both controls.

### 3. External API data is trusted without runtime validation

**Class:** Production readiness / reliability  
**Severity:** Medium  
**Evidence:** `Index.tsx` calls `response.json()` and immediately stores the result as countries. The TypeScript `Country` interface exists only at compile time; the country response is not parsed against a runtime schema. Rendering later dereferences `country.name.common`, `country.flags.svg`, and `country.maps.googleMaps`.

**Why it matters:** A successful HTTP response with a changed, partial, rate-limit, or malformed JSON shape can pass the `response.ok` test and then crash or misrender the application. Static types do not validate network payloads.

**Practical fix:** Parse both API responses through a narrow runtime schema (for example Zod), reject invalid records with a typed error, and surface a recoverable error state. Request only the fields actually rendered.

**Verification:** Mock a 200 response missing `name` or `flags.svg`; the page must show a controlled error rather than throw during render.

### 4. The primary data failure path has no recoverable UI

**Class:** Production readiness / user recovery  
**Severity:** Medium  
**Evidence:** On a country-fetch error, `Index.tsx` shows a transient toast and exits loading. The normal content path then renders “Showing 0 of 0 countries.” Unlike the advice card, there is no persistent error state or retry control for the primary dataset.

**Why it matters:** A transient network or provider failure leaves the core product looking legitimately empty. After the toast disappears, the user cannot distinguish “Africa has zero results” from a failed load or recover without reloading the whole page.

**Practical fix:** Model `idle/loading/success/error` explicitly. Keep a persistent error panel with a retry button and do not reuse the valid-empty state for transport failure.

**Verification:** Force the first request to fail and the second to succeed; the user must recover through an in-page retry without a browser reload.

### 5. Network requests have no timeout/cancellation, while query infrastructure is shipped but bypassed

**Class:** Performance / reliability / maintainability  
**Severity:** Medium–Low  
**Evidence:**

- `Index.tsx` uses bare `fetch` calls without `AbortController`, timeout, or unmount cleanup.
- `App.tsx` creates and provides a TanStack Query client, and `package.json` ships `@tanstack/react-query`, but the main API flows manually implement loading, errors, retries, and state.

**Why it matters:** A stalled upstream can keep the loading state indefinitely. Re-entering/unmounting does not cancel in-flight work. The project pays the dependency and architectural cost of a query layer while duplicating a less complete request lifecycle.

**Practical fix:** Use TanStack Query for both endpoints with bounded retry, stale time, cancellation signal, and explicit error UI—or remove the unused provider/dependency and implement an equivalent abortable request helper. Add a finite timeout appropriate to the public APIs.

**Verification:** Simulate a never-resolving request, navigate away, and confirm cancellation plus a bounded user-visible timeout. Confirm a second mount uses the intended cache policy.

## Proof result against buyer acceptance language

| Buyer predicate | Proof result |
|---|---|
| AI-generated provenance | **Pass** — repository pins a Lovable project and automatic Lovable commits |
| 3–5 real findings | **Pass** — five code-linked findings |
| Performance | **Pass** — stalled requests and bypassed query/caching lifecycle |
| Security | **Not claimed** — no strong security issue is asserted from the inspected surface |
| Accessibility | **Pass** — pointer-only cards and unnamed controls |
| Maintainability | **Pass** — duplicated request lifecycle and compile-time-only trust boundary |
| Production readiness | **Pass** — invalid-payload crash path and unrecoverable primary-data failure |
| Plain-English explanation | **Pass** |
| Practical fixes and verification | **Pass** |
| Private access required | **No** |

The proof deliberately does not inflate low-confidence observations into vulnerabilities. A credible audit may return no security finding when the inspected public surface does not support one.

## Commercial interpretation

This evidence materially sharpens the service candidate:

> **AI-generated web code evidence audit:** for one small public or access-controlled repository at an immutable commit, identify up to five demonstrable production risks, link each to exact code, explain the operational impact, and provide fixes plus verification tests.

This is narrower than the previously gated senior-architect assessment and does not inherently require eight years of professional tenure. The observed buyer rate is USD 15–25/hour, but sustainable pricing, delivery time, acceptance rate, customer demand for Waterfound, and ROI remain unmeasured.

## Kill criteria and result

| Criterion | Result |
|---|---|
| At least three defensible issues on a natural AI-generated fixture | **Pass** — five |
| Every finding pinned to exact public code | **Pass** |
| No private credentials/data needed for proof | **Pass** |
| Findings cover more than generic lint/style | **Pass** — accessibility and failure semantics |
| Buyer names this exact deliverable | **Pass** |
| Public WTP visible | **Pass** — USD 15–25/hour |
| Opportunity confirmed currently open with payment protection | **Unknown** |
| Authorized contracting identity/account exists | **Unknown / gate** |

## Exact next gate

Before any application:

1. verify the listing remains open and the client payment method/milestone protection is current;
2. authorize one Upwork proposal, any required Connects, identity/KYC/tax/payment onboarding, and external communication;
3. designate the truthful provider identity and availability;
4. permit linking or summarizing this public proof as a work sample;
5. require a funded milestone or hourly protection before any buyer-specific work.

Until those actions are authorized, keep the opportunity `APPLICATION_AUTHORITY_GATE` and revenue `USD 0`.

## Evidence discipline

### Established

- A buyer publicly requested exactly this narrow audit result.
- A natural public AI-generated fixture yielded five defensible findings.
- The proof required no private access and no source changes.
- A public rate envelope of USD 15–25/hour exists for this listing.

### Unknown — do not claim

- Current open status, payment verification, proposal/interview counts, buyer selection, or contract.
- Time-to-deliver under real buyer constraints.
- Customer acceptance, hours saved, defects avoided, monetary risk reduction, or ROI.
- Waterfound-specific willingness to try or pay.
- Any revenue or sustainable market price.

## Portfolio consequence

- Promote **AI-generated web code evidence audit** to the leading narrow service candidate.
- Keep the broader senior-architect audit gated and secondary to this lower-friction unit.
- Stop additional synthetic-fixture work unless it answers buyer acceptance, delivery time, or repeatability with measured evidence.
- Preserve `NO_PRODUCT_SELECTED` until external demand is authorized and observed; revenue remains `USD 0`.
