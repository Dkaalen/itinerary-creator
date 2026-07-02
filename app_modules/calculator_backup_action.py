"""Render calculator backup import/export controls."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from calculator.calculator_state import CalculatorState
from calculator.filename_sanitizer import sanitize_filename_stem
from calculator.state_serialization import calculator_state_from_json, calculator_state_to_json

CALCULATOR_BACKUP_MIME = "application/json"


@dataclass(frozen=True)
class CalculatorBackupDownload:
    """Prepared calculator backup download payload."""

    filename: str
    content: bytes


def prepare_calculator_backup_download(state: CalculatorState) -> CalculatorBackupDownload:
    """Return a JSON backup payload for the current calculator state."""

    stem = sanitize_filename_stem(state.itinerary_name or "Calculation")
    content = calculator_state_to_json(state).encode("utf-8")
    return CalculatorBackupDownload(filename=f"{stem} - Calculator Backup.json", content=content)


def read_calculator_backup(uploaded_file: object) -> CalculatorState:
    """Read calculator state from a Streamlit uploaded JSON file object."""

    if hasattr(uploaded_file, "getvalue"):
        return calculator_state_from_json(uploaded_file.getvalue())
    if hasattr(uploaded_file, "read"):
        return calculator_state_from_json(uploaded_file.read())
    raise ValueError("Unsupported calculator backup upload.")


def render_calculator_backup_controls(state: CalculatorState) -> CalculatorState | None:
    """Render calculator backup controls and return imported state when provided."""

    with st.expander("Save / reopen calculator", expanded=False):
        backup = prepare_calculator_backup_download(state)
        st.download_button(
            label="Download calculator backup",
            data=backup.content,
            file_name=backup.filename,
            mime=CALCULATOR_BACKUP_MIME,
            use_container_width=True,
        )
        uploaded_file = st.file_uploader(
            "Reopen calculator backup",
            type=("json",),
            accept_multiple_files=False,
            key="calculator_backup_upload",
        )
        if uploaded_file is None:
            return None
        if not st.button("Open calculator backup", use_container_width=True):
            return None
        try:
            return read_calculator_backup(uploaded_file)
        except (ValueError, TypeError) as exc:
            st.warning(f"Could not open calculator backup: {exc}")
            return None
