"""Image-bank validation and image matching for PDF export."""

from __future__ import annotations

import json
from collections.abc import Mapping

import streamlit as st

from app_modules.export_pdf_artifacts import clear_pdf_artifact
from app_modules.image_bank_status_cache import get_cached_image_bank_status, store_image_bank_status
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.workflow_state import image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
    select_day_images_with_overrides,
)
from images.day_image_selection import normalize_day_image_matches
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract

PDF_IMAGE_CONTRACT_CACHE_KEY = "_pdf_image_contract_cache"


def _image_contract_signature(grouped_days: Mapping, required_destinations: list) -> str:
    payload = {
        "preview_signature": st.session_state.get("preview_signature") or "",
        "days": list((grouped_days or {}).keys()),
        "required_destinations": required_destinations,
        "day_images": (st.session_state.get("output_edits", {}) or {}).get("day_images", {}),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _cached_stage_image_matches(grouped_days: Mapping) -> dict:
    cached = st.session_state.get("day_image_matches")
    if not isinstance(cached, Mapping):
        return {}
    normalized = normalize_day_image_matches(cached)
    required_days = {str(day) for day in (grouped_days or {}).keys()}
    if not required_days or not required_days.issubset({str(day) for day in normalized.keys()}):
        return {}
    return dict(normalized)


def _select_image_matches_for_export(grouped_days: Mapping) -> dict:
    cached_stage_matches = _cached_stage_image_matches(grouped_days)
    if cached_stage_matches:
        return cached_stage_matches
    return select_day_images_with_overrides(
        grouped_days,
        st.session_state.get("output_edits", {}),
    )


def _read_cached_pdf_image_contract(signature: str) -> tuple[dict, dict] | None:
    cached = st.session_state.get(PDF_IMAGE_CONTRACT_CACHE_KEY)
    if not isinstance(cached, Mapping) or cached.get("signature") != signature:
        return None
    image_bank_status_payload = cached.get("image_bank_status")
    image_matches = cached.get("image_matches")
    if not isinstance(image_bank_status_payload, Mapping) or not isinstance(image_matches, Mapping):
        return None
    return dict(image_bank_status_payload), dict(image_matches)


def _store_pdf_image_contract(signature: str, image_bank_status_payload: Mapping, image_matches: Mapping) -> None:
    st.session_state[PDF_IMAGE_CONTRACT_CACHE_KEY] = {
        "signature": signature,
        "image_bank_status": dict(image_bank_status_payload or {}),
        "image_matches": dict(image_matches or {}),
    }


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
    )
    if grouped_days and not image_bank_is_ready_for_client_pictures(current_image_bank_status):
        current_image_bank_status = store_image_bank_status(
            st.session_state,
            required_destinations,
            connect_remote_image_bank_if_missing(required_destinations),
        )
    if not image_bank_is_ready_for_client_pictures(current_image_bank_status):
        clear_pdf_artifact("Image bank missing")
        st.error(current_image_bank_status.get("blocking_message") or "PDF export stopped because the real destination image bank is missing.")
        return False, current_image_bank_status, {}, grouped_days

    contract_signature = _image_contract_signature(grouped_days, required_destinations)
    cached_contract = _read_cached_pdf_image_contract(contract_signature)
    if cached_contract is not None:
        cached_status, cached_matches = cached_contract
        return True, cached_status, cached_matches, grouped_days

    selected_image_matches = _select_image_matches_for_export(grouped_days)
    preview_image_matches = day_image_matches_from_preview_html(st.session_state.get("itinerary_html", ""))
    image_matches = merge_preview_image_contract(selected_image_matches, preview_image_matches)
    current_image_bank_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
    )
    _store_pdf_image_contract(contract_signature, current_image_bank_status, image_matches)
    return True, current_image_bank_status, image_matches, grouped_days


__all__ = ["image_grouped_days", "prepare_pdf_image_contract"]
