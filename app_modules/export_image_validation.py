"""Image-bank validation and image matching for PDF export."""

from __future__ import annotations

import streamlit as st

from app_modules.export_pdf_artifacts import clear_pdf_artifact
from app_modules.image_bank_status_cache import get_cached_image_bank_status, store_image_bank_status
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.workflow_state import image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
    image_bank_storage_signature,
    select_day_images_with_overrides,
)
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract


def image_grouped_days() -> dict:
    return image_grouped_days_from_state(st.session_state)


def prepare_pdf_image_contract() -> tuple[bool, dict, dict, dict]:
    """Validate image-bank readiness and return merged day-image matches."""

    grouped_days = image_grouped_days()
    required_destinations = destination_requests_from_rows(grouped_days)
    current_image_bank_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_storage_signature(),
    )
    if grouped_days and not current_image_bank_status.get(
        "required_destinations_ready",
        not current_image_bank_status.get("missing_full_bank"),
    ):
        current_image_bank_status = store_image_bank_status(
            st.session_state,
            required_destinations,
            connect_remote_image_bank_if_missing(required_destinations),
            bank_signature=image_bank_storage_signature(),
        )
    if not image_bank_is_ready_for_client_pictures(current_image_bank_status):
        clear_pdf_artifact("Image bank missing")
        st.error(current_image_bank_status.get("blocking_message") or "PDF export stopped because the real destination image bank is missing.")
        return False, current_image_bank_status, {}, grouped_days

    selected_image_matches = select_day_images_with_overrides(
        grouped_days,
        st.session_state.get("output_edits", {}),
    )
    preview_image_matches = day_image_matches_from_preview_html(st.session_state.get("itinerary_html", ""))
    image_matches = merge_preview_image_contract(selected_image_matches, preview_image_matches)
    current_image_bank_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_storage_signature(),
    )
    return True, current_image_bank_status, image_matches, grouped_days


__all__ = ["image_grouped_days", "prepare_pdf_image_contract"]
