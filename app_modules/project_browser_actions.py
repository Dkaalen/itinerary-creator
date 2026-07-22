"""Transactional actions shared by the compact project manager views."""

from __future__ import annotations

import streamlit as st

from app_modules.project_browser_state import remember_open_candidate, remember_selected_project
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_validation import SavedProjectError
from app_modules.session_transitions import complete_project_duplicate, prepare_project_switch
from project_storage.errors import storage_user_message
from project_storage.project_browser import load_latest_cloud_project_payload
from project_storage.project_management import duplicate_cloud_project


def request_open_cloud_project(project_id: str) -> None:
    """Open immediately unless the active project has unsaved changes."""

    active_id = active_project_id_from_state(st.session_state)
    if active_id and active_id != project_id and active_project_has_unsaved_changes(st.session_state):
        remember_selected_project(st.session_state, project_id)
        remember_open_candidate(st.session_state, project_id)
        st.rerun()
        return
    open_cloud_project(project_id)


def open_cloud_project(project_id: str) -> None:
    """Load the latest cloud snapshot through the supported reconstruction path."""

    try:
        payload = load_latest_cloud_project_payload(project_id)
    except Exception:
        st.error(storage_user_message("open"))
        return
    if not payload:
        st.warning("This cloud project has no saved itinerary snapshot yet.")
        return
    try:
        result = load_saved_project(st.session_state, payload, project_id_override=project_id)
    except SavedProjectError as error:
        st.error(f"Cloud project could not be opened: {error}")
        return
    except Exception:
        st.error(storage_user_message("open"))
        return
    if result.ok:
        prepare_project_switch(st.session_state)
        st.success(result.message or "Cloud project opened.")
        st.rerun()
    else:
        st.error(result.message or "Cloud project could not be opened.")


def duplicate_cloud_project_action(project_id: str, name: str) -> None:
    """Duplicate a project and select the new copy on the first list page."""

    try:
        result = duplicate_cloud_project(project_id, f"{name} — Copy")
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error(storage_user_message("save"))
        return
    if not result:
        st.warning("Cloud storage is unavailable. Project was not duplicated.")
        return
    from app_modules.project_browser_state import set_browser_page_index

    set_browser_page_index(st.session_state, 0)
    remember_selected_project(st.session_state, result.get("project_id"))
    complete_project_duplicate(st.session_state, name=result["name"])
    st.rerun()
