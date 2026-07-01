from __future__ import annotations

import streamlit as st

from app_modules.debug_mode import is_debug_mode
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.image_bank_status_cache import get_cached_image_bank_status, store_image_bank_status
from app_modules.workflow_actions import retry_image_bank_connection
from app_modules.workflow_state import image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    destination_requests_from_rows,
    image_bank_status,
)


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
    status = connect_remote_image_bank_if_missing(requests)
    return store_image_bank_status(
        st.session_state,
        requests,
        status,
    )

def _image_status_notice() -> None:
    status = _current_image_bank_status()
    if status.get("full_bank_found"):
        covered = len(status.get("covered_destinations", []))
        required = len(status.get("required_destinations", []))
        suffix = f" across {covered}/{required} itinerary destinations" if required else ""
        if status.get("missing_destinations"):
            st.warning(f"Image bank connected: {status.get('destination_image_count', 0)} destination pictures available{suffix}. Some route or destination-specific packs are missing, so fallback images may be used.")
        else:
            st.success(f"Image bank connected: {status.get('destination_image_count', 0)} destination pictures available{suffix}.")
    elif status.get("default_image_count") or status.get("total_image_count"):
        st.warning("Using bundled fallback pictures. You can still review and export the itinerary, then replace images when the full destination bank is available.")
    else:
        st.error(status.get("blocking_message") or "No usable itinerary images are available.")
        st.caption("Connect the destination image bank or add bundled fallback images before picture review.")

def _image_bank_gateway_is_blocking(result: dict | None) -> bool:
    if not isinstance(result, dict) or not result or result.get("ready"):
        return False
    status = result.get("status") if isinstance(result.get("status"), dict) else None
    return not image_bank_is_ready_for_client_pictures(status)

def _render_image_bank_gateway_repair(result: dict | None = None) -> None:
    result = result or st.session_state.get("image_bank_gateway") or {}
    status = result.get("status") if isinstance(result.get("status"), dict) else _current_image_bank_status()
    setup_status = result.get("setup_status") if isinstance(result.get("setup_status"), dict) else status.get("setup_status", {})
    message = result.get("message") or status.get("blocking_message") or "Full destination image bank is missing."

    st.html(
        '<div class="image-bank-repair-panel">'
        '<strong>Image source required</strong>'
        '<span>Add Pictures could not find destination or bundled fallback images. Connect the image bank or add fallback images first.</span>'
        '</div>'
    )
    st.error(message)
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
            st.success("Image bank connected. Click Add pictures again to select destination images.")
        st.rerun()
