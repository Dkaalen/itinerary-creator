"""Legacy output-edits bridge for typed editable drafts."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.editable_draft_lookup import first_block_html, section_by_id
from itinerary_generation.editable_draft_normalize import _as_bool, _as_dict, _as_text, _page_html

def mirror_draft_to_legacy_output_edits(output_edits: dict[str, Any], editor_draft: Mapping[str, Any]) -> None:
    """Mirror typed draft values to legacy keys used by existing renderers.

    The typed ``editor_draft`` remains the preferred save contract.  The mirror
    lets preview/PDF/editor recovery continue to work until those layers are
    rewritten to consume typed draft fields directly.
    """

    if not isinstance(output_edits, dict) or not isinstance(editor_draft, Mapping):
        return

    output_edits["editor_draft"] = dict(editor_draft)

    for key, value in _as_dict(editor_draft.get("cover")).items():
        if key == "destinations_line":
            output_edits[key] = _as_text(value)
        else:
            output_edits[key] = _as_text(value).strip()

    summary = _as_dict(editor_draft.get("summary"))
    if isinstance(summary.get("trip_glance"), Mapping):
        output_edits["trip_glance"] = {str(key).strip(): _as_text(value).strip() for key, value in summary["trip_glance"].items() if str(key).strip()}
    if isinstance(summary.get("journey_arc"), list):
        output_edits["journey_arc"] = [dict(row) for row in summary["journey_arc"] if isinstance(row, Mapping)]

    days = output_edits.setdefault("days", {})
    for draft_day in editor_draft.get("days") or []:
        if not isinstance(draft_day, Mapping):
            continue
        day_id = _as_text(draft_day.get("day_id") or draft_day.get("day") or draft_day.get("label", "")).strip()
        if not day_id:
            continue
        day_edits = days.setdefault(day_id, {})
        for field in ("title", "city", "intro", "date"):
            if field in draft_day:
                day_edits[field] = _as_text(draft_day.get(field, "")).strip()
        for field in (
            "intro_generated_value",
            "intro_generator_version",
            "intro_source_signature",
            "blocks_html_generated_value",
            "blocks_html_generator_version",
        ):
            if field in draft_day:
                day_edits[field] = _as_text(draft_day.get(field, ""))
        for field in ("intro_manual_override", "blocks_manual_override"):
            if field in draft_day:
                day_edits[field] = _as_bool(draft_day.get(field, False))
        block_html = first_block_html(draft_day)
        if block_html is not None:
            day_edits["blocks_html"] = block_html

    included = section_by_id(editor_draft, "whats_included")
    if included:
        pages = included.get("pages") or []
        page_htmls = [_page_html(page) for page in pages if isinstance(page, Mapping) or page is not None]
        if page_htmls:
            output_edits["whats_included_pages_html"] = page_htmls
            output_edits["whats_included_html"] = ""
            output_edits["whats_included_text"] = _as_text(included.get("text", ""))
        elif "content_html" in included:
            output_edits["whats_included_html"] = _as_text(included.get("content_html", ""))
            output_edits.pop("whats_included_pages_html", None)
            output_edits["whats_included_text"] = _as_text(included.get("text", ""))

    excluded = section_by_id(editor_draft, "whats_not_included")
    if excluded:
        html = _as_text(excluded.get("content_html", ""))
        if not html and excluded.get("pages"):
            html = _page_html(excluded["pages"][0])
        if html:
            output_edits["whats_not_included_html"] = html
            output_edits["whats_not_included_text"] = ""
        elif "text" in excluded:
            output_edits["whats_not_included_text"] = _as_text(excluded.get("text", "")).strip()

    notes = section_by_id(editor_draft, "important_travel_notes")
    if notes:
        output_edits["important_travel_notes_text"] = _as_text(notes.get("text", "")).strip()

    workflow = _as_dict(editor_draft.get("workflow"))
    if "pictures_added" in workflow:
        # The Streamlit workflow state is the source of truth once picture review
        # has been activated. Older/stale editor payloads can still carry
        # workflow.pictures_added=false; those must not turn off pictures after
        # the user has clicked Add pictures. A positive editor value may still
        # promote the state for restored projects.
        editor_pictures_added = bool(workflow.get("pictures_added"))
        output_edits["pictures_added"] = bool(output_edits.get("pictures_added")) or editor_pictures_added

    issue_flags = [dict(flag) for flag in editor_draft.get("issue_flags") or [] if isinstance(flag, Mapping)]
    if issue_flags:
        output_edits["visual_editor_issue_flags"] = issue_flags

__all__ = ["mirror_draft_to_legacy_output_edits"]
