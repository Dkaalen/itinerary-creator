"""Render cloud calculator workbook rows inside the project browser."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.project_browser_formatting import short_storage_time
from app_modules.project_browser_state import (
    clear_file_delete_confirmation,
    file_delete_candidate_id,
    remember_file_delete_candidate,
)
from project_storage.errors import storage_user_message
from app_modules.project_storage_service import (
    delete_cloud_project_file_result,
    download_cloud_project_file,
    list_cloud_calculation_files,
)
from project_storage.file_writer import CALCULATION_XLSX_MIME
from app_modules.session_state_keys import (
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
)


def render_calculation_files(project_id: str) -> None:
    """Render saved calculator workbooks for one cloud project."""

    visible_key = f"cloud_calculator_files_visible_{project_id}"
    visible = bool(st.session_state.get(visible_key))
    label = "Hide Calculator files" if visible else "Show Calculator files"
    if st.button(label, key=f"toggle_cloud_calculator_files_{project_id}", use_container_width=True):
        st.session_state[visible_key] = not visible
        st.rerun()
    if not visible:
        return

    try:
        files = list_cloud_calculation_files(project_id, limit=8)
    except Exception:
        st.caption(storage_user_message("files"))
        return
    if not files:
        st.caption("No calculator files saved for this itinerary yet.")
        return
    with st.container(border=True, key=f"cloud_calculator_files_{project_id}"):
        st.caption(f"Calculator files ({len(files)})")
        for index, item in enumerate(files):
            _render_calculation_file(project_id, item, index=index)


def _render_calculation_file(project_id: str, item: dict[str, Any], *, index: int) -> None:
    filename = str(item.get("filename") or "calculation.xlsx")
    created = short_storage_time(item.get("created_at"))
    storage_path = str(item.get("storage_path") or "")
    file_id = str(item.get("id") or "")
    row_key = file_id or str(index)
    st.html(
        f"""
        <div class="cloud-file-row">
          <strong>{escape(filename)}</strong>
          <span>{escape(created)}</span>
        </div>
        """
    )
    prepared_key = f"cloud_calculator_file_payload_{project_id}_{row_key}"
    prepare_col, delete_col = st.columns([0.68, 0.32])
    with prepare_col:
        if st.button(
            "Prepare calculator file",
            key=f"prepare_cloud_calculator_{project_id}_{row_key}",
            use_container_width=True,
            disabled=not storage_path,
        ):
            try:
                st.session_state[prepared_key] = download_cloud_project_file(storage_path)
            except Exception:
                st.caption(storage_user_message("download"))
    with delete_col:
        if st.button(
            "Delete file",
            key=f"delete_cloud_calculator_file_{project_id}_{row_key}",
            use_container_width=True,
            disabled=not file_id and not storage_path,
        ):
            remember_file_delete_candidate(st.session_state, file_id=file_id or storage_path, filename=filename)
            st.rerun()
    _render_calculation_file_delete_confirmation(
        project_id,
        file_id=file_id,
        storage_path=storage_path,
        filename=filename,
        prepared_key=prepared_key,
    )
    content = st.session_state.get(prepared_key)
    if content:
        st.download_button(
            "Download calculator file",
            data=bytes(content),
            file_name=filename,
            mime=CALCULATION_XLSX_MIME,
            key=f"download_cloud_calculator_{project_id}_{row_key}",
            use_container_width=True,
        )


def _render_calculation_file_delete_confirmation(
    project_id: str,
    *,
    file_id: str,
    storage_path: str,
    filename: str,
    prepared_key: str,
) -> None:
    candidate = file_delete_candidate_id(st.session_state)
    if not candidate or candidate not in {file_id, storage_path}:
        return
    st.html(
        f"""
        <div class="cloud-project-delete-warning">
          <strong>Delete {escape(filename)}?</strong>
          <span>This removes the saved calculator workbook from cloud storage.</span>
        </div>
        """
    )
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key=f"cancel_delete_cloud_file_{project_id}_{candidate}", use_container_width=True):
            clear_file_delete_confirmation(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button("Delete file permanently", key=f"confirm_delete_cloud_file_{project_id}_{candidate}", use_container_width=True):
            try:
                result = delete_cloud_project_file_result(file_id, storage_path=storage_path)
                if result and result.ok:
                    st.session_state.pop(prepared_key, None)
                    clear_file_delete_confirmation(st.session_state)
                    if not result.storage_files_deleted:
                        st.session_state[PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY] = (
                            "File record was deleted, but the stored file could not be removed automatically."
                        )
                    st.session_state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Deleted {filename}."
                    st.rerun()
                    return
                st.warning("Cloud storage is unavailable. File was not deleted.")
            except Exception:
                st.error(storage_user_message("delete"))
