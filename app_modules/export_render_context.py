"""PDF render-context preparation for export workflow.

The pure helpers accept a session-like mapping so PDF export can be tested and
reasoned about without importing Streamlit. Small wrappers remain for the live
app surface.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import streamlit as st

from app_modules.itinerary_render_artifact import build_and_persist_itinerary_render_artifact
from app_modules.render_context_cache import get_cached_render_context
from images.app_image_selection import read_day_image_crop_focus


def pdf_render_context_for_state(state: MutableMapping[str, Any], signature: str):
    """Return the cached or canonically rebuilt render context for ``state``."""

    pdf_render_context = get_cached_render_context(state, signature=signature)
    if pdf_render_context is not None:
        return pdf_render_context

    output_edits = state.get("output_edits", {}) if isinstance(state.get("output_edits"), Mapping) else {}
    artifact = build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=state.get("parsed_rows", []) or [],
        output_edits=dict(output_edits),
        save_html=False,
        update_preview_state=False,
        cache_signature=signature,
    )
    return artifact.render_context


def pdf_render_context_for_signature(signature: str):
    """Return the cached or freshly-built render context for the live app state."""

    return pdf_render_context_for_state(st.session_state, signature)


def day_image_crop_focus_for_grouped_days(
    grouped_days: Mapping[str, object],
    output_edits: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Return PDF crop focus per day without mutating output edits."""

    if output_edits is None:
        output_edits = st.session_state.get("output_edits", {}) or {}
    return {
        str(day): read_day_image_crop_focus(output_edits, day)
        for day in (grouped_days or {})
    }


__all__ = [
    "day_image_crop_focus_for_grouped_days",
    "pdf_render_context_for_signature",
    "pdf_render_context_for_state",
]
