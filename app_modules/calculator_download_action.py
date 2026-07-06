"""Download action for exported calculation workbooks."""

from __future__ import annotations

import streamlit as st

from calculator.calculator_state import CalculatorState
from calculator.workbook_export import WorkbookExport, export_calculation_workbook
from project_storage.workflow_hooks import save_calculation_workbook

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def prepare_calculation_download(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> WorkbookExport:
    """Build the Excel download payload for the current calculator state."""

    return export_calculation_workbook(state, currency_rates=currency_rates)


def render_calculation_download_button(
    state: CalculatorState,
    *,
    currency_rates: dict[str, float] | None = None,
) -> None:
    """Render the Excel download button for the calculator page."""

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
