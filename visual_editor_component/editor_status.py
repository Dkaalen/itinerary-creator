"""Shared visual-editor session status helpers."""

import streamlit as st


def autosave_status(saved_info, *, recovered=False):
    if not isinstance(saved_info, dict):
        return
    status = st.session_state.setdefault("persistent_draft_status", {})
    status.update({
        "ok": bool(saved_info.get("ok")),
        "draft_id": saved_info.get("draft_id", ""),
        "saved_at": saved_info.get("saved_at", ""),
        "payload_hash": saved_info.get("payload_hash", ""),
        "recovered": bool(recovered),
        "reason": saved_info.get("reason", ""),
    })
