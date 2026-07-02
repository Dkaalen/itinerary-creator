"""Download action for exported calculation workbooks."""

from __future__ import annotations

import streamlit as st

from calculator.calculator_state import CalculatorState
from calculator.workbook_export import WorkbookExport, export_calculation_workbook

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def prepare_calculation_download(state: CalculatorState) -> WorkbookExport:
    """Build the Excel download payload for the current calculator state."""

    return export_calculation_workbook(state)


def render_calculation_download_button(state: CalculatorState) -> None:
    """Render the Excel download button for the calculator page."""

    export = prepare_calculation_download(state)
    st.download_button(
        label="Download Excel",
        data=export.content,
        file_name=export.filename,
        mime=CALCULATION_XLSX_MIME,
        use_container_width=True,
        disabled=not bool(state.rows),
    )
