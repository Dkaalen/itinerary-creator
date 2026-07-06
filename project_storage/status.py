"""Small UI status helpers for project storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st


def render_storage_error_if_any(state: Mapping[str, Any]) -> None:
    """Show a non-blocking storage warning only when the last save failed."""

    error = str(state.get("project_storage_last_error") or "").strip()
    if error:
        st.warning("The itinerary was created, but Supabase storage did not save this version yet.")
