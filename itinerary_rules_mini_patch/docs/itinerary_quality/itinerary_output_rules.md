# Itinerary Output Rules

## Core principle

The itinerary generator should use reusable logic that works across similar inputs. Avoid one-off fixes for a single itinerary, exact row, or exact customer input unless there is no reasonable general rule.

The output should feel client-ready: polished, clear, commercially accurate, and visually premium.

## Cover title rules

Use the detected countries and season to build the cover title.

- One country only: `[Country] [Season] Journey`
  - Example: `Iceland Summer Journey`
  - Example: `Norway Summer Journey`
- Two or more Scandinavian countries only: `Scandinavian [Season] Journey`
  - Denmark + Sweden + Norway should be Scandinavian.
- Two or more Nordic countries, but not only Scandinavian: `Nordic [Season] Journey`
  - Finland + Norway should be Nordic.
- Unknown or mixed outside Nordic: use a neutral title such as `Curated [Season] Journey`.

Cover title layout should avoid awkward line breaks where possible. Short three-word titles such as `Norway Summer Journey` should be sized to fit cleanly on one line when feasible.

## Subtitle rules

Single-country itineraries should use country-aware subtitles when possible.

Examples:

- `A premium Iceland summer self-drive journey with scenic routes and curated experiences`
- `A premium Norway summer journey with scenic travel and curated experiences`

Self-drive itineraries should explicitly mention self-drive.

## Journey Arc rules

The Journey Arc should summarize the story of the trip, not repeat generic filler.

Hard rules:

- Keep each “What You’ll Experience” phrase compact enough to fit one row where possible.
- Use a maximum of one or two strong themes per chapter.
- Avoid repeated generic phrases such as `Guided sightseeing`.
- Avoid themes that do not fit the destination or source content.
  - Do not use `Arctic` for Bergen unless the source explicitly justifies it.
  - Do not use `fjord scenery and coastal cruising` for every cruise-adjacent chapter when more precise themes are available.
- Cruise-only chapters may be summarized as `Coastal voyage towards [destination]` or similar.

Good examples:

- `Helsinki — Guided city discovery`
- `Rovaniemi — Aurora, Santa Village and Arctic experiences`
- `Tromsø — Sámi culture, fjords and northern lights`
- `Bergen — City, funicular and coastal cruise`
- `Cruise — Coastal voyage towards Bergen`
- `Oslo — Norway in a Nutshell and scenic rail`

## Day page rules

Day titles should be short and client-facing.

- Transport day title: `Train to Bergen`, `Flight to Kirkenes`, `Coach Transfer to Alta`, `Cruise to Bergen`, `Departure from Oslo`.
- Travel Arrangement bullets may be more descriptive than the title.
- A transport-only day should not be described as a “planned highlight” or “experience” unless the transport is clearly a scenic experience product.
- Departure-day transfers should not say `to your accommodation`; infer `to the airport/station/port` when the day is clearly a departure day.
- Day rows with only leisure/cruise leisure should not repeat the same line as both title and bullet unnecessarily.

## Leisure rules

Leisure blocks should be short and not overly repetitive across long itineraries.

Preferred short wording:

`Enjoy the rest of the day at your own pace.`

Long generic paragraphs should not be repeated on many pages in the same itinerary.

## Cruise day rules

Cruise leisure days should read like itinerary days, not commercial inclusions.

Preferred title:

`Spend time at leisure onboard the cruise`

Preferred body:

`Enjoy a relaxed day at sea with time to take in the coastal scenery, onboard facilities and the rhythm of the voyage.`

Cruise leisure days must not appear in `What’s included` as standalone ferry/cruise inclusions.

Cruise start day intro should point to the cruise destination, not the current port.

Bad:

`The journey continues towards Kirkenes` on a Kirkenes-to-Bergen cruise start day.

Good:

`Your coastal cruise begins in Kirkenes, with time onboard as the journey continues towards Bergen.`

Cruise arrival rows should preserve arrival time when provided.

Example:

`Cruise arrival to Bergen — 2:45 PM`

## Activity rules

Activities should be classified by type:

- guided tour
- admission/ticket
- spa/wellness
- scenic route product
- transfer/transport
- optional add-on
- cruise/leisure

Admission-style products should not be called guided unless the source says guided.

Optional add-ons must be separated from included activities and must never appear as normal included activities.

## Inclusion rules

Inclusions should be client-facing and commercially accurate.

- Breakfast attached to hotels belongs under Accommodation.
- Do not create a separate `Meals included` section when it only repeats hotel breakfasts.
- Keep non-hotel meals under `Meals included` when meaningful: lunch, dinner, food tastings, fish soup, full board/full pension, cruise meal plan.
- Items marked `not included`, `excluded`, `to be bought on site`, or similar must not appear under `Included With This Experience`.
- Optional add-ons must not appear in normal inclusions unless specifically selected/included.
- Self transfers must never appear in the inclusions list.
- Arrival times are information, not commercial inclusions. Do not list plain arrival times under `Other arranged transport`.

## Inclusions pagination rules

Inclusion categories should not be split awkwardly.

Preferred rule:

- If a category cannot fit on the current page, move the whole category to the next page.

Fallback rule if a category must continue:

- Repeat the category heading with `continued`, e.g. `Ferries & cruises continued`.

Never leave orphan bullets on a new page without the relevant category heading.

## Exclusions rules

Exclusions should include clear commercial protections.

Default exclusions:

- International flights unless specifically listed
- Meals unless specifically stated
- Drinks unless specifically stated
- Porterage unless specified
- Self transfers and self-arranged travel costs unless specifically stated
- Travel insurance
- Optional upgrades and personal expenses
- City taxes or local fees, where applicable

Add when relevant:

- `Self-arranged flights or transport listed in the itinerary, unless specifically stated as included`
- `Optional add-ons and experiences unless specifically selected`
- `Tickets or services marked as excluded or to be bought on site`

## Preview/PDF parity rules

The preview, visual editor, and PDF output should use the same content and visual logic.

If a design element changes in the PDF, it should also change in preview/editor unless explicitly impossible.

## Day-image divider rules

The divider between day content and image should be:

- one solid accent color
- visually premium and slightly thicker than the early thin version
- attached to the image/content boundary
- line and emblem aligned by their center points
- emblem slightly larger than the early version
- transparent background behind the emblem; no cream/white patch

