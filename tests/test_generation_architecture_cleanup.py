from __future__ import annotations

import importlib


GENERATION_FACADE_MODULES = [
    "itinerary_generation.day_intro_activity",
    "itinerary_generation.day_intro_arrival",
    "itinerary_generation.day_intro_route",
    "itinerary_generation.day_intro_classification",
    "itinerary_generation.structured_items_builder",
    "itinerary_generation.structured_warning_builder",
    "itinerary_generation.structured_days_builder",
    "itinerary_generation.structured_travel_sequences",
    "itinerary_generation.structured_final_sections",
    "itinerary_generation.editable_draft_model",
    "itinerary_generation.editable_draft_normalize",
    "itinerary_generation.editable_draft_lookup",
    "itinerary_generation.editable_draft_merge",
    "itinerary_generation.generation_quality_gate",
    "itinerary_generation.client_output_quality_gate",
    "itinerary_generation.nutshell_model",
    "itinerary_generation.nutshell_route_parser",
    "itinerary_generation.nutshell_journey_builder",
    "itinerary_generation.day_render_activity_blocks",
    "itinerary_generation.day_render_transport_blocks",
    "itinerary_generation.day_render_block_ordering",
    "itinerary_generation.day_render_document_adapter",
]

RETIRED_ZERO_IMPORT_FACADES = [
    "itinerary_generation.activity_title_normalization",
    "itinerary_generation.activity_title_rules",
    "itinerary_generation.city_experience_classifier",
    "itinerary_generation.debug.qa_edit_events",
    "itinerary_generation.debug.qa_report_model",
    "itinerary_generation.debug.qa_report_persist",
    "itinerary_generation.debug.qa_report_render",
    "itinerary_generation.debug.qa_warning_events",
    "itinerary_generation.image_quality_gate",
    "itinerary_generation.journey_arc_builder",
    "itinerary_generation.legacy_output_edits_bridge",
    "itinerary_generation.nutshell_detection",
    "itinerary_generation.render_document_text_scan",
    "itinerary_generation.trip_glance_builder",
    "itinerary_generation.exclusion_commercial_items",
    "itinerary_generation.exclusion_flights",
    "itinerary_generation.exclusion_formatting",
    "itinerary_generation.exclusion_self_transfers",
]


def test_generation_cleanup_modules_import_without_side_effects():
    for module_name in GENERATION_FACADE_MODULES:
        module = importlib.import_module(module_name)
        assert module.__all__, module_name


def test_zero_import_facades_removed_after_deletion_proof():
    for module_name in RETIRED_ZERO_IMPORT_FACADES:
        assert importlib.util.find_spec(module_name) is None, module_name


def test_generation_public_facades_keep_existing_entry_points():
    from itinerary_generation.activity_titles import create_client_activity_title
    from itinerary_generation.day_intro_engine import create_day_intro
    from itinerary_generation.day_render_blocks import build_render_day
    from itinerary_generation.editable_draft import normalise_editable_draft
    from itinerary_generation.exclusion_sections import create_whats_not_included
    from itinerary_generation.nutshell_domain import build_nutshell_journey
    from itinerary_generation.qa_report import build_qa_report
    from itinerary_generation.quality_gate import evaluate_itinerary_quality
    from itinerary_generation.structured_builder import build_itinerary_document
    from itinerary_generation.summaries import create_trip_glance

    assert callable(create_client_activity_title)
    assert callable(create_day_intro)
    assert callable(build_render_day)
    assert callable(normalise_editable_draft)
    assert callable(create_whats_not_included)
    assert callable(build_nutshell_journey)
    assert callable(build_qa_report)
    assert callable(evaluate_itinerary_quality)
    assert callable(build_itinerary_document)
    assert callable(create_trip_glance)
