"""Build visual editor payloads from itinerary state.

The payload contract remains owned here, while focused helper modules keep the
cover, summary, days, final pages, images, source rows, and warnings logic small.
"""

from app_modules.display_settings import get_color_preset
from app_modules.output_brand import editor_brand_payload, output_brand_id
from app_modules.output_brand_cover import apply_output_brand_cover_palette
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.editable_draft import normalise_editable_draft
from itinerary_generation.editor_page_contract import build_editor_document_pages
from ui.picture_workflow import pictures_are_added
from visual_editor_component.editor_payload_days import build_payload_days
from visual_editor_component.editor_payload_final_pages import (
    _build_generated_exclusions_html,
    _build_generated_inclusion_page_htmls,
    _build_generated_inclusion_sections,
    _build_generated_inclusions_html,
    build_final_pages_payload,
)
from visual_editor_component.editor_payload_images import (
    _editor_cover_image_payload,
    build_cover_image_payloads,
    build_day_image_context,
)
from visual_editor_component.editor_payload_sections import (
    build_cover_payload,
    build_generated_values,
    build_summary_payload,
)
from visual_editor_component.editor_payload_sources import (
    _generated_value_for_page_html,
    _page_html_payload,
    _source_rows_payload,
    _source_signature,
)
from visual_editor_component.editor_payload_summary import (
    _get_journey_arc,
    _get_trip_glance,
    _merge_trip_glance,
    _normalise_journey_arc,
)
from visual_editor_component.editor_payload_warnings import (
    _client_output_warnings_for_payload,
    _compact_model_warnings,
)
from visual_editor_component.editor_status import persistent_draft_status

# Migration breadcrumbs for older static tests while payload image logic lives in
# editor_payload_images.py: _editor_cover_image_payload;
# image["data_uri"] = get_image_preview_for_path; limit=12.


def _stored_editor_draft(output_edits):
    stored = (output_edits or {}).get("editor_draft") if isinstance(output_edits, dict) else {}
    return stored if isinstance(stored, dict) else {}


def _append_payload_warnings(payload, model_warnings, image_warnings):
    output_warnings = _client_output_warnings_for_payload(payload)
    for warning in model_warnings:
        output_warnings.append({
            "code": warning.get("code", "model_warning"),
            "severity": warning.get("severity", "review"),
            "category": warning.get("category", "model"),
            "excerpt": warning.get("message", "Structured model warning"),
            "message": warning.get("message", "Structured model warning"),
            "page_label": warning.get("page_label", "Structured itinerary"),
            "page_id": warning.get("page_id", ""),
            "source_row_ids": warning.get("source_row_ids", []),
        })
    for warning in image_warnings:
        output_warnings.append({
            "code": warning.code,
            "severity": "critical" if getattr(warning, "severity", "") == "error" else "review",
            "category": "image",
            "message": warning.message,
            "excerpt": warning.message,
            "page_label": getattr(warning, "day", "Image review"),
        })
    payload["client_output_warnings"] = output_warnings[:30]
    return payload


def build_visual_editor_payload(parsed_rows, grouped_days, output_edits):
    """Build the editable A4-page payload used by the visual editor component."""
    output_edits = output_edits or {}
    pictures_added = pictures_are_added(output_edits)
    image_matches, image_warnings, image_warnings_by_day = build_day_image_context(
        grouped_days,
        output_edits,
        pictures_added=pictures_added,
    )
    stored_editor_draft = _stored_editor_draft(output_edits)
    payload_days, generated_days_values = build_payload_days(
        grouped_days,
        output_edits,
        stored_editor_draft,
        pictures_added=pictures_added,
        image_matches=image_matches,
        image_warnings_by_day=image_warnings_by_day,
    )

    final_pages_bundle = build_final_pages_payload(parsed_rows, grouped_days, output_edits, stored_editor_draft)
    model_warnings = _compact_model_warnings(final_pages_bundle["structured_document"], parsed_rows)

    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=False)
    cover_theme = apply_output_brand_cover_palette(cover_theme, output_brand_id(output_edits))
    cover_image, summary_image = build_cover_image_payloads(parsed_rows, output_edits, pictures_added=pictures_added)
    cover_theme["background_path"] = cover_image.get("path", "")
    cover_theme["background_data_uri"] = cover_image.get("data_uri", "")
    cover_theme["background_crop_focus"] = cover_image.get("crop_focus", "top")
    typed_cover = stored_editor_draft.get("cover", {}) if isinstance(stored_editor_draft.get("cover"), dict) else {}
    typed_summary = stored_editor_draft.get("summary", {}) if isinstance(stored_editor_draft.get("summary"), dict) else {}

    payload = {
        "draft_id": output_edits.get("draft_id", ""),
        "brand": editor_brand_payload(output_edits, get_color_preset(output_edits)),
        "meta": {
            "draft_schema_version": 3,
            "source_signature": _source_signature(parsed_rows, grouped_days),
            "day_count": len(payload_days),
        },
        "cover": build_cover_payload(
            parsed_rows,
            grouped_days,
            output_edits,
            typed_cover,
            cover_theme,
            cover_image,
            summary_image,
        ),
        "summary": build_summary_payload(parsed_rows, grouped_days, output_edits, typed_summary),
        "days": payload_days,
        "final_pages": final_pages_bundle["final_pages"],
        "issue_flags": output_edits.get("visual_editor_issue_flags", []),
        "workflow": {"pictures_added": pictures_added},
        "model_warnings": model_warnings,
        "autosave_status": persistent_draft_status(),
    }
    payload["source_rows"] = _source_rows_payload(parsed_rows)
    payload["generated_values"] = build_generated_values(
        parsed_rows,
        grouped_days,
        generated_days_values,
        final_pages_bundle["generated_values"],
    )
    payload["document_pages"] = build_editor_document_pages(
        payload=payload,
        grouped_days=grouped_days,
        existing_pages=stored_editor_draft.get("document_pages"),
    )
    payload["editor_draft"] = normalise_editable_draft(payload)
    _append_payload_warnings(payload, model_warnings, image_warnings)
    return payload
