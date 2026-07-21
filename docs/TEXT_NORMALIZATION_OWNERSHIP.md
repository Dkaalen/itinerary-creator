# Text Normalization Ownership

Patch 18 keeps syntax-only normalization shared and meaning-specific rules local to their domain.

## Shared primitives

| Authority | Responsibility | Must not do |
|---|---|---|
| `shared.text.clean_space` | Convert arbitrary values to one-line text, normalize non-breaking spaces and line endings, and collapse whitespace | Correct spelling, alter punctuation, infer geography, change casing, or rewrite supplier meaning |
| `place_alias_text.normalize_place_key` | Produce the accent-insensitive key used by Nordic alias maps and the destination registry | Return client-facing display text or choose between ambiguous destinations |
| `shared.text_cleanup_rules` | Own shared typo, casing, proper-noun, and QA pattern tables | Apply destination-copy or product-specific generation policy |

The legacy private `place_alias_text._key` name remains a compatibility wrapper around `normalize_place_key`.

## Explicit semantic owners

These layers deliberately remain separate because their rules are not equivalent:

- `text_polish_modules.text_cleanup`: client-facing prose cleanup, including multiline preservation and supplier-fragment handling.
- `text_polish_modules.titles`: title casing, small-word handling, named-product spelling, and title-only removals.
- `itinerary_generation.supplier_cleanup_brain`: conservative supplier-fragment punctuation and wording repairs.
- `itinerary_generation.destination_helpers`: route/display destination cleanup and client-title marketing removals.
- `itinerary_generation.destination_content`: destination-specific arrival, leisure, and travel-day copy.
- `itinerary_generation.transport_domain`: route endpoint parsing and transport-specific cleanup.
- activity, hotel, day-title, and group-tour modules: product- or output-specific transformations backed by their own tests.

## Rule for future consolidation

Share a helper only when inputs, outputs, punctuation behavior, casing behavior, and failure semantics are identical. Similar-looking regular expressions are not sufficient evidence. Add or update behavioral snapshots before moving a rule between owners.
