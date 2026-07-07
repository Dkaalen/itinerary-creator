"""PDF render-context preparation for export workflow.

The pure helpers accept a session-like mapping so PDF export can be tested and
reasoned about without importing Streamlit.  Small wrappers remain for the live
app surface.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import streamlit as st

from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import get_cached_render_context, store_render_context
from images.app_image_selection import read_day_image_crop_focus
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import apply_output_edits


def pdf_render_context_for_state(state: MutableMapping[str, Any], signature: str):
    """Return the cached or freshly-built render context for ``state``."""

    pdf_render_context = get_cached_render_context(state, signature=signature)
    if pdf_render_context is not None:
        return pdf_render_context

    output_edits = state.get("output_edits", {}) if isinstance(state.get("output_edits"), Mapping) else {}
    edited_rows_for_pdf = apply_output_edits(state.get("parsed_rows", []) or [], output_edits)
    grouped_days_for_pdf = group_rows_by_day(edited_rows_for_pdf)
    pdf_render_context = build_itinerary_render_context(
        edited_rows_for_pdf,
        grouped_days_for_pdf,
        output_edits,
    )
    store_render_context(state, signature=signature, context=pdf_render_context)
    return pdf_render_context


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
