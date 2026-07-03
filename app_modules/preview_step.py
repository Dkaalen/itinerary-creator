from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_REQUEST_KEY,
    add_pictures_editor_commit_elapsed_seconds,
    add_pictures_editor_commit_ready,
    add_pictures_editor_commit_timed_out,
    clear_add_pictures_editor_commit_request,
    request_add_pictures_editor_commit,
)
from app_modules.image_gateway_ui import (
    _connect_current_image_bank,
    _current_image_bank_status,
    _image_bank_gateway_is_blocking,
    _render_image_bank_gateway_repair,
)
from app_modules.input_step import _render_generation_messages
from app_modules.project_io import rebuild_current_preview
from app_modules.workflow_actions import enter_picture_stage
from app_modules.workflow_config import STAGE_COPY
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits, mark_output_dirty
from ui.render_cache import make_render_signature
from visual_editor_component.editor_workflow import render_visual_editor
from images.app_image_selection import audit_day_image_matches, select_day_images_with_overrides


def _render_document_editor(*, pictures_active: bool) -> None:
    if not (st.session_state.get("parsed_rows") and st.session_state.get("output_edits")):
        return

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)

    editor_applied = render_visual_editor(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
        rebuild_preview=rebuild_current_preview,
        mark_dirty=mark_output_dirty,
    )
    if editor_applied:
        return

    render_signature = make_render_signature(st.session_state.parsed_rows, st.session_state.output_edits)
    preview_is_current = (
        bool(st.session_state.get("itinerary_html", ""))
        and st.session_state.get("preview_signature") == render_signature
    )
    if not preview_is_current:
        rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)
    elif not st.session_state.get("html_path"):
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

def _activate_picture_stage() -> bool:
    result = enter_picture_stage(
        st.session_state,
        status_func=_current_image_bank_status,
        connect_func=_connect_current_image_bank,
        select_images_func=select_day_images_with_overrides,
        audit_images_func=audit_day_image_matches,
        rebuild_preview_func=rebuild_current_preview,
    )
    if result.ok:
        st.session_state.pop("add_pictures_last_error", None)
        st.session_state["add_pictures_last_message"] = result.message
    else:
        st.session_state["add_pictures_last_error"] = result.message or "Add Pictures could not start."
    return result.ok

def _add_pictures_apply_ready() -> bool:
    return add_pictures_editor_commit_ready(st.session_state)

def _add_pictures_apply_pending() -> bool:
    return bool(st.session_state.get(ADD_PICTURES_COMMIT_REQUEST_KEY)) and not _add_pictures_apply_ready()

def render_edit_page(app_version: str) -> None:
    _render_app_header(app_version, stage="edit")
    _render_generation_messages()
    _render_stage_actions("edit")
    _stage_panel(STAGE_COPY["edit"]["panel_title"], STAGE_COPY["edit"]["panel_text"])

    was_waiting_for_apply = _add_pictures_apply_pending()
    if not _add_pictures_apply_ready():
        _render_document_editor(pictures_active=False)
        if was_waiting_for_apply and _add_pictures_apply_ready():
            st.rerun()

    st.html('<div class="bottom-cta"><div><strong>Text ready?</strong><span>Apply the current preview changes, then add destination pictures from the committed itinerary.</span></div></div>')
    last_error = st.session_state.get("add_pictures_last_error")
    if last_error:
        st.error(str(last_error))
        st.caption("Retry Add Pictures after fixing the issue, or continue editing and apply changes again.")
    gateway_result = st.session_state.get("image_bank_gateway")
    if _image_bank_gateway_is_blocking(gateway_result):
        _render_image_bank_gateway_repair(gateway_result)
        return

    apply_ready = _add_pictures_apply_ready()
    apply_pending = _add_pictures_apply_pending()

    if apply_ready:
        st.success("Changes applied. Add pictures is ready to run from the committed itinerary.")
        left, right = st.columns(2)
        with left:
            if st.button("Edit again", use_container_width=True):
                clear_add_pictures_editor_commit_request(st.session_state)
                st.rerun()
        with right:
            if st.button("Add pictures", type="primary", use_container_width=True):
                with st.spinner("Preparing destination pictures and finding the best matches…"):
                    _activate_picture_stage()
                st.rerun()
        return

    if apply_pending:
        if add_pictures_editor_commit_timed_out(st.session_state):
            waited = int(add_pictures_editor_commit_elapsed_seconds(st.session_state))
            st.warning(f"The editor has not returned the latest changes after {waited} seconds.")
            st.caption("This usually means the browser editor did not answer the save request. You can retry, continue from the last saved version, or cancel and keep editing.")
            retry_col, saved_col, cancel_col = st.columns(3)
            with retry_col:
                if st.button("Retry save", type="primary", use_container_width=True, key="retry_add_pictures_editor_commit"):
                    request_add_pictures_editor_commit(st.session_state)
                    st.rerun()
            with saved_col:
                if st.button("Add pictures from last saved version", use_container_width=True, key="fallback_add_pictures_after_timeout"):
                    clear_add_pictures_editor_commit_request(st.session_state)
                    with st.spinner("Preparing destination image packs and finding the best matches…"):
                        _activate_picture_stage()
                    st.rerun()
            with cancel_col:
                if st.button("Cancel", use_container_width=True, key="cancel_add_pictures_editor_commit"):
                    clear_add_pictures_editor_commit_request(st.session_state)
                    st.rerun()
        else:
            st.info("Saving the latest editor changes before adding pictures…")
            st.button("Add pictures", disabled=True, use_container_width=True)
            if st.button("Add pictures from last saved version", use_container_width=True):
                clear_add_pictures_editor_commit_request(st.session_state)
                with st.spinner("Preparing destination image packs and finding the best matches…"):
                    _activate_picture_stage()
                st.rerun()
        return

    if st.button("Apply Changes", type="primary", use_container_width=True):
        st.session_state.pop("add_pictures_last_error", None)
        request_add_pictures_editor_commit(st.session_state)
        st.rerun()
    st.button("Add pictures", disabled=True, use_container_width=True)
    st.caption("Apply changes before adding pictures so image matching uses the latest committed itinerary.")
