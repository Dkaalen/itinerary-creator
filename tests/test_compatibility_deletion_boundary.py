from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RETIRED_GENERATION_SHIMS = (
    "activity_cache.py",
    "activity_product_core.py",
    "activity_product_text.py",
    "activity_training_loader.py",
    "activity_training_matcher.py",
    "activity_training_model.py",
    "activity_training_text.py",
    "activity_training_validation.py",
    "group_tour_accommodation_policy.py",
    "group_tour_builder.py",
    "group_tour_commercial_items.py",
    "group_tour_constants.py",
    "group_tour_day_parser.py",
    "group_tour_master_rows.py",
    "group_tour_models.py",
    "group_tour_orphan_days.py",
    "group_tour_parsing.py",
    "group_tour_row_helpers.py",
    "group_tour_serialization.py",
    "group_tour_text.py",
    "nutshell_cleaning.py",
    "nutshell_constants.py",
    "nutshell_journey_builder.py",
    "nutshell_labels.py",
    "nutshell_model.py",
    "nutshell_route_parser.py",
    "nutshell_route_parsing.py",
    "nutshell_source.py",
    "product_rule_context.py",
    "product_rule_descriptions.py",
    "product_rule_evidence.py",
    "product_rule_matcher.py",
    "product_rule_models.py",
)

NEUTRAL_OWNERS = (
    "itinerary_domain.activity_cache",
    "itinerary_domain.activity_product_core",
    "itinerary_domain.activity_product_text",
    "itinerary_domain.activity_training_loader",
    "itinerary_domain.activity_training_matcher",
    "itinerary_domain.activity_training_model",
    "itinerary_domain.activity_training_text",
    "itinerary_domain.activity_training_validation",
    "itinerary_domain.group_tour_accommodation_policy",
    "itinerary_domain.group_tour_builder",
    "itinerary_domain.group_tour_commercial_items",
    "itinerary_domain.group_tour_constants",
    "itinerary_domain.group_tour_day_parser",
    "itinerary_domain.group_tour_master_rows",
    "itinerary_domain.group_tour_models",
    "itinerary_domain.group_tour_orphan_days",
    "itinerary_domain.group_tour_parsing",
    "itinerary_domain.group_tour_row_helpers",
    "itinerary_domain.group_tour_serialization",
    "itinerary_domain.group_tour_text",
    "itinerary_domain.nutshell_cleaning",
    "itinerary_domain.nutshell_constants",
    "itinerary_domain.nutshell_journey_builder",
    "itinerary_domain.nutshell_labels",
    "itinerary_domain.nutshell_model",
    "itinerary_domain.nutshell_route_parser",
    "itinerary_domain.nutshell_route_parsing",
    "itinerary_domain.nutshell_source",
    "itinerary_domain.product_rule_context",
    "itinerary_domain.product_rule_descriptions",
    "itinerary_domain.product_rule_evidence",
    "itinerary_domain.product_rule_matcher",
    "itinerary_domain.product_rule_models",
)


def test_retired_generation_shims_are_absent() -> None:
    base = ROOT / "itinerary_generation"
    for filename in RETIRED_GENERATION_SHIMS:
        assert not (base / filename).exists(), filename
    assert not (base / "activity_product_rules").exists()


def test_neutral_replacements_are_importable() -> None:
    for module_name in NEUTRAL_OWNERS:
        assert importlib.import_module(module_name) is not None, module_name
