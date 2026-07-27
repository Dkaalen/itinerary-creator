# Text Normalization and Sanitation Ownership

Patch 19 keeps syntax repair, source cleanup, field sanitation, document sanitation, domain-specific copy generation, and UI security separate.

## Shared primitives

| Authority | Responsibility | Must not do |
|---|---|---|
| `shared.text.clean_space` | Convert arbitrary values to one-line text, normalize non-breaking spaces and line endings, and collapse whitespace | Correct spelling, alter facts, infer geography, change casing, or rewrite supplier meaning |
| `place_alias_text.normalize_place_key` | Produce the accent-insensitive key used by Nordic alias maps and the destination registry | Return client-facing display text or choose between ambiguous destinations |
| `shared.text_cleanup_rules` | Own shared typo, casing, proper-noun, and QA pattern tables | Apply destination-copy or product-specific generation policy |

The legacy private `place_alias_text._key` name remains a compatibility wrapper around `normalize_place_key`.

## Three sanitation stages

| Stage | Authority | Responsibility | Must not do |
|---|---|---|---|
| Supplier/source cleanup | `shared.source_text_cleanup` | Repair source-system artifacts and supplier-only administrative lines before parser/normalizer interpretation | Apply customer synonyms, reclassify products, erase provenance, or rewrite source-owned names |
| Field-aware sanitation | `itinerary_domain.field_sanitation` | Sanitize titles, descriptions, inclusions, exclusions, meeting points, locations, times, URL metadata, internal notes, and HTML according to field semantics | Traverse documents, infer itinerary facts, apply title case, or globally erase internal metadata |
| Final prepared-document sanitation | `itinerary_generation.final_document_sanitation` | Traverse one prepared `RenderDocument` once and sanitize only customer-visible fields | Reparse, renormalize, classify, calculate continuity, alter images/financials, or mutate technical metadata |

See `docs/architecture/PATCH_19_THREE_STAGE_SANITATION_CONTRACT.md` for the complete contract.

## Explicit semantic owners

These layers deliberately remain separate because their rules are not equivalent:

- `text_polish_modules.text_cleanup`: generated client-prose polishing inside domain/copy generation, not source sanitation or final-document traversal.
- `text_polish_modules.titles`: title casing, small-word handling, named-product spelling, and title-only removals.
- `itinerary_generation.destination_helpers`: route/display destination cleanup and client-title marketing removals.
- `itinerary_generation.destination_content`: destination-specific arrival, leisure, and travel-day copy.
- `itinerary_generation.transport_domain`: route endpoint parsing and transport-specific generation.
- activity, hotel, day-title, and group-tour modules: product- or output-specific transformations backed by their own tests.
- `ui.editor_sanitizer`: UI HTML security at the editor/rendering boundary, not itinerary sanitation.
- `itinerary_generation.client_output_quality_gate`: audit-only validation of the sanitized prepared document.

## Rule for future consolidation

Share a helper only when inputs, outputs, field semantics, punctuation behavior, casing behavior, metadata treatment, and failure semantics are identical. Similar-looking regular expressions are not sufficient evidence. Add or update behavioral snapshots and ownership guards before moving a rule between owners.
