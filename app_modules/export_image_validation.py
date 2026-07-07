"""Image-bank validation and image matching for PDF export."""

from __future__ import annotations

import json
from collections.abc import Mapping

import streamlit as st

from app_modules.export_pdf_artifacts import clear_pdf_artifact
from app_modules.image_bank_status_cache import (
    clear_image_bank_status_cache,
    get_cached_image_bank_status,
    image_bank_storage_signature_from_status,
    store_image_bank_status,
)
from app_modules.image_gateway import (
    image_bank_is_ready_for_client_pictures,
    image_bank_should_attempt_destination_connection,
)
from app_modules.workflow_state import image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
    image_bank_storage_signature,
    select_day_images_with_overrides,
)
from images.day_image_selection import normalize_day_image_matches
from images.image_overrides import normalize_image_mode
from images.scanner import invalidate_image_bank_cache
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract

PDF_IMAGE_CONTRACT_CACHE_KEY = "_pdf_image_contract_cache"


def _normalized_day_image_overrides_for_signature() -> dict:
    normalized = {}
    for day, choice in (_day_image_overrides() or {}).items():
        if not isinstance(choice, Mapping):
            continue
        mode = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
        normalized[str(day)] = {
            "mode": mode,
            "path": "" if mode == "none" else str(choice.get("path") or ""),
            "crop_focus": str(choice.get("crop_focus") or "top"),
        }
    return normalized


def _explicitly_removed_days() -> frozenset[str]:
    removed = []
    for day, choice in (_day_image_overrides() or {}).items():
        if not isinstance(choice, Mapping):
            continue
        if normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", "")) == "none":
            removed.append(str(day))
    return frozenset(removed)


def _image_contract_signature(grouped_days: Mapping, required_destinations: list, image_bank_signature: str = "") -> str:
    payload = {
        "preview_signature": st.session_state.get("preview_signature") or "",
        "days": list((grouped_days or {}).keys()),
        "required_destinations": required_destinations,
        "image_bank_signature": image_bank_signature,
        "day_images": _normalized_day_image_overrides_for_signature(),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _day_image_overrides() -> Mapping:
    output_edits = st.session_state.get("output_edits", {}) or {}
    return output_edits.get("day_images", {}) if isinstance(output_edits, Mapping) else {}


def _overrides_require_fresh_selection(overrides: Mapping | None) -> bool:
    for choice in (overrides or {}).values():
        if not isinstance(choice, Mapping):
            continue
        mode = normalize_image_mode(choice.get("mode"), removed=choice.get("removed", False), path=choice.get("path", ""))
        if mode in {"manual", "none"} or choice.get("crop_focus"):
            return True
    return False


def _cached_stage_image_matches(grouped_days: Mapping) -> dict:
    if _overrides_require_fresh_selection(_day_image_overrides()):
        return {}
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
    image_bank_signature = image_bank_storage_signature()
    current_image_bank_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_signature,
    )
    if grouped_days and image_bank_should_attempt_destination_connection(current_image_bank_status):
        clear_image_bank_status_cache(st.session_state)
        invalidate_image_bank_cache()
        current_image_bank_status = store_image_bank_status(
            st.session_state,
            required_destinations,
            connect_remote_image_bank_if_missing(required_destinations),
            bank_signature=image_bank_storage_signature(),
        )
        invalidate_image_bank_cache()
        image_bank_signature = image_bank_storage_signature()
    if not image_bank_is_ready_for_client_pictures(current_image_bank_status):
        clear_pdf_artifact("Image bank missing")
        st.error(current_image_bank_status.get("blocking_message") or "PDF export stopped because the real destination image bank is missing.")
        return False, current_image_bank_status, {}, grouped_days

    status_signature = image_bank_storage_signature_from_status(current_image_bank_status)
    contract_signature = _image_contract_signature(grouped_days, required_destinations, f"{image_bank_signature}|{status_signature}")
    cached_contract = _read_cached_pdf_image_contract(contract_signature)
    if cached_contract is not None:
        cached_status, cached_matches = cached_contract
        return True, cached_status, cached_matches, grouped_days

    selected_image_matches = _select_image_matches_for_export(grouped_days)
    preview_image_matches = day_image_matches_from_preview_html(st.session_state.get("itinerary_html", ""))
    image_matches = merge_preview_image_contract(
        selected_image_matches,
        preview_image_matches,
        removed_days=_explicitly_removed_days(),
    )
    current_image_bank_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_signature,
    )
    _store_pdf_image_contract(contract_signature, current_image_bank_status, image_matches)
    return True, current_image_bank_status, image_matches, grouped_days


__all__ = ["image_grouped_days", "prepare_pdf_image_contract"]
