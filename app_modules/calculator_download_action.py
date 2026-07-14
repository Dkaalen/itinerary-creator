"""Download action for exported calculation workbooks."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, MutableMapping
from typing import Any

try:
    import streamlit as st
except ModuleNotFoundError:  # Allow pure calculator tests without Streamlit installed.
    st = None

from calculator.calculator_state import CalculatorState
from calculator.currency_rates import normalize_currency_rates
from calculator.state_serialization import calculator_state_to_dict
from calculator.workbook_export import WorkbookExport, export_calculation_workbook
from app_modules.calculator_state_keys import CALCULATOR_READY_DOWNLOAD_KEY
from app_modules.calculator_session_state import clear_ready_calculation_download

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _streamlit_api():
    global st
    if st is None:
        import streamlit as streamlit_api

        st = streamlit_api
    return st


def calculator_download_signature(
    state: CalculatorState,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> str:
    """Return a stable identity for the calculator state that feeds Excel export."""

    payload = {
        "calculator_state": calculator_state_to_dict(state),
        "currency_rates": normalize_currency_rates(currency_rates),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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

    from project_storage.workflow_hooks import save_calculation_workbook

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    saved_to_cloud = save_calculation_workbook(
        session_state,
        state,
        content=export.content,
        filename=export.filename,
        currency_rates=currency_rates or {},
    )
    session_state[CALCULATOR_READY_DOWNLOAD_KEY] = {
        "filename": export.filename,
        "mime": CALCULATION_XLSX_MIME,
        "content": export.content,
        "saved_to_cloud": bool(saved_to_cloud),
        "download_signature": calculator_download_signature(state, currency_rates=currency_rates),
    }
    return export


def ready_calculation_download_payload(
    session_state: MutableMapping[str, Any],
    current_state: CalculatorState,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return a browser-download payload for the current prepared workbook."""

    payload = session_state.get(CALCULATOR_READY_DOWNLOAD_KEY)
    if not isinstance(payload, dict) or not payload.get("content"):
        return {}
    if payload.get("download_signature") != calculator_download_signature(
        current_state,
        currency_rates=currency_rates,
    ):
        clear_ready_calculation_download(session_state)
        return {}
    content = bytes(payload["content"])
    return {
        "filename": str(payload.get("filename") or "itinerary-calculation.xlsx"),
        "mime": str(payload.get("mime") or CALCULATION_XLSX_MIME),
        "content_base64": base64.b64encode(content).decode("ascii"),
        "saved_to_cloud": bool(payload.get("saved_to_cloud")),
    }


def render_ready_calculation_download(
    session_state: MutableMapping[str, Any],
    current_state: CalculatorState | None = None,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> None:
    """Render a user-clicked Streamlit download button to avoid browser-blocked popups."""

    ui = _streamlit_api()
    payload = session_state.get(CALCULATOR_READY_DOWNLOAD_KEY)
    if not isinstance(payload, dict) or not payload.get("content"):
        return
    if current_state is not None and payload.get("download_signature") != calculator_download_signature(
        current_state,
        currency_rates=currency_rates,
    ):
        clear_ready_calculation_download(session_state)
        ui.info("Prepared Excel was cleared because the calculator changed. Prepare the download again.")
        return
    filename = str(payload.get("filename") or "itinerary-calculation.xlsx")
    ui.html('<div class="calculator-download-ready-panel">')
    if payload.get("saved_to_cloud"):
        ui.success("Excel is ready and saved to the cloud.")
    else:
        ui.info("Excel is ready. Cloud save is unavailable for this session.")
    ui.download_button(
        label="Download prepared Excel",
        data=bytes(payload["content"]),
        file_name=filename,
        mime=str(payload.get("mime") or CALCULATION_XLSX_MIME),
        use_container_width=True,
        key=f"download_prepared_calculation_{filename}",
    )
    if ui.button("Clear prepared Excel", use_container_width=True, key="clear_prepared_calculation_download"):
        clear_ready_calculation_download(session_state)
        ui.rerun()
    ui.html("</div>")
