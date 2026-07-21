from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PDF_PACKAGE_EXPORTS = (
    "pdf_style_tokens",
    "pdf_branding",
    "pdf_style_base",
    "pdf_style_cover",
    "pdf_style_day",
    "pdf_style_final_pages",
    "pdf_style_summary",
    "pdf_style_tables",
    "styles",
    "html_utils",
    "story",
    "day_page_guard",
    "pdf_reportlab_config",
    "image_constants",
    "image_layout",
    "background_flowables",
    "same_page_image_flowable",
    "image_flowables",
    "decorative_flowables",
    "render_tables",
    "render_flowables",
    "cover_page",
    "image_paths",
    "render_text",
    "render_cover",
    "render_controlled_content",
    "render_inclusion_content",
    "render_content_blocks",
    "day_images",
    "render_pages",
    "render_content",
    "render_glance",
    "exporter",
    "export_html_to_pdf",
    "export_profiles",
    "pdf_export_profile_options",
    "pdf_filename",
    "resolve_pdf_export_profile",
    "pdf_cover_renderer",
    "pdf_image_renderer",
    "pdf_supported_html_renderer",
    "pdf_day_renderer",
    "pdf_final_section_renderer",
    "pdf_html_support",
    "pdf_html_fallback",
    "pdf_image_prewarm",
    "typed_exporter",
    "export_render_document_to_pdf",
    "render_document_requires_html_fallback",
    "clean_text",
    "has_class",
    "para_text",
    "add_day_image_if_possible",
    "PDF_CROP_FOCUS_FACTORS",
    "PDF_CROP_VERTICAL_FOCUS",
    "PDF_IMAGE_BOTTOM_Y",
    "PDF_IMAGE_GAP",
    "PDF_IMAGE_HALF_OFFSET",
    "PDF_MIN_IMAGE_HEIGHT",
    "calculate_day_image_layout",
    "make_cover_cropped_image",
    "normalize_crop_focus",
    "resolve_image_path",
    "SamePageDayImage",
    "render_day_section_pdf",
    "render_general_page",
    "render_cover_page",
    "render_glance_page",
    "add_bullets",
    "add_paragraph",
    "make_table",
    "story_height",
    "BODY",
    "CARD",
    "DEFAULT_PDF_COLORS",
    "INK",
    "LINE",
    "MUTED",
    "PAGE_BACKGROUND",
    "apply_pdf_palette",
    "extract_pdf_palette",
    "hex_to_color",
    "make_styles",
    "page_background",
)

EXPECTED_PDF_FACADE_EXPORTS = (
    "BODY",
    "CARD",
    "DEFAULT_PDF_COLORS",
    "INK",
    "LINE",
    "MUTED",
    "PAGE_BACKGROUND",
    "PDF_CROP_FOCUS_FACTORS",
    "PDF_CROP_VERTICAL_FOCUS",
    "PDF_IMAGE_BOTTOM_Y",
    "PDF_IMAGE_GAP",
    "PDF_IMAGE_HALF_OFFSET",
    "PDF_MIN_IMAGE_HEIGHT",
    "SamePageDayImage",
    "_activity_time_range_text",
    "add_bullets",
    "add_day_image_if_possible",
    "add_paragraph",
    "apply_pdf_palette",
    "calculate_day_image_layout",
    "clean_text",
    "export_html_to_pdf",
    "export_render_document_to_pdf",
    "render_document_requires_html_fallback",
    "extract_pdf_palette",
    "has_class",
    "hex_to_color",
    "make_cover_cropped_image",
    "make_styles",
    "make_table",
    "normalize_crop_focus",
    "page_background",
    "pdf_export_profile_options",
    "pdf_filename",
    "resolve_pdf_export_profile",
    "para_text",
    "render_content_blocks",
    "render_cover_page",
    "render_day_section_pdf",
    "render_general_page",
    "render_glance_page",
    "resolve_image_path",
    "story_height",
)

_HEAVY_PDF_MODULES = {
    "pdf_exporter_modules.exporter",
    "pdf_exporter_modules.typed_exporter",
    "pdf_exporter_modules.styles",
    "pdf_exporter_modules.render_content",
    "pdf_exporter_modules.render_cover",
    "pdf_exporter_modules.render_glance",
}


