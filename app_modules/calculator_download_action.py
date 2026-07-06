"""Download action for exported calculation workbooks."""

from __future__ import annotations

import base64
import uuid
from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from calculator.calculator_state import CalculatorState
from calculator.workbook_export import WorkbookExport, export_calculation_workbook
from project_storage.workflow_hooks import save_calculation_workbook

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PENDING_BROWSER_DOWNLOAD_KEY = "calculator_pending_xlsx_download"


def prepare_calculation_download(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> WorkbookExport:
    """Build the Excel download payload for the current calculator state."""

    return export_calculation_workbook(state, currency_rates=currency_rates)


def prepare_browser_calculation_download(
    session_state: MutableMapping[str, Any],
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> WorkbookExport:
    """Prepare an Excel file for immediate browser-side download."""

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    save_calculation_workbook(
        session_state,
        state,
        content=export.content,
        filename=export.filename,
        currency_rates=currency_rates or {},
    )
    session_state[_PENDING_BROWSER_DOWNLOAD_KEY] = {
        "id": uuid.uuid4().hex,
        "filename": export.filename,
        "mime": CALCULATION_XLSX_MIME,
        "base64": base64.b64encode(export.content).decode("ascii"),
    }
    return export


def browser_calculation_download_payload(session_state: MutableMapping[str, Any]) -> dict[str, str] | None:
    """Return the pending browser download payload, if one exists."""

    payload = session_state.get(_PENDING_BROWSER_DOWNLOAD_KEY)
    if not isinstance(payload, dict):
        return None
    required = {"id", "filename", "mime", "base64"}
    if not required.issubset(payload):
        return None
    return {key: str(payload[key]) for key in required}


def clear_browser_calculation_download(session_state: MutableMapping[str, Any]) -> None:
    """Clear the pending browser-side calculator download."""

    session_state.pop(_PENDING_BROWSER_DOWNLOAD_KEY, None)


def render_calculation_download_button(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> None:
    """Render a fallback Excel download button for the calculator page."""

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    st.download_button(
        label="Download Excel fallback",
        data=export.content,
        file_name=export.filename,
        mime=CALCULATION_XLSX_MIME,
        use_container_width=True,
        disabled=not bool(state.rows),
        on_click=_save_calculation_workbook,
        args=(state, export.content, export.filename, currency_rates or {}),
    )


def _save_calculation_workbook(
    state: CalculatorState,
    content: bytes,
    filename: str,
    currency_rates: dict[str, float],
) -> None:
    save_calculation_workbook(
        st.session_state,
        state,
        content=content,
        filename=filename,
        currency_rates=currency_rates,
    )
