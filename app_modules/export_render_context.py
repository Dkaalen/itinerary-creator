"""PDF render-context preparation for export workflow."""

from __future__ import annotations

import streamlit as st

from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import get_cached_render_context, store_render_context
from images.app_image_selection import get_day_image_crop_focus
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import apply_output_edits


def pdf_render_context_for_signature(signature: str):
    """Return the cached or freshly-built render context for a PDF signature."""

    pdf_render_context = get_cached_render_context(st.session_state, signature=signature)
    if pdf_render_context is not None:
        return pdf_render_context

    edited_rows_for_pdf = apply_output_edits(
        st.session_state.get("parsed_rows", []) or [],
        st.session_state.get("output_edits", {}) or {},
    )
    grouped_days_for_pdf = group_rows_by_day(edited_rows_for_pdf)
    pdf_render_context = build_itinerary_render_context(
        edited_rows_for_pdf,
        grouped_days_for_pdf,
        st.session_state.get("output_edits", {}) or {},
    )
    store_render_context(st.session_state, signature=signature, context=pdf_render_context)
    return pdf_render_context


def day_image_crop_focus_for_grouped_days(grouped_days: dict) -> dict:
    return {
        day: get_day_image_crop_focus(st.session_state.get("output_edits", {}) or {}, day)
        for day in grouped_days
    }


__all__ = ["day_image_crop_focus_for_grouped_days", "pdf_render_context_for_signature"]