def _run_probe(source: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return json.loads(completed.stdout)


def test_pdf_package_import_is_lightweight_in_clean_process() -> None:
    result = _run_probe(
        """
import importlib
import json
import sys

importlib.import_module("pdf_exporter_modules")
loaded = sorted(name for name in sys.modules if name.startswith("pdf_exporter_modules"))
print(json.dumps({"loaded": loaded}))
"""
    )

    assert result["loaded"] == ["pdf_exporter_modules"]


def test_pdf_public_api_and_top_level_facade_imports_are_lightweight() -> None:
    for module_name in ("pdf_exporter_modules.public_api", "pdf_exporter"):
        result = _run_probe(
            f"""
import importlib
import json
import sys

importlib.import_module({module_name!r})
loaded = sorted(name for name in sys.modules if name.startswith("pdf_exporter_modules"))
print(json.dumps({{"loaded": loaded}}))
"""
        )

        assert _HEAVY_PDF_MODULES.isdisjoint(result["loaded"])


def test_pdf_package_and_facade_export_contracts_are_preserved() -> None:
    import pdf_exporter
    import pdf_exporter_modules
    from pdf_exporter_modules import public_api

    assert tuple(pdf_exporter_modules.__all__) == EXPECTED_PDF_PACKAGE_EXPORTS
    assert tuple(public_api.__all__) == EXPECTED_PDF_FACADE_EXPORTS
    assert tuple(pdf_exporter.__all__) == EXPECTED_PDF_FACADE_EXPORTS


def test_pdf_package_resolves_symbols_and_submodules_lazily() -> None:
    import importlib

    import pdf_exporter_modules as package

    exporter = importlib.import_module("pdf_exporter_modules.exporter")
    styles = importlib.import_module("pdf_exporter_modules.styles")
    cover_page = importlib.import_module("pdf_exporter_modules.cover_page")

    assert package.export_html_to_pdf is exporter.export_html_to_pdf
    assert package.make_styles is styles.make_styles
    assert package.BODY is styles.BODY
    assert package.cover_page is cover_page


def test_pdf_compatibility_facades_resolve_the_same_objects_lazily() -> None:
    import pdf_exporter
    from pdf_exporter_modules import public_api
    from pdf_exporter_modules.exporter import export_html_to_pdf
    from pdf_exporter_modules.typed_exporter import export_render_document_to_pdf

    assert public_api.export_html_to_pdf is export_html_to_pdf
    assert pdf_exporter.export_html_to_pdf is export_html_to_pdf
    assert public_api.export_render_document_to_pdf is export_render_document_to_pdf
    assert pdf_exporter.export_render_document_to_pdf is export_render_document_to_pdf

EXPECTED_IMAGE_PACKAGE_EXPORTS = (
    "CITY_ALIASES",
    "IMAGE_EXTENSIONS",
    "SEASON_ALIASES",
    "SUMMER_MONTHS",
    "THEME_ALIASES",
    "WINTER_MONTHS",
    "ImageAuditWarning",
    "ImageCandidate",
    "ImageBankIndex",
    "DestinationRequest",
    "_candidate_destination_matches",
    "_candidate_to_payload",
    "_coerce_image_bank_paths",
    "_is_global_default_candidate",
    "_score_default_candidate",
    "_season_available_for_context",
    "_select_best_candidate_for_context",
    "audit_day_image_match",
    "audit_day_image_matches",
    "build_day_context",
    "candidate_destination_matches",
    "candidate_to_payload",
    "city_variants",
    "connect_remote_image_bank_if_missing",
    "destination_requests_from_rows",
    "coerce_image_bank_paths",
    "extract_image_metadata",
    "ensure_runtime_image_bank",
    "ensure_runtime_image_bank_status",
    "ensure_destination_packs",
    "format_match_for_debug",
    "get_image_bank_diagnostics",
    "image_bank_debug_payload",
    "image_bank_status",
    "image_bank_status_for_paths",
    "image_bank_status_summary",
    "image_bank_manifest_url",
    "get_image_bank_index",
    "invalidate_image_bank_cache",
    "day_image_matches_from_preview_html",
    "merge_preview_image_contract",
    "prefetch_image_bank_for_rows",
    "infer_primary_month_from_rows",
    "infer_season_from_rows",
    "infer_seasons",
    "infer_themes",
    "is_global_default_candidate",
    "normalize_keyword",
    "scan_image_bank",
    "score_default_candidate",
    "score_image_for_day",
    "season_available_for_context",
    "select_best_candidate_for_context",
    "select_day_image",
    "select_day_images",
    "tokenize",
)


def test_images_package_import_is_lightweight_in_clean_process() -> None:
    result = _run_probe(
        """
import importlib
import json
import sys

importlib.import_module("images")
loaded = sorted(name for name in sys.modules if name.startswith("images"))
print(json.dumps({"loaded": loaded}))
"""
    )

    assert result["loaded"] == ["images"]


def test_images_package_export_contract_is_preserved() -> None:
    import images

    assert tuple(images.__all__) == EXPECTED_IMAGE_PACKAGE_EXPORTS


def test_images_package_resolves_symbols_and_submodules_lazily() -> None:
    import importlib

    import images

    metadata = importlib.import_module("images.metadata")
    matcher = importlib.import_module("images.matcher")
    image_bank = importlib.import_module("images.image_bank")

    assert images.ImageCandidate is metadata.ImageCandidate
    assert images.select_day_image is matcher.select_day_image
    assert images.ensure_runtime_image_bank is image_bank.ensure_runtime_image_bank
    assert images.image_bank is image_bank


def test_image_matcher_compatibility_facade_still_exports_image_api() -> None:
    import image_matcher
    from images.matcher import select_day_image
    from images.metadata import ImageCandidate

    assert image_matcher.select_day_image is select_day_image
    assert image_matcher.ImageCandidate is ImageCandidate

EXPECTED_NORMALIZER_EXPORTS = (
    "normalize_row",
    "normalize_itinerary_rows",
    "warn_suspicious_city",
)

EXPECTED_COPY_EXPORTS = (
    "DayVisitContext",
    "build_day_visit_contexts",
    "client_activity_intro",
    "client_group_tour_intro",
)


def test_normalizer_package_and_facade_imports_are_lightweight() -> None:
    for module_name in ("normalizer_modules", "normalizer"):
        result = _run_probe(
            f"""
import importlib
import json
import sys

importlib.import_module({module_name!r})
loaded = sorted(name for name in sys.modules if name.startswith("normalizer_modules"))
print(json.dumps({{"loaded": loaded}}))
"""
        )
        assert result["loaded"] == ["normalizer_modules"]


def test_normalizer_package_and_facade_contracts_are_preserved() -> None:
    import normalizer
    import normalizer_modules
    from normalizer_modules.core import normalize_itinerary_rows, normalize_row, warn_suspicious_city

    assert tuple(normalizer_modules.__all__) == EXPECTED_NORMALIZER_EXPORTS
    assert tuple(normalizer.__all__) == EXPECTED_NORMALIZER_EXPORTS
    assert normalizer_modules.normalize_row is normalize_row
    assert normalizer.normalize_itinerary_rows is normalize_itinerary_rows
    assert normalizer.warn_suspicious_city is warn_suspicious_city


def test_copy_package_import_is_lightweight_and_submodules_are_independent() -> None:
    result = _run_probe(
        """
import importlib
import json
import sys

importlib.import_module("itinerary_generation.copy.visit_context")
loaded = sorted(name for name in sys.modules if name.startswith("itinerary_generation.copy"))
print(json.dumps({"loaded": loaded}))
"""
    )

    assert "itinerary_generation.copy" in result["loaded"]
    assert "itinerary_generation.copy.visit_context" in result["loaded"]
    assert "itinerary_generation.copy.activity_composition" not in result["loaded"]


def test_copy_package_export_contract_is_preserved_lazily() -> None:
    import itinerary_generation.copy as copy_package
    from itinerary_generation.copy.activity_composition import client_activity_intro, client_group_tour_intro
    from itinerary_generation.copy.visit_context import DayVisitContext, build_day_visit_contexts

    assert tuple(copy_package.__all__) == EXPECTED_COPY_EXPORTS
    assert copy_package.DayVisitContext is DayVisitContext
    assert copy_package.build_day_visit_contexts is build_day_visit_contexts
    assert copy_package.client_activity_intro is client_activity_intro
    assert copy_package.client_group_tour_intro is client_group_tour_intro
