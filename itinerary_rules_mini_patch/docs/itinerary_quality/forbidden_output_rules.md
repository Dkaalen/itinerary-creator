# Forbidden Output Rules

These strings/patterns should be treated as regression failures unless deliberately allowed for a specific documented reason.

## Commercial correctness

Never show optional add-ons as normal included activities.

Forbidden patterns:

- `Optional Addon` under `Activities & experiences`
- `Optional experience` under normal inclusions
- `Not included` under `Included With This Experience`
- `included excluded`
- `Food and drinks are included excluded`

## Transport and inclusions

Forbidden patterns:

- `Self-guided transfer`
- `Self transfer` under `What’s included`
- `Train:` under `Activities & experiences` when it is a city-to-city rail transfer
- `Train to Malmö` when the day destination/final rail destination is Stockholm
- `Private transfer to your accommodation` on a departure day
- `Spend time at leisure onboard the cruise` under commercial cruise inclusions
- Orphan inclusion bullets on a new page with no category heading

## Fallback text leaks

Forbidden unless present in the source context:

- `Ranua Wildlife Park`
- `Stokmarknes`
- `Northern Lights hunt by reindeer`

## Repetition and weak content

Forbidden or discouraged:

- repeated `Guided sightseeing` in Journey Arc
- `Journey` as a chapter label when a real city/cruise context is available
- `Onward travel and accommodation` as the main Journey Arc phrase when a more specific phrase can be inferred

## Typos and bad normalization

Forbidden patterns:

- `Bluelagoon`
- `Skylagoon`
- `Gothernburg`
- `Trosmø`
- `SVolaver`
- `accommodaiton`
- `Brekafast`
- `inlcuded`
- `Includse`
- `Full Pention`
- `Overngiht Cruise`
- `central of Reykjavík`
- `central of Alta`

## Duplicates

Forbidden patterns:

- `National Park National Park`
- rental car pick-up repeated twice on the same day
- hotel breakfasts repeated in both Accommodation and a breakfast-only Meals section

