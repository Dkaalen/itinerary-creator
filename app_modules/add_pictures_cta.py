"""Edit-stage Add Pictures call-to-action and editor-save transaction UI."""

from __future__ import annotations

import streamlit as st

from app_modules.image_gateway_ui import (
    _connect_current_image_bank,
    _current_image_bank_status,
    _image_bank_gateway_is_blocking,
    _render_image_bank_gateway_repair,
)
from app_modules.project_io import rebuild_current_preview
from app_modules.workflow_actions import enter_picture_stage
from app_modules.workflow_transactions import (
    WorkflowTransactionTarget,
    clear_workflow_transaction,
    retry_workflow_transaction,
    start_workflow_transaction,
    transaction_timeout_copy,
    transaction_wait_copy,
    workflow_transaction_state,
)
from images.app_image_selection import audit_day_image_matches, select_day_images_with_overrides


def activate_picture_stage() -> bool:
    """Run the committed Add Pictures transition and store user-facing status."""

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


def add_pictures_transaction():
    return workflow_transaction_state(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)


def add_pictures_apply_ready() -> bool:
    return add_pictures_transaction().ready


def add_pictures_apply_pending() -> bool:
    transaction = add_pictures_transaction()
    return transaction.pending or transaction.timed_out


def maybe_rerun_after_editor_commit(was_waiting_for_apply: bool) -> None:
    """Rerun as soon as the editor reports a pending Add Pictures commit is ready."""

    if was_waiting_for_apply and add_pictures_apply_ready():
        st.rerun()


def render_add_pictures_cta() -> None:
    """Render the edit-stage CTA without owning the whole edit page."""

    st.html(
        '<div class="bottom-cta"><div><strong>Text ready?</strong>'
        '<span>Apply the current preview changes, then add destination pictures from the committed itinerary.</span></div></div>'
    )
    last_error = st.session_state.get("add_pictures_last_error")
    if last_error:
        st.error(str(last_error))
        st.caption("Retry Add Pictures after fixing the issue, or continue editing and apply changes again.")
    gateway_result = st.session_state.get("image_bank_gateway")
    if _image_bank_gateway_is_blocking(gateway_result):
        _render_image_bank_gateway_repair(gateway_result)
        return

    if add_pictures_apply_ready():
        _render_ready_actions()
        return

    if add_pictures_apply_pending():
        _render_pending_actions()
        return

    if st.button("Apply Changes", type="primary", use_container_width=True):
        st.session_state.pop("add_pictures_last_error", None)
        start_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
        st.rerun()
    st.button("Add pictures", disabled=True, use_container_width=True)
    st.caption("Apply changes before adding pictures so image matching uses the latest committed itinerary.")


def _render_ready_actions() -> None:
    st.success("Changes applied. Add pictures is ready to run from the committed itinerary.")
    left, right = st.columns(2)
    with left:
        if st.button("Edit again", use_container_width=True):
            clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
            st.rerun()
    with right:
        if st.button("Add pictures", type="primary", use_container_width=True):
            with st.spinner("Preparing destination pictures and finding the best matches…"):
                activate_picture_stage()
            st.rerun()


def _render_pending_actions() -> None:
    transaction = add_pictures_transaction()
    if transaction.timed_out:
        _render_timeout_actions(transaction)
        return

    st.info(transaction_wait_copy(transaction))
    st.button("Add pictures", disabled=True, use_container_width=True)
    if st.button("Add pictures from last saved version", use_container_width=True):
        clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
        with st.spinner("Preparing destination image packs and finding the best matches…"):
            activate_picture_stage()
        st.rerun()


def _render_timeout_actions(transaction) -> None:
    st.warning(transaction_timeout_copy(transaction))
    st.caption("Retry the save, add pictures from the last saved version, or cancel and keep editing.")
    with st.container(key="workflow_transaction_actions_add_pictures"):
        retry_col, saved_col, cancel_col = st.columns([0.22, 0.56, 0.22], gap="small")
        with retry_col:
            if st.button("Retry save", type="primary", use_container_width=True, key="retry_add_pictures_editor_commit"):
                retry_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
                st.rerun()
        with saved_col:
            if st.button("Add pictures from last saved version", use_container_width=True, key="fallback_add_pictures_after_timeout"):
                clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
                with st.spinner("Preparing destination image packs and finding the best matches…"):
                    activate_picture_stage()
                st.rerun()
        with cancel_col:
            if st.button("Cancel", use_container_width=True, key="cancel_add_pictures_editor_commit"):
                clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)
                st.rerun()
