# Patch 19 — Three-Stage Sanitation Contract

## Decision

Itinerary sanitation is deliberately split into three owners with different inputs, permissions, and failure semantics:

1. **Supplier/source cleanup** — `shared/source_text_cleanup.py`
2. **Field-aware customer sanitation** — `itinerary_domain/field_sanitation.py`
3. **Final prepared-document sanitation** — `itinerary_generation/final_document_sanitation.py`

The supported execution boundary is:

```text
source/workbook text
→ supplier/source cleanup
→ parser and normalizer/domain enrichment
→ field-aware sanitation
→ prepared RenderDocument
→ one final-document sanitation traversal
→ audit-only quality evaluation
→ preview/editor/PDF rendering
```

These stages are not interchangeable and must not be collapsed into a universal text cleaner.

## Stage 1 — supplier/source cleanup

`shared/source_text_cleanup.py` owns conservative source-system repair before parser and normalizer interpretation.

It may:

- repair recurring source typos and malformed section boundaries;
- remove clearly labelled supplier-only administrative lines;
- normalize known Nordic place aliases and safe whitespace/punctuation artifacts;
- preserve multiline supplier cells for parser extraction.

It must preserve:

- product names and source-owned terminology;
- source capitalization, including lowercase-leading brand names;
- Nordic and other Unicode characters;
- ratings such as `3/4-star`;
- dates, quantities, and valid time ranges;
- workbook provenance and internal source URLs, which are stored separately from customer copy.

It must not import field or final-document sanitation, apply customer-language synonyms, or reinterpret itinerary facts.

## Stage 2 — field-aware sanitation

`itinerary_domain/field_sanitation.py` owns sanitation of individual already-extracted or generated values.

The supported field types are:

- title;
- description;
- inclusion;
- exclusion;
- meeting point;
- location;
- time;
- URL metadata;
- internal note.

Customer-visible fields remove booking URLs, protocol-relative URLs, contacts, supplier codes, commercial fragments, placeholders, duplicate labels, duplicate punctuation, and unsafe HTML. URL metadata and internal notes preserve their internal values.

Field sanitation is idempotent and must not apply title case, synonyms, route inference, product classification, date inference, continuity decisions, or source-name rewriting.

HTML sanitation in this stage removes unsafe blocks and attributes while retaining safe structural markup and source-identity attributes such as `data-source-row-ids` when their values contain no URL or executable content.

## Stage 3 — final prepared-document sanitation

`itinerary_generation/final_document_sanitation.py` owns the only traversal of the completed prepared `RenderDocument`.

It sanitizes customer-visible fields according to their type, including:

- document, cover, summary, day, and block copy;
- typed metadata values such as time, meeting point, and location;
- structured inclusions and exclusions;
- notes and manual final-page HTML.

It does not traverse or mutate:

- row IDs or source-row IDs;
- warnings or internal labels;
- continuity reports;
- image/background paths;
- hidden-page state or page order;
- CSS classes;
- final-section metadata;
- workbook provenance, source URLs, or financial state.

The render context attaches the full editor/PDF contract, sanitizes the editor document once, then derives the visible preview/PDF projection from that sanitized authority. Renderers do not perform independent customer-copy cleanup.

## Quality boundary

`itinerary_generation/client_output_quality_gate.py` is audit-only. It receives the sanitized visible `RenderDocument`, reports remaining violations, and does not mutate or repair the document.

`itinerary_generation/client_quality_text.py` traverses an explicit list of customer-visible fields. It does not recursively inspect technical dataclass state. Canonical page headings are excluded from raw-supplier-label scanning so labels such as “What’s included” are not treated as source leakage.

The prepared quality report remains the single report reused by preview, PDF readiness, health reporting, and real-output QA.

## UI security boundary

`ui/editor_sanitizer.py` remains a separate rendering/security concern. It sanitizes HTML at the visual-editor rendering boundary and does not replace itinerary field or final-document sanitation.

## Internal metadata and Excel export

