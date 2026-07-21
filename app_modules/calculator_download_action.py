"""Download action for exported calculation workbooks."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, MutableMapping
from typing import Any

from calculator.calculator_state import CalculatorState
from calculator.currency_rates import normalize_currency_rates
from calculator.state_serialization import calculator_state_to_dict
from calculator.workbook_export import WorkbookExport, export_calculation_workbook
from app_modules.calculator_state_keys import CALCULATOR_READY_DOWNLOAD_KEY
from app_modules.calculator_session_state import clear_ready_calculation_download

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
) -> None:
    """Prepare an Excel file for immediate browser download.

    Project persistence is independent from calculator workbook downloads. The
    session retains only the browser-ready base64 payload, not a second raw-byte
    copy of the same workbook.
    """

    export = prepare_calculation_download(state, currency_rates=currency_rates)
    session_state[CALCULATOR_READY_DOWNLOAD_KEY] = {
        "filename": export.filename,
        "mime": CALCULATION_XLSX_MIME,
        "content_base64": base64.b64encode(export.content).decode("ascii"),
        "download_signature": calculator_download_signature(state, currency_rates=currency_rates),
    }
    return None


def ready_calculation_download_payload(
    session_state: MutableMapping[str, Any],
    current_state: CalculatorState,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return the current browser-download payload when it is still valid."""

    payload = session_state.get(CALCULATOR_READY_DOWNLOAD_KEY)
    if not isinstance(payload, dict) or not payload.get("content_base64"):
        return {}
    if payload.get("download_signature") != calculator_download_signature(
        current_state,
        currency_rates=currency_rates,
    ):
        clear_ready_calculation_download(session_state)
        return {}
    return {
        "filename": str(payload.get("filename") or "itinerary-calculation.xlsx"),
        "mime": str(payload.get("mime") or CALCULATION_XLSX_MIME),
        "content_base64": str(payload.get("content_base64") or ""),
        "download_signature": str(payload.get("download_signature") or ""),
    }
