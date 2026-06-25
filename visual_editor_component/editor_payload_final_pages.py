"""Final-section payload helpers for the visual editor."""

from itinerary_generation.editable_draft import section_by_id
from itinerary_generation.inclusions import create_whats_not_included
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_html_audit import validate_source_aware_html_coverage
from ui.day_pages import render_inclusion_page_inner_htmls, render_inclusion_sections_inner_html
from ui.inclusion_page_ownership import inclusion_pages_match_generated
from ui.render_helpers import list_to_text, text_to_list
from ui.premium_final_notes import render_premium_notes_inner_html
from visual_editor_component.editor_payload_sources import _generated_value_for_page_html, _page_html_payload


def _build_generated_inclusion_sections(parsed_rows, grouped_days):
    return build_itinerary_document(parsed_rows, grouped_days).inclusions


def _build_generated_inclusions_html(parsed_rows, grouped_days):
    return render_inclusion_sections_inner_html(_build_generated_inclusion_sections(parsed_rows, grouped_days))


def _build_generated_inclusion_page_htmls(parsed_rows, grouped_days):
    return render_inclusion_page_inner_htmls(_build_generated_inclusion_sections(parsed_rows, grouped_days))


def _build_generated_exclusions_html(parsed_rows, grouped_days=None):
    return render_inclusion_sections_inner_html(build_itinerary_document(parsed_rows, grouped_days).exclusions)


def build_final_pages_payload(parsed_rows, grouped_days, output_edits, stored_editor_draft):
    structured_document = build_itinerary_document(parsed_rows, grouped_days)
    generated_inclusions_html = render_inclusion_sections_inner_html(structured_document.inclusions)
    generated_inclusion_page_htmls = render_inclusion_page_inner_htmls(structured_document.inclusions)
    typed_inclusions = section_by_id(stored_editor_draft, "whats_included")
    typed_exclusions = section_by_id(stored_editor_draft, "whats_not_included")
    typed_notes = section_by_id(stored_editor_draft, "important_travel_notes")
    typed_inclusion_pages = [
        page.get("content_html", "")
        for page in typed_inclusions.get("pages", [])
        if isinstance(page, dict)
    ] if typed_inclusions else []
    generated_page_htmls = generated_inclusion_page_htmls
    typed_pages_are_refreshable = inclusion_pages_match_generated(typed_inclusion_pages, generated_page_htmls)
    saved_output_pages = output_edits.get("whats_included_pages_html")
    saved_output_pages_are_refreshable = inclusion_pages_match_generated(saved_output_pages, generated_page_htmls)
    saved_inclusion_page_htmls = (
        [] if typed_pages_are_refreshable else typed_inclusion_pages
    ) or (
        [] if saved_output_pages_are_refreshable else saved_output_pages
    )
    saved_exclusions_html = typed_exclusions.get("content_html") if typed_exclusions else output_edits.get("whats_not_included_html")
    if typed_exclusions and not saved_exclusions_html and typed_exclusions.get("pages"):
        first_page = typed_exclusions.get("pages", [{}])[0]
        saved_exclusions_html = first_page.get("content_html", "") if isinstance(first_page, dict) else ""
    effective_inclusion_page_htmls = _page_html_payload(saved_inclusion_page_htmls or generated_inclusion_page_htmls)
    generated_whats_not_included_text = list_to_text(create_whats_not_included(parsed_rows))
    generated_whats_not_included_html = render_inclusion_sections_inner_html(structured_document.exclusions)
    effective_exclusions_html = saved_exclusions_html or generated_whats_not_included_html
    final_page_source_warnings = (
        *validate_source_aware_html_coverage(
            html_fragments=effective_inclusion_page_htmls,
            sections=structured_document.inclusions,
            page_name="What's included",
            warning_code="edited_inclusions_missing_source_identity",
        ),
        *validate_source_aware_html_coverage(
            html_fragments=effective_exclusions_html,
            sections=structured_document.exclusions,
            page_name="What's not included",
            warning_code="edited_exclusions_missing_source_identity",
        ),
    )
    structured_document.warnings = tuple((*structured_document.warnings, *final_page_source_warnings))
    important_notes_text = typed_notes.get("text") if typed_notes else output_edits.get("important_travel_notes_text", "")
    important_notes_html = render_premium_notes_inner_html(text_to_list(important_notes_text))

    return {
        "structured_document": structured_document,
        "typed_inclusions": typed_inclusions,
        "typed_exclusions": typed_exclusions,
        "typed_notes": typed_notes,
        "final_pages": {
            "whats_included_title": typed_inclusions.get("title") if typed_inclusions else output_edits.get("whats_included_title", "What’s included"),
            "whats_not_included_title": typed_exclusions.get("title") if typed_exclusions else output_edits.get("whats_not_included_title", "What’s not included"),
            "important_travel_notes_title": typed_notes.get("title") if typed_notes else output_edits.get("important_travel_notes_title", "Important travel notes"),
            "whats_included_html": output_edits.get("whats_included_html") or generated_inclusions_html,
            "whats_included_pages_html": effective_inclusion_page_htmls,
            "whats_included_text": output_edits.get("whats_included_text", ""),
            "whats_not_included_html": effective_exclusions_html,
            "whats_not_included_text": output_edits.get("whats_not_included_text") or generated_whats_not_included_text,
            "important_travel_notes_text": important_notes_text,
            "important_travel_notes_html": important_notes_html,
        },
        "generated_values": {
            "whats_included_title": "What’s included",
            "whats_not_included_title": "What’s not included",
            "important_travel_notes_title": "Important travel notes",
            "whats_included_html": generated_inclusions_html,
            "whats_included_pages_html": [
                {"html": _generated_value_for_page_html(page)} for page in generated_inclusion_page_htmls
            ],
            "whats_not_included_html": generated_whats_not_included_html,
            "whats_not_included_text": generated_whats_not_included_text,
            "important_travel_notes_text": "",
            "important_travel_notes_html": "",
        },
    }
