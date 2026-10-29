# WRM — Family Recipe Box to Cookbook Screen — 2026-10-26

Status: **PAID_AND_DELIGHTFUL_CATEGORY / CURRENT_BUYER_PAIN / EXACT_SELF_SERVICE_SUBSTITUTES / SAFETY_REVIEW_REQUIRED / NO_BUILD / CLOSED**

Observed Waterfound revenue: **USD 0**

## Narrow job tested

**Buyer:** a family member holding handwritten recipe cards, clippings, photographs and oral cooking notes.

**Desired outcome:** upload or photograph the collection once and receive a readable, searchable, print-ready family cookbook that preserves the original handwriting and provenance while minimizing transcription and layout work.

This is a desired heirloom outcome with digital delivery and low marginal fulfillment. The commercial test was whether Waterfound could remove a still-manual step, not whether OCR or PDF generation is technically possible.

## Current problem evidence

Recent public discussions still show the job:

- families struggling to choose a service after compiling recipes in a document;
- people seeking a service that turns inherited handwritten material into a physical cookbook;
- users wanting both the original card image and a readable transcription;
- substantial manual time reported for scanning, naming, transcribing and arranging old cards.

Sources:

- https://www.reddit.com/r/Cooking/comments/1umpfht/trying_to_create_a_family_cookbook_anyone_have/
- https://www.reddit.com/r/CookbookLovers/comments/1sqqc9n/digitizing_old_recipes/
- https://www.reddit.com/r/Old_Recipes/comments/1j58dah/how_to_preserve_family_recipes/
- https://www.reddit.com/r/Old_Recipes/comments/1w432bt/do_you_prefer_pictures_or_scans_of_recipes/

These are problem signals, not evidence that a buyer would choose or pay Waterfound.

## Exact substitution

The complete proposed flow is already directly served:

| Proposed attribute | Current substitute evidence |
| --- | --- |
| Photograph handwritten or cursive cards | RecipePrinter, Tasteful Memories, Handed To Us, Recipe Restore and others advertise card scanning/OCR |
| Editable structured ingredients and steps | RecipePrinter and Handed To Us convert images into organized editable recipes |
| Preserve original card beside readable text | Recipe Restore explicitly offers dual-format pages; several builders retain card images |
| Automatic book layout and print-ready PDF | RecipePrinter, Tasteful Memories, Culinary Lineage, Recipe Restore and ReciScan |
| Family contribution without individual accounts | Handed To Us accepts private-link contributions without contributor accounts |
| Searchable private family collection | Handed To Us and adjacent recipe-box products |
| Voice, story and provenance around recipes | Tasteful Memories and Culinary Lineage |
| One-time, no-subscription price | RecipePrinter: USD 19.99 per cookbook; Recipe Restore: USD 79 for up to 50 recipes; Culinary Lineage: observed one-off tiers |
| Free preview / low-risk entry | RecipePrinter previews up to 10 recipes free; Handed To Us offers one recipe free |
| Physical cookbook | Tasteful Memories, ReciScan and boutique providers include or arrange printed output |

Representative sources:

- https://www.recipeprinter.com/handwritten-recipes-to-cookbook
- https://welcome.thetastefulmemories.com/pricing
- https://handedtous.com/
- https://reciperestore.com/recipe-digitizing-service
- https://culinarylineage.com/en/pricing
- https://reciscan.app/family-cookbook
- https://www.butterandink.com/

The price range also spans inexpensive self-service, mid-priced digitization and premium family collections. A generic implementation would enter an already segmented market rather than expose an overlooked job.

## Safety and fidelity boundary

Recipe transcription is not ordinary prose OCR. Misreading “1/4 tsp” as “14 tsp”, changing an allergen, omitting a cooking temperature, or inventing an unclear step can make the result unusable or unsafe.

A lawful product would therefore need to:

- preserve the source image;
- visibly mark uncertain fields;
- require a human to verify quantities, allergens, temperatures and preservation/canning instructions;
- never “repair” an ambiguous recipe by guessing;
- distinguish transcription from modernization or culinary advice.

That verification is appropriate for the family as a bounded approval, but it is not a competitive advantage: current services already expose editable text and source images, and some explicitly market review/correction.

## Decision

Close before build.

Do not create another:

- handwritten recipe OCR tool;
- recipe normalizer;
- family cookbook PDF generator;
- no-account contribution link;
- searchable private recipe box;
- voice-to-recipe or story-to-recipe wrapper;
- mock store, checkout or print integration.

The exact outcome is available from current substitutes at prices low enough that a Waterfound proof would answer only technical capability, not commercial differentiation.

## Re-entry criteria

Re-enter only if all are true:

1. a specific cohort has a documented failure that survives the existing scan/OCR/edit/layout/print offerings;
2. at least three independent buyer observations show a repeated willingness to pay for the missing outcome;
3. the differentiation is measurable in error rate, active family minutes, completion rate, provenance coverage or print acceptance;
4. a synthetic fixture can test the outcome without copyrighted third-party recipes or sensitive family data;
5. unsafe ambiguity fails closed and remains human-verifiable;
6. acquisition can be lawful, repeatable and materially unattended under existing permissions.

## Kill criteria

Reject immediately if differentiation is only:

- AI/OCR;
- cursive recognition;
- preservation of original images;
- structured ingredients and steps;
- editable pages;
- print-ready PDF;
- one-time pricing;
- privacy/no account;
- family collaboration;
- voice stories or QR codes;
- physical printing.

Reject if the system silently guesses measurements, allergens, temperatures, canning guidance or food-safety facts.

## Evidence accounting

- Buyer/problem: observed.
- Paid/delight category: observed from commercial offers; independent WTP for Waterfound unknown.
- Exact product substitution: strong.
- Technical capability: not tested because it is not the missing predicate.
- Differentiated outcome: none identified.
- Waterfound WTT/WTP/revenue: none / none / USD 0.
- Mission posture: continue commercial discovery; no human gate.

No build, upload, collection of family data, outreach, publication, pricing commitment, account creation, print order, spend, contract, payment/KYC, runtime activation, privacy-producer activation, merge or canonical-state mutation occurred.
