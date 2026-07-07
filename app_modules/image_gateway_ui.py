from __future__ import annotations

import streamlit as st

from app_modules.debug_mode import is_debug_mode
from app_modules.image_bank_readiness import image_bank_readiness_label, image_bank_readiness_message, image_bank_repair_message
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.image_bank_status_cache import (
    clear_image_bank_status_cache,
    get_cached_image_bank_status,
    store_image_bank_status,
)
from app_modules.workflow_actions import retry_image_bank_connection
from app_modules.workflow_state import image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
)
from images.scanner import invalidate_image_bank_cache


def _current_image_bank_requests():
    return destination_requests_from_rows(image_grouped_days_from_state(st.session_state))

def _current_image_bank_status() -> dict:
    requests = _current_image_bank_requests()
    return get_cached_image_bank_status(
        st.session_state,
        requests,
        image_bank_status,
    )

def _connect_current_image_bank() -> dict:
    requests = _current_image_bank_requests()
    clear_image_bank_status_cache(st.session_state)
    invalidate_image_bank_cache()
    status = connect_remote_image_bank_if_missing(requests)
    clear_image_bank_status_cache(st.session_state)
    return store_image_bank_status(
        st.session_state,
        requests,
        status,
    )

def _image_status_notice() -> None:
    status = _current_image_bank_status()
    label = image_bank_readiness_label(status)
    message = image_bank_readiness_message(status)
    if label == "Destination images ready":
        st.success(message)
        return
    if label == "Fallback images available":
        st.warning(message)
        if st.button("Retry destination image-bank connection", key="retry_destination_image_bank_from_fallback", use_container_width=True):
            with st.spinner("Preparing destination images…"):
                retry = retry_image_bank_connection(st.session_state, _current_image_bank_status, _connect_current_image_bank)
            if retry.ok:
                st.success("Destination images are ready. Click Add pictures again to refresh image matches.")
            st.rerun()
        return
    st.error(message)
    st.caption("Prepare the destination image bank or fallback images before picture review.")

def _image_bank_gateway_is_blocking(result: dict | None) -> bool:
    if not isinstance(result, dict) or not result or result.get("ready"):
        return False
    status = result.get("status") if isinstance(result.get("status"), dict) else None
    return not image_bank_is_ready_for_client_pictures(status)

def _render_image_bank_gateway_repair(result: dict | None = None) -> None:
    result = result or st.session_state.get("image_bank_gateway") or {}
    status = result.get("status") if isinstance(result.get("status"), dict) else _current_image_bank_status()
    setup_status = result.get("setup_status") if isinstance(result.get("setup_status"), dict) else status.get("setup_status", {})
    message = image_bank_repair_message(status)

    st.html(
        '<div class="image-bank-repair-panel">'
        '<strong>Image source required</strong>'
        '<span>Destination images are prepared before picture review. If they are unavailable, fallback images can still keep review moving.</span>'
        '</div>'
    )
    st.error(message)
    if is_debug_mode(st.session_state):
        st.caption("Expected source: Dkaalen/itinerary-image-bank/image_bank_full. Bundled fallback pictures are allowed for review when available.")

    if is_debug_mode(st.session_state) and setup_status and (setup_status.get("error") or setup_status.get("git_error") or setup_status.get("code")):
        with st.expander("Image-bank setup details", expanded=False):
            st.json({
                "code": setup_status.get("code", ""),
                "method": setup_status.get("method", ""),
                "repo_url": setup_status.get("repo_url", status.get("repo_url", "")),
                "manifest_url": setup_status.get("manifest_url", status.get("manifest_url", "")),
                "zip_url": setup_status.get("zip_url", status.get("zip_url", "")),
                "error": setup_status.get("error", ""),
                "git_error": setup_status.get("git_error", ""),
                "requested_destinations": setup_status.get("requested_destinations", status.get("required_destinations", [])),
                "installed_destinations": setup_status.get("installed_destinations", []),
                "unresolved_destinations": setup_status.get("unresolved_destinations", []),
                "download_errors": setup_status.get("errors", []),
                "paths": status.get("paths", []),
            })

    if st.button("Retry image-bank connection", use_container_width=True):
        with st.spinner("Preparing the required destination image packs…"):
            retry = retry_image_bank_connection(st.session_state, _current_image_bank_status, _connect_current_image_bank)
        if retry.ok:
            st.success("Destination images are ready. Click Add pictures again to select images.")
        st.rerun()
