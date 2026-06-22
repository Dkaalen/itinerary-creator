"""Shared visual-editor session status helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        "updated_at": _now_iso(),
    })


def persistent_draft_status() -> dict:
    """Return compact autosave/recovery status for the browser editor payload."""

    status = st.session_state.get("persistent_draft_status")
    if not isinstance(status, dict):
        return {}
    allowed = {
        "ok",
        "draft_id",
        "saved_at",
        "payload_hash",
        "recovered",
        "reason",
        "updated_at",
    }
    return {key: status.get(key, "") for key in allowed if key in status}
