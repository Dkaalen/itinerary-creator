# Patch 12 compatibility deletion audit

Every path below was deleted only after repository-wide import, string-reference, package-export, routing, test, script, documentation and runtime-owner review. The active implementation remains under `itinerary_domain`.

| Removed compatibility path | Neutral owner | Batch |
|---|---|---|
| `itinerary_generation/activity_cache.py` | `itinerary_domain.activity_cache` | 12A — zero-consumer facade |
| `itinerary_generation/activity_product_core.py` | `itinerary_domain.activity_product_core` | 12A — zero-consumer facade |
| `itinerary_generation/activity_product_rules/__init__.py` | `itinerary_domain.activity_product_rules` | 12C — conditional reference migration |
| `itinerary_generation/activity_product_rules/iceland.py` | `itinerary_domain.activity_product_rules.iceland` | 12A — zero-consumer facade |
| `itinerary_generation/activity_product_rules/nordic.py` | `itinerary_domain.activity_product_rules.nordic` | 12A — zero-consumer facade |
| `itinerary_generation/activity_product_rules/norway.py` | `itinerary_domain.activity_product_rules.norway` | 12C — conditional reference migration |
| `itinerary_generation/activity_product_rules/scandinavia.py` | `itinerary_domain.activity_product_rules.scandinavia` | 12A — zero-consumer facade |
| `itinerary_generation/activity_product_text.py` | `itinerary_domain.activity_product_text` | 12A — zero-consumer facade |
| `itinerary_generation/activity_training_loader.py` | `itinerary_domain.activity_training_loader` | 12A — zero-consumer facade |
| `itinerary_generation/activity_training_matcher.py` | `itinerary_domain.activity_training_matcher` | 12A — zero-consumer facade |
| `itinerary_generation/activity_training_model.py` | `itinerary_domain.activity_training_model` | 12A — zero-consumer facade |
| `itinerary_generation/activity_training_text.py` | `itinerary_domain.activity_training_text` | 12A — zero-consumer facade |
| `itinerary_generation/activity_training_validation.py` | `itinerary_domain.activity_training_validation` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_accommodation_policy.py` | `itinerary_domain.group_tour_accommodation_policy` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_builder.py` | `itinerary_domain.group_tour_builder` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_commercial_items.py` | `itinerary_domain.group_tour_commercial_items` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_constants.py` | `itinerary_domain.group_tour_constants` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_day_parser.py` | `itinerary_domain.group_tour_day_parser` | 12C — conditional reference migration |
| `itinerary_generation/group_tour_master_rows.py` | `itinerary_domain.group_tour_master_rows` | 12B — test-only surface |
| `itinerary_generation/group_tour_models.py` | `itinerary_domain.group_tour_models` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_orphan_days.py` | `itinerary_domain.group_tour_orphan_days` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_parsing.py` | `itinerary_domain.group_tour_parsing` | 12C — conditional reference migration |
| `itinerary_generation/group_tour_row_helpers.py` | `itinerary_domain.group_tour_row_helpers` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_serialization.py` | `itinerary_domain.group_tour_serialization` | 12A — zero-consumer facade |
| `itinerary_generation/group_tour_text.py` | `itinerary_domain.group_tour_text` | 12A — zero-consumer facade |
| `itinerary_generation/nutshell_cleaning.py` | `itinerary_domain.nutshell_cleaning` | 12A — zero-consumer facade |
| `itinerary_generation/nutshell_constants.py` | `itinerary_domain.nutshell_constants` | 12A — zero-consumer facade |
| `itinerary_generation/nutshell_journey_builder.py` | `itinerary_domain.nutshell_journey_builder` | 12B — test-only surface |
| `itinerary_generation/nutshell_labels.py` | `itinerary_domain.nutshell_labels` | 12B — test-only surface |
| `itinerary_generation/nutshell_model.py` | `itinerary_domain.nutshell_model` | 12B — test-only surface |
| `itinerary_generation/nutshell_route_parser.py` | `itinerary_domain.nutshell_route_parser` | 12B — test-only surface |
| `itinerary_generation/nutshell_route_parsing.py` | `itinerary_domain.nutshell_route_parsing` | 12C — conditional reference migration |
| `itinerary_generation/nutshell_source.py` | `itinerary_domain.nutshell_source` | 12C — conditional reference migration |
| `itinerary_generation/product_rule_context.py` | `itinerary_domain.product_rule_context` | 12A — zero-consumer facade |
| `itinerary_generation/product_rule_descriptions.py` | `itinerary_domain.product_rule_descriptions` | 12A — zero-consumer facade |
| `itinerary_generation/product_rule_evidence.py` | `itinerary_domain.product_rule_evidence` | 12A — zero-consumer facade |
| `itinerary_generation/product_rule_matcher.py` | `itinerary_domain.product_rule_matcher` | 12A — zero-consumer facade |
| `itinerary_generation/product_rule_models.py` | `itinerary_domain.product_rule_models` | 12A — zero-consumer facade |

The package directory `itinerary_generation/activity_product_rules/` is intentionally absent because all five compatibility files in it were retired and no consumer imports that package.

Permanent regression coverage lives in `tests/test_compatibility_deletion_boundary.py` and `tests/test_generation_architecture_cleanup.py`.