Internal Local Library URLs and workbook provenance remain authoritative through Calculator state, generation handoff, project storage, and workbook export. They are excluded from customer-facing generator text and quality traversal, but retained in the Excel export provenance property `BooknordicsLocalLibraryProvenance`.

## Retired mixed owners

Patch 19 deletes the prior mixed-responsibility modules:

- `itinerary_generation/supplier_cleanup_brain.py`
- `itinerary_generation/client_copy_sanitation.py`
- `itinerary_generation/client_sanitizer.py`

They must not be recreated as forwarding wrappers.

## Guardrails

Architecture tests fail when:

- parser/source cleanup imports field or final-document sanitation;
- supplier cleanup invokes customer semantic polishing;
- final-document sanitation imports parser, normalizer, classification, continuity, or document-building owners;
- more than one production call site traverses a prepared document for sanitation;
- preview/editor/PDF renderers invoke independent customer sanitation;
- quality calls a mutating sanitizer;
- quality recursively traverses technical metadata;
- internal URL/provenance fields are globally erased;
- the retired mixed owners reappear.

## Repository call-graph classification

Patch 19 audited cleanup and normalization calls by execution purpose rather than function name. The repository-wide classification is:

| Execution area | Classification | Supported ownership |
|---|---|---|
| Workbook loading and Local Library preparation | Internal metadata preservation and unrelated normalization | Workbook readers, provenance/fingerprint owners, product indexing, aliasing, and ranking may normalize lookup keys, paths, URLs, and spreadsheet values. They do not sanitize customer copy or erase source URLs. |
| Raw parser input and source-row standardization | Supplier/source cleanup plus extraction normalization | `shared/source_text_cleanup.py`, source time/duration normalization, and parser-specific token extraction repair source-system artifacts before facts are interpreted. They do not import Stage 2 or Stage 3. |
| Normalizer and domain enrichment | Field-aware sanitation plus unrelated fact enrichment | Extracted title, description, location, meeting-point, and time fields use `itinerary_domain.field_sanitation`; classification, route facts, city propagation, duration, and source identity remain separate domain decisions. |
| Description, title, inclusion, and exclusion generation | Copy composition plus field-aware sanitation | Copy brains and `text_polish` compose supported customer wording from already interpreted facts. Stage 2 removes prohibited fragments at explicit typed boundaries; it does not perform classification or route inference. |
| Manual final pages and render-context preparation | Field-aware sanitation followed by one final-document traversal | User-authored final-page fields are typed when prepared. `app_modules.itinerary_render_context` invokes `sanitize_prepared_render_document` once on the full prepared editor/PDF authority before deriving the visible projection. |
| Preview, visual editor, and PDF renderers | Prepared-document consumption | Renderers project the prepared sanitized fields and do not invoke supplier cleanup, field sanitation, or final-document sanitation independently. |
| Visual-editor HTML boundary | UI security sanitization | `ui/editor_sanitizer.py` applies rendering/security rules independently of itinerary sanitation. Shared clipboard-marker removal is a narrow security utility, not a customer-copy stage. |
| Quality gate, health reporting, and real-output QA | Audit-only inspection | These consumers inspect the same sanitized prepared document and report violations. They do not repair or mutate it. |
| Excel export and financial projection | Internal metadata preservation and unrelated normalization | Export planning and renderers retain workbook provenance, source identity, formulas, and internal source URLs where required. They do not copy those values into customer-facing text. |
| URL parsing, product fingerprints, generated-ownership hashes, and comparison helpers | Internal metadata preservation or unrelated normalization | Canonicalization used for identity, equality, caching, and diagnostics is not customer-copy sanitation and remains outside the three stages. |
| Generic whitespace, HTML-to-text, and display helpers | Unrelated normalization | `clean_space`, PDF text extraction, comparison folding, and safe display formatting remain local transformations only where they do not remove customer-visible facts or commercial leakage. |

This classification is enforced by architecture tests over imports and production call sites. Similar names such as `clean_text`, `sanitize_*`, or `normalize_*` are not sufficient grounds to move a call between stages; its execution input, output, and consumer determine its category.
