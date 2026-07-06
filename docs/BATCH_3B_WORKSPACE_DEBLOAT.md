# Batch 3B — Workspace De-bloat and Layout Simplification

This patch corrects the first Batch 3 design direction. The previous input page still looked like a boxed landing page: a large hero, explanatory helper cards, scattered right-column tools, badge-style hints, and controls for language/tone that are not actually user decisions.

## Product decision

The input page should behave like a quiet work surface, not a marketing page or dashboard. Users need to name the itinerary, paste supplier rows, and generate either the agent or customer version. Calculator, Local Library, and saved projects are tools, not helper-card content.

## UI changes

- Removed the large home hero.
- Removed the suggested-flow and alternate-start cards.
- Removed the right-side helper-card column.
- Removed the “Rows can be messy” pill.
- Removed the explanatory action card above generation.
- Replaced the card-heavy composition with a simple toolbar, page heading, itinerary-name field, supplier paste area, and generation buttons.
- Simplified calculator and Local Library headings.
- Changed primary buttons from dark/high-contrast blocks to quiet taupe actions.

## Generation defaults

Language and tone are fixed in normal generation:

- `presentation_language = en`
- `tone_preset = premium_concise`

The Streamlit selector modules for those controls were removed because they are no longer part of the normal user interface.

## Remaining design notes

The visual editor internals and generated PDF theme are intentionally not redesigned in this patch. Those surfaces are more sensitive because preview/PDF parity must be preserved.
