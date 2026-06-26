"""Final-section source data preparation for itinerary render context."""

from __future__ import annotations

from typing import Any
import re

from app_modules.render_context_cover_data import _safe_label
from itinerary_generation.client_sanitizer import normalize_important_note_paragraphs, sanitize_client_list
from itinerary_generation.editable_draft import section_by_id
from itinerary_generation.inclusions import create_whats_included, create_whats_not_included
from ui.final_pages import create_optional_addons, get_important_travel_notes
from ui.inclusion_page_ownership import inclusion_pages_match_generated
from ui.inclusion_pages import render_inclusion_page_inner_htmls
from ui.render_helpers import text_to_list


def _plain_html_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", "\n", str(value or ""))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _looks_like_stale_generated_exclusion_html(value: Any) -> bool:
    text = _plain_html_text(value).casefold()
    if not text:
        return False
    lines = {line.strip() for line in text.splitlines()}
    return "accommodation" in lines or "self-arranged -" in text or "self arranged -" in text


def _typed_exclusion_html(typed_exclusions: dict[str, Any] | None) -> str:
    if not typed_exclusions:
        return ""
    typed_exclusion_html = typed_exclusions.get("content_html", "")
    if typed_exclusion_html or not typed_exclusions.get("pages"):
        return typed_exclusion_html
    first_page = typed_exclusions.get("pages", [{}])[0]
    return first_page.get("content_html", "") if isinstance(first_page, dict) else ""


def build_final_context_data(parsed_rows, grouped_days, output_edits: dict[str, Any], editor_draft: dict[str, Any], structured_document: Any) -> dict[str, Any]:
    """Build inclusion/exclusion/notes fields for render context."""

    manual_whats_included = sanitize_client_list(text_to_list(output_edits.get("whats_included_text", "")))
    whats_included = manual_whats_included or create_whats_included(parsed_rows, grouped_days)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = sanitize_client_list(text_to_list(output_edits.get("whats_not_included_text")))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)

    typed_inclusions = section_by_id(editor_draft, "whats_included")
    typed_exclusions = section_by_id(editor_draft, "whats_not_included")
    typed_notes = section_by_id(editor_draft, "important_travel_notes")
    generated_inclusion_pages = render_inclusion_page_inner_htmls(structured_document.inclusions)
    typed_inclusion_pages = [
        page.get("content_html", "")
        for page in typed_inclusions.get("pages", [])
        if isinstance(page, dict)
    ] if typed_inclusions else []
    typed_inclusion_pages_refreshable = inclusion_pages_match_generated(typed_inclusion_pages, generated_inclusion_pages)
    saved_inclusion_pages_refreshable = inclusion_pages_match_generated(
        output_edits.get("whats_included_pages_html"),
        generated_inclusion_pages,
    )
    final_section_titles = {
        "whats_included": _safe_label(typed_inclusions.get("title") if typed_inclusions else output_edits.get("whats_included_title"), "What’s included"),
        "whats_not_included": _safe_label(typed_exclusions.get("title") if typed_exclusions else output_edits.get("whats_not_included_title"), "What’s not included"),
        "important_travel_notes": _safe_label(typed_notes.get("title") if typed_notes else output_edits.get("important_travel_notes_title"), "Important travel notes"),
        "optional_experiences": _safe_label(output_edits.get("optional_experiences_title"), "Optional Experiences"),
    }

    return {
        "categorized_inclusions": structured_document.inclusions,
        "manual_whats_included": manual_whats_included,
        "whats_included": whats_included,
        "optional_addons": create_optional_addons(parsed_rows),
        "whats_not_included": whats_not_included,
        "structured_whats_not_included": structured_document.exclusions,
        "typed_inclusion_pages": [] if typed_inclusion_pages_refreshable else typed_inclusion_pages,
        "typed_inclusions_owned": bool(typed_inclusions) and not typed_inclusion_pages_refreshable,
        "saved_inclusion_pages_refreshable": bool(saved_inclusion_pages_refreshable),
        "typed_exclusion_html": "" if _looks_like_stale_generated_exclusion_html(_typed_exclusion_html(typed_exclusions)) else _typed_exclusion_html(typed_exclusions),
        "typed_exclusions_owned": bool(typed_exclusions) and not _looks_like_stale_generated_exclusion_html(_typed_exclusion_html(typed_exclusions)),
        "saved_exclusion_html_refreshable": _looks_like_stale_generated_exclusion_html(output_edits.get("whats_not_included_html")),
        "important_travel_notes": normalize_important_note_paragraphs(typed_notes.get("text") if typed_notes else get_important_travel_notes(output_edits, parsed_rows=parsed_rows)),
        "final_section_titles": final_section_titles,
    }


__all__ = ["build_final_context_data"]
