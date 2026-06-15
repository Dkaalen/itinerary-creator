# Norway in a Nutshell dependency map

Patch BZ1A records the current product path before the dedicated domain refactor.
The product is a compound scenic journey, not a generic train, cruise, coach, or
activity. Its identity, route, legs, commercial status, and client title must be
classified once and reused by every consumer.

## Current source-to-output path

| Stage | Current modules and symbols | State carried forward | Risk before BZ1B/BZ1C |
| --- | --- | --- | --- |
| Parse | `parser_modules.parser_main.parse_itinerary`, `parser_modules.extract_inclusions` | Raw title, details, inclusions, time, commercial metadata | Product identity is not yet explicit. |
| Product detection | `itinerary_generation.activity_product_rules.norway`, `itinerary_generation.product_rules.find_product_match`, `itinerary_generation.transport_norway._is_norway_in_a_nutshell_text` | `activity_product.canonical_family == "norway_in_a_nutshell"` | Detection is repeated by text-marker checks outside the product rule. |
| Normalization | `normalizer_modules.transport.normalize_transport_title`, `normalizer_modules.transport.is_transport_activity`, `normalizer_modules.core` | Canonical title, `effective_type`, route metadata | Product is represented as a generic row plus loosely coupled metadata. |
| Route extraction | `itinerary_generation.transport_norway` | Explicit title, route points, timetable legs, supplier inclusions | Several consumers call low-level extractors independently and can choose different endpoints. |
| Client activity title | `itinerary_generation.activity_titles.create_client_activity_title`, `itinerary_generation.title_routes._route_label_from_activity_text` | Full client-facing product title | This path currently returns the correct `Norway in a Nutshell from X to Y` title. |
| Transport title | `itinerary_generation.transport_domain.titles.get_transport_route_phrase`, `get_primary_transport_title` | Route phrase and destination-focused day title | Direction/title policy is independently reconstructed. |
| Day planning | `itinerary_generation.day_titles.create_day_title`, `itinerary_generation.day_planner.create_day_plan` | Day heading and product-specific day kind | Detection and destination-focused title conversion are repeated. |
| Travel arrangements | `itinerary_generation.transport_domain.render._norway_nutshell_lines` | Day-page travel lines | Confirmed divergence: multi-point rows hardcode `Scenic Rail & Fjord Journey from X to Y`. |
| Final inclusions | `itinerary_generation.transport_domain.inclusions._norway_nutshell_inclusion_line`, `transport_line` | Product title, time, route facts, included services | Rebuilds route facts separately from the day renderer. |
| Summaries | `itinerary_generation.summaries.describe_city_experience`, `has_norway_in_a_nutshell` | Journey-arc summary wording | Uses broad marker detection and does not consume a canonical product object. |
| Structured document | `itinerary_generation.structured_builder._build_transport_item` | Generic scenic `TransportItem` | Product-specific legs and identity are not a dedicated structured type. |
| Preview/editor | `ui.day_blocks.build_day_blocks`, visual-editor document/payload builders | Rendered HTML and editor blocks | They inherit whichever title the travel renderer emits. |
| PDF | `pdf_exporter_modules.typed_exporter` and structured PDF story builders | Rendered day contract/HTML | PDF inherits day-render divergence; it should not re-detect the product. |
| Cover/image scoring | `itinerary_generation.cover_background_selector` | Scenic-journey image hints | Marker-based use is acceptable only as a consumer of canonical identity/fallback text. |

## Current duplicate decision points

The following decisions are made in more than one place and must move behind the
BZ1B product contract:

1. Whether a row is Norway in a Nutshell.
2. Whether an activity row becomes transport.
3. Route origin, destination, and direction.
4. Full product title versus destination-focused day title.
5. Ordered route points and route legs.
6. Whether the compound journey is emitted once or as independent transport legs.
7. Product-specific inclusion and summary wording.

## Canonical facts that must survive migration

- Canonical family: `norway_in_a_nutshell`.
- Full product title and route direction.
- Original supplier text and source row identifiers.
- Ordered rail, cruise, and coach legs when supplied.
- Journey-level departure/arrival time and per-leg times when supplied.
- Supplier inclusions, including luggage transfer where present.
- Commercial status and reason.
- Adjacent local transfers and accommodation remain separate itinerary rows.
- Missing facts are omitted; they are not inferred from unrelated rows.

## Resolved baseline defect

`tests/test_regressions_fixture_quality.py::test_v36c57_real_uploaded_inputs_quality_gate`
now passes because the day renderer consumes the canonical product title from
the attached contract. The isolated BZ1A expected-failure gate was converted
into a permanent passing regression assertion in BZ1C.

## Existing expectations that require deliberate migration

The following tests currently preserve the generic scenic label and must be
updated only when BZ1C routes all consumers through the canonical product title:

- `tests/test_qg_c_source_fidelity.py`
- `tests/test_qg_d_norway_source_fidelity.py`

Their route-leg and source-fidelity assertions remain valid. Only the generic
product label expectation is obsolete.

## BZ1B/BZ1C acceptance gates

1. A dedicated structured product is created once from normalized source data.
2. Generic renderers do not identify or rename Norway in a Nutshell.
3. Day page, preview, editor, inclusions, and PDF consume the same canonical title.
4. Route direction and ordered legs are identical across all consumers.
5. The compound product is emitted once; legs remain details of that product.
6. Optional and self-arranged status survive product normalization unchanged.
7. Adjacent station/hotel transfers remain separate and ordered.
8. Partial data preserves known endpoints and omits unknown times/operators.
9. Architecture tests prevent new product-specific title reconstruction in generic renderers.

## BZ1B implemented boundary

Patch BZ1B introduces `itinerary_generation.nutshell_domain` as the canonical
product contract. Normalized Nutshell rows now carry a versioned
`activity_product.domain_contract` containing:

- Canonical product identity and client title.
- Origin, destination and normalized direction.
- Ordered route points and structured rail/cruise/road legs.
- Journey-level and leg-level times when supplied.
- Supplier route inclusions and normalized included services.
- Commercial status/reason and source row identifiers.
- Explicit diagnostics for discontinuous or endpoint-conflicting source legs.

Activity fingerprinting and the legacy title entry points now delegate product
route/title decisions to this contract. The normalizer attaches the full
contract once after row normalization. Explicitly classified non-Nutshell
products, such as the Bergen guided Flåm day tour, take precedence over broad
route-marker detection.

BZ1B intentionally did not migrate day-page, inclusion, summary, editor or PDF
consumers. That migration is completed by BZ1C as documented below.

## BZ1C consumer migration

Patch BZ1C moves client-facing consumers onto the attached
`NutshellJourney` contract:

- Transport route titles resolve the contract before generic route logic.
- Day planning and day-title selection use the contract destination/title.
- Travel-arrangement blocks render the canonical product title, contract time,
  ordered contract legs, contract route points, and contract inclusions.
- Structured final inclusions use the same title, route facts, commercial row
  identity, and included services.
- Journey-arc classification checks canonical Nutshell identity rather than the
  legacy broad product-text helper.
- Preview, visual editor, and typed PDF export all inherit the same RenderDocument
  product line; they do not independently rename the journey.

The former strict expected-failure for the day-renderer title is now a normal
passing regression gate. The generic `Scenic Rail & Fjord Journey` alias and
low-level route re-parsing were removed from the day renderer.

For contradictory supplier legs, the contract keeps the original route-leg
facts and emits `route_leg_discontinuity`. Consumers do not create a synthetic
route-highlight sequence from those conflicting legs. For a continuous
newline-based timetable, the normalized contract retains the ordered route
points and consumers may render route highlights from that stored order.
