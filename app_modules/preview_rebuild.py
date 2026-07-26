"""Preview HTML rebuild service for the current editable itinerary."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_render_artifact import build_and_persist_itinerary_render_artifact
from app_modules.render_lifecycle import mark_pdf_dirty as mark_pdf_dirty_state
from ui.export_files import save_html_file
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

    previous_html = state.get("itinerary_html", "")
    artifact = build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=parsed_rows,
        output_edits=output_edits,
        save_html=save_html,
    )
    html_changed = artifact.html != previous_html

    if mark_pdf_dirty and html_changed:
        mark_pdf_dirty_state(state, status="Needs refresh")
    return True
