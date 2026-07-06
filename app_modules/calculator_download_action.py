"""Download action for exported calculation workbooks."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from calculator.calculator_state import CalculatorState
from calculator.workbook_export import WorkbookExport, export_calculation_workbook
from project_storage.workflow_hooks import save_calculation_workbook

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_READY_DOWNLOAD_KEY = "calculator_ready_xlsx_download"


def prepare_calculation_download(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> WorkbookExport:
    """Build the Excel download payload for the current calculator state."""

    return export_calculation_workbook(state, currency_rates=currency_rates)


def prepare_staged_calculation_download(
    session_state: MutableMapping[str, Any],
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> WorkbookExport:
    """Prepare an Excel file, save it to cloud, and expose a safe download button."""

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    saved_to_cloud = save_calculation_workbook(
        session_state,
        state,
        content=export.content,
        filename=export.filename,
        currency_rates=currency_rates or {},
    )
    session_state[_READY_DOWNLOAD_KEY] = {
        "filename": export.filename,
        "mime": CALCULATION_XLSX_MIME,
        "content": export.content,
        "saved_to_cloud": bool(saved_to_cloud),
    }
    return export


def render_ready_calculation_download(session_state: MutableMapping[str, Any]) -> None:
    """Render a user-clicked Streamlit download button to avoid browser-blocked popups."""

    payload = session_state.get(_READY_DOWNLOAD_KEY)
    if not isinstance(payload, dict) or not payload.get("content"):
        return
    filename = str(payload.get("filename") or "itinerary-calculation.xlsx")
    st.html('<div class="calculator-download-ready-panel">')
    if payload.get("saved_to_cloud"):
        st.success("Excel is ready and saved to the cloud.")
    else:
        st.info("Excel is ready. Cloud save is unavailable for this session.")
    st.download_button(
        label="Download prepared Excel",
        data=bytes(payload["content"]),
        file_name=filename,
        mime=str(payload.get("mime") or CALCULATION_XLSX_MIME),
        use_container_width=True,
        key=f"download_prepared_calculation_{filename}",
    )
    if st.button("Clear prepared Excel", use_container_width=True, key="clear_prepared_calculation_download"):
        clear_ready_calculation_download(session_state)
        st.rerun()
    st.html("</div>")


def clear_ready_calculation_download(session_state: MutableMapping[str, Any]) -> None:
    """Clear the staged calculator download."""

    session_state.pop(_READY_DOWNLOAD_KEY, None)


def render_calculation_download_button(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> None:
    """Render a safe Excel download button for the calculator page."""

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    st.download_button(
        label="Download Excel",
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
