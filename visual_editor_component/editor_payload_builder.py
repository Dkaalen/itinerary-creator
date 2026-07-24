"""Build visual editor payloads from itinerary state.

The payload contract remains owned here, while focused helper modules keep the
cover, summary, days, final pages, images, source rows, and warnings logic small.
"""

from app_modules.display_settings import get_color_preset
from app_modules.itinerary_render_artifact import build_itinerary_render_artifact
from app_modules.output_brand import editor_brand_payload, output_brand_id
from app_modules.output_brand_cover import apply_output_brand_cover_palette
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.editable_draft import normalise_editable_draft
from itinerary_generation.editor_page_contract import build_editor_document_pages
from ui.picture_workflow import pictures_are_added
from visual_editor_component.editor_payload_final_pages import (
    _build_generated_exclusions_html,
    _build_generated_inclusion_page_htmls,
    _build_generated_inclusion_sections,
    _build_generated_inclusions_html,
)
from visual_editor_component.editor_render_document_adapter import (
    build_cover_payload_from_render_document,
    build_day_payloads_from_render_document,
    build_final_pages_payload_from_render_document,
    build_generated_values_from_render_context,
    build_summary_payload_from_render_document,
)
from visual_editor_component.editor_payload_images import (
    _editor_cover_image_payload,
    build_editor_image_payload_bundle,
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


def build_visual_editor_payload(parsed_rows, grouped_days, output_edits, *, render_context=None):
    """Build the editor payload by adapting the canonical RenderDocument."""

    output_edits = output_edits or {}
    if render_context is None:
        render_context = build_itinerary_render_artifact(parsed_rows or [], output_edits).render_context

    authoritative_rows = list(render_context.parsed_rows or [])
    authoritative_grouped_days = render_context.grouped_days or {}
    render_document = getattr(render_context, "editor_render_document", None) or render_context.render_document
    pictures_added = pictures_are_added(output_edits)
    image_payload_bundle = build_editor_image_payload_bundle(
        authoritative_rows,
        authoritative_grouped_days,
        output_edits,
        pictures_added=pictures_added,
    )
    stored_editor_draft = _stored_editor_draft(output_edits)
    payload_days, generated_days_values = build_day_payloads_from_render_document(
        render_document,
        stored_editor_draft,
        day_images=image_payload_bundle["day_images"],
    )
    final_pages = build_final_pages_payload_from_render_document(render_document)
    model_warnings = _compact_model_warnings(render_context.structured_document, authoritative_rows)

    cover_image = image_payload_bundle["cover_image"]
    summary_image = image_payload_bundle["summary_image"]
    payload = {
        "draft_id": output_edits.get("draft_id", ""),
        "brand": editor_brand_payload(output_edits, get_color_preset(output_edits)),
        "meta": {
            "draft_schema_version": 3,
            "source_signature": _source_signature(authoritative_rows, authoritative_grouped_days),
            "day_count": len(payload_days),
            "content_authority": "render_document",
        },
        "cover": build_cover_payload_from_render_document(
            render_document,
            cover_theme=render_context.cover_theme,
            cover_image=cover_image,
            summary_image=summary_image,
        ),
        "summary": build_summary_payload_from_render_document(render_document),
        "days": payload_days,
        "final_pages": final_pages,
        "issue_flags": output_edits.get("visual_editor_issue_flags", []),
        "workflow": {"pictures_added": pictures_added},
        "model_warnings": model_warnings,
        "autosave_status": persistent_draft_status(),
    }
    payload["source_rows"] = _source_rows_payload(authoritative_rows)
    payload["generated_values"] = build_generated_values_from_render_context(
        render_context,
        generated_days_values,
    )
    payload["document_pages"] = build_editor_document_pages(
        payload=payload,
        grouped_days=authoritative_grouped_days,
        existing_pages=stored_editor_draft.get("document_pages"),
    )
    payload["editor_draft"] = normalise_editable_draft(payload)
    _append_payload_warnings(payload, model_warnings, image_payload_bundle["image_warnings"])
    return payload
