"""Preview HTML rebuild service for the current editable itinerary."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import store_render_context
from app_modules.workflow_state import mark_pdf_dirty as mark_pdf_dirty_state
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits
from ui.render_cache import make_render_signature


def rebuild_current_preview_for_state(
    state: MutableMapping[str, Any],
    *,
    mark_pdf_dirty: bool = True,
    force: bool = False,
    save_html: bool = True,
) -> bool:
    """Ensure preview/HTML matches the current editable project state."""

    parsed_rows = state.get("parsed_rows", [])
    output_edits = state.get("output_edits", {})

    if not parsed_rows or not output_edits:
        return False

    render_signature = make_render_signature(parsed_rows, output_edits)
    cached_signature = state.get("preview_signature")
    has_html = bool(state.get("itinerary_html", ""))

    if not force and has_html and cached_signature == render_signature:
        if save_html and not state.get("html_path"):
            state["html_path"] = save_html_file(state["itinerary_html"])
        return True

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    rebuilt_html = build_itinerary_html_from_context(render_context)

    html_changed = rebuilt_html != state.get("itinerary_html", "")
    state["itinerary_html"] = rebuilt_html
    state["preview_signature"] = render_signature
    store_render_context(state, signature=render_signature, context=render_context)

    if mark_pdf_dirty and html_changed:
        mark_pdf_dirty_state(state, status="Needs refresh")

    if save_html:
        state["html_path"] = save_html_file(state["itinerary_html"])
    return True
