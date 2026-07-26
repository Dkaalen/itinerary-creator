# Group Tour Domain Contract — IH2

## Purpose

A multi-day group tour is one commercial product with multiple itinerary-day
segments. It is not a set of independently purchased activities and it is not
generic coach transport.

Patch IH2 introduces a renderer-neutral canonical contract in:

```text
itinerary_generation/group_tour_domain.py
```

The reference corpus remains test data only. Runtime domain code does not import
or depend on the corpus.

## Ownership

`GroupTourPackage` owns:

- Package identity and stable package ID
- Source title and client-facing package title
- Summer/winter season
- Declared and observed package duration
- Package-day to itinerary-day mapping
- Meeting point and pickup time
- Package-wide description and inclusions
- Accommodation, transport, and guide policies
- Commercial status
- Source URL and source-row identity
- Optional/commercial rows
- Package diagnostics

`GroupTourDay` owns:

- Package-day number
- Itinerary-day number
- Supplier day title and description
- Source-derived route regions
- Day-specific highlights and included activities
- Meals explicitly present in source
- Overnight area and accommodation wording
- Optional and conditional facts
- Source identity and diagnostics

`GroupTourCommercialItem` keeps these outside the included package contract:

- Transfer packages
- Activity upgrades
- Single supplements
- Extra hotel nights

## Invariants

```text
One group-tour master row
↓
One GroupTourPackage
↓
Ordered GroupTourDay segments
```

The contract enforces these rules:

1. Package-day numbers and itinerary-day numbers are separate.
2. Pre-tour and post-tour hotels remain independent rows.
3. Optional/commercial rows are not package inclusions.
4. Sheet/configured season wins over conflicting source wording, but the conflict
   remains visible as a warning.
5. Generic parser mistakes such as classifying an overview as excluded do not
   override the identified booked package and its package-day rows.
6. Unknown accommodation names remain unknown. Generic hotel promises never
   become invented named properties.
7. Missing or conflicting facts produce warnings rather than silent repair.

## Contract version

```text
kind: group_tour_package
schema_version: 1
```

Metadata round-trips through `GroupTourPackage.from_metadata()` so later preview,
editor, inclusion, and PDF consumers can reuse the exact same structured result.

## Current integration boundary

Patch IH2 adds the contract and annotation helpers but does not yet migrate the
full parser or render pipeline.

Planned next steps:

1. Iceland GTS/GTW parser integration and package-day annotation
2. Preview/editor/PDF/final-inclusion migration
3. Cross-output parity and duplicate-package prevention

## IH3 parser and normalizer integration

Patch IH3 connects supplier-shaped rows to the contract through:

```text
itinerary_domain/group_tour_parsing.py
```

The integration boundary now:

- Recognizes `Group Tour`, `Activity Upgrade`, `Transfer Package`,
  `Single Supplement Fee`, and `Extra Hotel Night` as known row types.
- Marks package commercial rows optional by default unless their source units or
  commercial state explicitly show selection.
- Accepts package-day text both as `Day 1: ...` and as
  `Reykjavík: Day 1: ...`.
- Attaches one package contract to the master row and one day contract to each
  numbered programme row.
- Preserves independent arrivals, departures, transfers, leisure rows, and
  pre/post-tour hotels without package ownership metadata.
- Links optional commercial rows with `related_group_tour_package_id` while
  keeping them out of `group_tour_package_id` and package-day output.
- Removes only the Iceland workbook's exact `Totals / x / x` bookkeeping row.
- Accepts optional `source_name` and `group_tour_season` context in
  `normalize_itinerary_rows()` so trusted sheet metadata can remain canonical.

Rendering is still deferred to IH4. `Group Tour` rows remain package-day rows;
they are not silently converted into ordinary activities by the normalizer.

## IH4 rendering and output ownership

Patch IH4 makes the canonical package contract the only source for group-tour
client output through:

```text
itinerary_generation/group_tour_rendering.py
```

The rendering boundary now enforces:

- The package master is omitted from itinerary day blocks.
- Each `GroupTourDay` produces exactly one `group_tour_day` render block on its
  mapped itinerary day.
- Preview, visual editor, and typed PDF reuse the same block title, route,
  inclusions, meals, overnight note, conditions, and source-row identity.
- Final inclusions contain one `group_tour` product item, never one product per
  package day.
- Package accommodation is described inside the package inclusion while
  independent pre/post-tour hotels remain normal accommodation entries.
- Unselected upgrades, transfer packages, supplements, and extra nights remain
  outside included package content.
- Cover route, trip subtitle, travel style, and journey summaries consume the
  package season and ordered route regions.
- A source season conflict remains visible in package diagnostics and never
  changes the trusted configured season used by client-facing summaries.

The shared output path is now:

```text
Supplier rows
↓
GroupTourPackage + ordered GroupTourDay contracts
↓
Canonical day model + one package inclusion item
↓
Preview / visual editor / typed PDF
```
