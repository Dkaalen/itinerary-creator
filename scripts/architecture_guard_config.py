"""Static configuration for architecture guard checks."""

from __future__ import annotations

NORMAL_WORKFLOW_SOURCES = (
    "app_modules/main_view.py",
    "app_modules/input_step.py",
    "app_modules/preview_step.py",
    "app_modules/picture_step.py",
    "app_modules/export_page.py",
    "app_modules/workflow_shell.py",
    "app_modules/workflow_actions.py",
    "app_modules/generation_action.py",
    "app_modules/project_load_action.py",
    "app_modules/image_stage_action.py",
    "app_modules/export_stage_action.py",
    "visual_editor_component/frontend/js/render.js",
    "visual_editor_component/frontend/js/editor_shell.js",
    "visual_editor_component/frontend/js/editor_dirty_state.js",
    "visual_editor_component/frontend/js/state.js",
)

NORMAL_WORKFLOW_GLOBS = (
    "visual_editor_component/frontend/js/editor_inspector*.js",
    "visual_editor_component/frontend/styles/editor*.css",
    "ui/style*.py",
)

DEBUG_ALLOWED_SOURCES = frozenset(
    {
        "app_modules/debug_tools.py",
        "ui/input_review_panel.py",
        "ui/diagnostics_panel.py",
        "visual_editor_component/frontend/js/editor_debug_shell.js",
        "visual_editor_component/frontend/js/editor_debug_readiness.js",
        "visual_editor_component/frontend/js/editor_readiness.js",
        "visual_editor_component/frontend/styles/editor_debug.css",
        "ui/style_debug.py",
        "itinerary_generation/input_review.py",
        "pdf_exporter_modules/pdf_internal_review_appendix.py",
    }
)

FORBIDDEN_NORMAL_UI_MARKERS = (
    "Document checks",
    "Export checks",
    "Autosave ready",
    "Server autosave ready",
    "Advanced tools",
    "Structured input review",
    "Rows to review",
    "Parser confidence",
    "Safe parser fixes",
    "Correction queue",
    "Review summary",
    "Client QA",
    "Ready for Client",
    "Needs Review",
    "WHY THIS IMAGE",
    "IMAGE TOOLS",
    "REPLACEMENT IMAGE",
)

HIGH_VALUE_SOURCE_ROOTS = (
    "app_modules",
    "parser_modules",
    "pdf_exporter_modules",
    "images",
    "visual_editor_component/frontend/js",
    "visual_editor_component/frontend/styles",
)

PATCH_HISTORY_NAME_MARKERS = (
    "_late",
    "_corrections",
    "_new",
    "_old",
    "_misc",
    "-late",
    "-corrections",
    "-new",
    "-old",
    "-misc",
)

ROOT_PATCH_ARTIFACT_NAMES = frozenset({"CHANGED_FILES_MANIFEST.md", "DELETION_MANIFEST.md"})
PATCH_METADATA_DIR_NAMES = frozenset({"_patch_metadata"})
DUPLICATE_TEST_DIRS = ("tests", "visual_editor_component/tests")

TOP_LEVEL_COMPATIBILITY_FACADES = {
    "generator.py": 90,
    "image_matcher.py": 40,
    "itinerary_parser.py": 40,
    "normalizer.py": 20,
    "pdf_exporter.py": 100,
    "text_polish.py": 20,
}


CLEANED_GENERATION_CORE_FACADES = {
    "itinerary_generation/day_intro_engine_core.py": 80,
    "itinerary_generation/day_render_blocks_core.py": 80,
    "itinerary_generation/editable_draft_core.py": 120,
    "itinerary_generation/exclusion_sections_core.py": 80,
    "itinerary_generation/nutshell_domain_core.py": 80,
    "itinerary_generation/qa_report_core.py": 80,
    "itinerary_generation/quality_gate_core.py": 140,
    "itinerary_generation/structured_builder_core.py": 160,
    "itinerary_generation/summaries_core.py": 80,
}

GENERATION_CORE_FACADE_MODULES = (
    "itinerary_generation.day_intro_engine_core",
    "itinerary_generation.day_render_blocks_core",
    "itinerary_generation.editable_draft_core",
    "itinerary_generation.exclusion_sections_core",
    "itinerary_generation.nutshell_domain_core",
    "itinerary_generation.qa_report_core",
    "itinerary_generation.quality_gate_core",
    "itinerary_generation.structured_builder_core",
    "itinerary_generation.summaries_core",
)

GENERATION_IMPLEMENTATION_MODULES_THAT_MUST_NOT_IMPORT_CORE = (
    "itinerary_generation/city_experience_classifier.py",
    "itinerary_generation/day_intro_activity.py",
    "itinerary_generation/day_intro_arrival.py",
    "itinerary_generation/day_intro_classification.py",
    "itinerary_generation/day_intro_route.py",
    "itinerary_generation/day_render_activity_blocks.py",
    "itinerary_generation/day_render_block_ordering.py",
    "itinerary_generation/day_render_document_adapter.py",
    "itinerary_generation/day_render_group_tour_blocks.py",
    "itinerary_generation/day_render_leisure_blocks.py",
    "itinerary_generation/day_render_transport_blocks.py",
    "itinerary_generation/debug/qa_edit_events.py",
    "itinerary_generation/debug/qa_report_model.py",
    "itinerary_generation/debug/qa_report_persist.py",
    "itinerary_generation/debug/qa_report_render.py",
    "itinerary_generation/debug/qa_warning_events.py",
    "itinerary_generation/editable_draft_model.py",
    "itinerary_generation/editable_draft_normalize.py",
    "itinerary_generation/editable_draft_lookup.py",
    "itinerary_generation/editable_draft_merge.py",
    "itinerary_generation/editable_draft_legacy_bridge.py",
    "itinerary_generation/exclusion_commercial_items.py",
    "itinerary_generation/exclusion_flights.py",
    "itinerary_generation/exclusion_formatting.py",
    "itinerary_generation/exclusion_self_transfers.py",
    "itinerary_generation/generation_quality_gate.py",
    "itinerary_generation/client_output_quality_gate.py",
    "itinerary_generation/journey_arc_builder.py",
    "itinerary_generation/journey_arc_text_safety.py",
    "itinerary_generation/nutshell_detection.py",
    "itinerary_generation/nutshell_journey_builder.py",
    "itinerary_generation/nutshell_labels.py",
    "itinerary_generation/nutshell_model.py",
    "itinerary_generation/nutshell_route_parser.py",
    "itinerary_generation/nutshell_source.py",
    "itinerary_generation/quality_gate_patterns.py",
    "itinerary_generation/structured_row_helpers.py",
    "itinerary_generation/structured_items_builder.py",
    "itinerary_generation/structured_warning_builder.py",
    "itinerary_generation/structured_days_builder.py",
    "itinerary_generation/structured_travel_sequences.py",
    "itinerary_generation/structured_final_sections.py",
    "itinerary_generation/trip_glance_builder.py",
)

EXACT_VAGUE_FILE_NAMES = frozenset({"utils.py", "helpers.py", "utils.js", "helpers.js", "utils.css", "helpers.css"})

PYTHON_FUNCTION_ALLOWLIST = frozenset(
    {
        "itinerary_generation/activity_titles_core.py:create_client_activity_title",
        "itinerary_generation/day_intro_engine.py:create_day_intro",
        "itinerary_generation/summaries.py:describe_city_experience",
    }
)

PYTHON_FILE_ALLOWLIST = frozenset(
    {
        "itinerary_generation/data/nordic_destination_registry.py",
    }
)
